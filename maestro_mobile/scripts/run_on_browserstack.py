import argparse
import configparser
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import maestro_report
import requests
import yaml
from requests.auth import HTTPBasicAuth

BASE_URL = "https://api-cloud.browserstack.com/app-automate/maestro/v2"
PROJECT_ROOT = Path(__file__).parent.parent.parent
FLOWS_DIR = Path(__file__).parent.parent / "flows"
# The app is built against one Connect server, so the environment picks the build -
# there is no runtime switch. Keys match config/env.yaml so a caller can hand its
# own env name straight through.
APK_BY_ENV = {
    "stage": "app-cccStaging-release.apk",
    "prod": "app-commcare-release.apk",
}
DEFAULT_APP_ENV = "stage"
DEVICE = "Google Pixel 7-13.0"
PROJECT_NAME = "Connect Mobile Automation"
TEST_FLOWS = [
    "login_signup_success.yaml",
    "login_account_locked.yaml",
    # Case List Map "View on Map" cases (share the Case_list worker).
    "map_10_toggle_panel_visible.yaml",
    "map_11_toggle_switches.yaml",
    # Map_08 (config-error banner) and Map_09 (single-entity, panel hidden) - each
    # on its own worker. Real-device only: the emulator fails PersonalId's
    # device-security check for these accounts.
    "map_08_config_warning.yaml",
    "map_09_single_entity_panel_hidden.yaml",
]
POLL_INTERVAL_SECONDS = 15

# Single source of truth for mobile identities, shared with the hybrid web test -
# a worker defined in two files drifts, and the symptom is a device signing in as
# the wrong worker on one environment only.
WORKERS_FILE = PROJECT_ROOT / "test_data" / "mobile_workers.yaml"
WORKER_BY_FLOW = {
    "login_signup_success.yaml": "MAESTRO_LOGIN_SIGNUP_SUCCESS",
    "login_account_locked.yaml": "MAESTRO_LOGIN_ACCOUNT_LOCKED",
    # Both halves of the hybrid chain sign in as the same worker - they are two
    # device sessions against one opportunity, split so the web side can confirm
    # Connect evaluated the blocked visit before the task completion is submitted.
    "worker_blocked_visit.yaml": "MAESTRO_WORKER_RELEARN_TASK",
    "worker_relearn_task.yaml": "MAESTRO_WORKER_RELEARN_TASK",
    # Map_10/Map_11 sign in as the same worker; it is baked into each executed
    # flow and inherited by the shared_map_open subflow via runFlow.
    "map_10_toggle_panel_visible.yaml": "MAESTRO_MAP_CASE_LIST",
    "map_11_toggle_switches.yaml": "MAESTRO_MAP_CASE_LIST",
    # DATA SWAP (Anshu): the MAP_08 test (misconfigured banner) runs on the Map_09
    # account, and the MAP_09 test (single entity, panel hidden) on the Map_08
    # account. Wired here deliberately - do not "correct" the mismatch.
    "map_08_config_warning.yaml": "MAESTRO_MAP_USER_09",
    "map_09_single_entity_panel_hidden.yaml": "MAESTRO_MAP_USER_08",
}
# workers-file key -> the Maestro env key the flows read.
WORKER_ENV_KEYS = {
    "country_code": "COUNTRY_CODE",
    "phone_number": "PHONE_NUMBER",
    "username": "USERNAME",
    "backup_code": "BACKUP_CODE",
}
STAGING_SUFFIX = "_staging"
STAGING_ENV = "stage"
# login_signup_success checks the wrong-code error path, so it needs a code that is
# guaranteed *not* to be the account's. Derived rather than hardcoded: prod's signup
# account really does use "123456", so a literal wrong code logged it straight in and
# the expected error never appeared.
WRONG_BACKUP_CODES = ("000000", "111111")


def load_workers():
    with open(WORKERS_FILE, encoding="utf-8") as f:
        return yaml.safe_load(f)


def resolve_worker(entry, app_env=None):
    """The environment's values from one mobile_workers.yaml entry.

    Same convention as the rest of that file and web_test_data.yaml: unsuffixed
    keys are prod and a "_staging" key overrides its base key on staging, so a
    value that is identical on both environments is written once.
    """
    app_env = app_env or DEFAULT_APP_ENV
    resolved = {}
    for data_key, env_key in WORKER_ENV_KEYS.items():
        value = entry.get(f"{data_key}{STAGING_SUFFIX}") if app_env == STAGING_ENV else None
        if value is None:
            value = entry.get(data_key)
        if value is not None:
            resolved[env_key] = str(value)

    first, second = WRONG_BACKUP_CODES
    resolved["WRONG_BACKUP_CODE"] = second if resolved.get("BACKUP_CODE") == first else first
    return resolved


def env_by_flow(flows, app_env=None):
    """Maestro env per flow, keyed by flow filename.

    Per flow rather than one dict for the whole zip because the flows use
    deliberately different accounts - login_account_locked needs the locked one -
    and a single shared env would hand every flow the same identity. Flows with no
    entry (subflows like shared_login_signup.yaml) get nothing and inherit from
    their caller, which is how Maestro already passes env into runFlow.
    """
    workers = None
    resolved = {}
    for flow in flows:
        key = WORKER_BY_FLOW.get(flow)
        if not key:
            continue
        if workers is None:
            workers = load_workers()
        entry = workers.get(key)
        if entry is None:
            sys.exit(f"No '{key}' entry in {WORKERS_FILE.name}, needed by flow {flow}")
        resolved[flow] = resolve_worker(entry, app_env)
    return resolved


def _yaml_quote(value):
    escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def apply_env_overrides(flow_text, env):
    """Return flow_text with its Maestro `env:` header values replaced by env.

    Maestro flows are YAML: a header (appId, env, ...), a `---` separator, then
    steps. BrowserStack's Maestro API accepts no per-build env values, so
    runtime parameters have to be baked into the flow files before upload.
    Values are always quoted - opportunity names contain colons.
    """
    if not env:
        return flow_text

    newline = "\r\n" if "\r\n" in flow_text else "\n"
    lines = flow_text.splitlines()
    try:
        separator = next(i for i, line in enumerate(lines) if line.strip() == "---")
    except StopIteration:
        raise ValueError("Flow has no '---' separator - not a Maestro flow")

    header, body = lines[:separator], lines[separator:]
    pending = dict(env)
    out = []
    in_env_block = False

    for line in header:
        stripped = line.strip()
        if stripped == "env:":
            in_env_block = True
            out.append(line)
            continue
        if in_env_block:
            # Comments and blank lines are part of the block, not its end. Ending
            # it on them stranded every key declared after a comment: the key was
            # appended here AND left in place further down, so the env mapping
            # carried it twice. Python's YAML quietly keeps the last duplicate,
            # but BrowserStack rejects the whole test suite with
            # "[BROWSERSTACK_INVALID_TESTSUITE] Invalid YAML syntax".
            if not stripped or stripped.startswith("#"):
                out.append(line)
                continue
            is_entry = line[:1].isspace() and ":" in stripped
            if is_entry:
                key = stripped.split(":", 1)[0].strip()
                if key in pending:
                    indent = line[: len(line) - len(line.lstrip())]
                    out.append(f"{indent}{key}: {_yaml_quote(pending.pop(key))}")
                else:
                    out.append(line)
                continue
            # a non-indented line ends the env block - add any new keys first
            for key, value in pending.items():
                out.append(f"  {key}: {_yaml_quote(value)}")
            pending.clear()
            in_env_block = False
        out.append(line)

    if pending:
        if not in_env_block:
            out.append("env:")
        for key, value in pending.items():
            out.append(f"  {key}: {_yaml_quote(value)}")

    result = newline.join(out + body)
    return result + newline if flow_text.endswith(("\n", "\r")) else result


def resolve_apk(app_env=None):
    """The APK for this environment, checked to exist before anything is uploaded.

    Failing here beats failing on a 42 MB upload, or worse, running the wrong build
    against the wrong server and reading the result as a test failure.
    """
    app_env = app_env or DEFAULT_APP_ENV
    name = APK_BY_ENV.get(app_env)
    if name is None:
        sys.exit(f"Unknown app environment {app_env!r} - expected one of {sorted(APK_BY_ENV)}")
    path = PROJECT_ROOT / "app" / name
    if not path.exists():
        sys.exit(f"No APK for environment {app_env!r} at {path}")
    return path


def _raise_for_status_with_body(response, what):
    """raise_for_status(), but keep BrowserStack's explanation.

    Their upload errors carry the only useful detail in the body - e.g. a 422
    "[BROWSERSTACK_INVALID_TESTSUITE] Invalid YAML syntax" - and a bare status
    code sends you looking in the wrong place.
    """
    if response.ok:
        return
    raise requests.HTTPError(f"{what} failed with HTTP {response.status_code}: {response.text[:500]}")


def get_credentials():
    username = os.getenv("BROWSERSTACK_USERNAME")
    access_key = os.getenv("BROWSERSTACK_ACCESS_KEY")

    if not username or not access_key:
        config = configparser.ConfigParser()
        config.read(PROJECT_ROOT / "settings.cfg")
        if config.has_section("browserstack"):
            username = username or config.get("browserstack", "BROWSERSTACK_USERNAME", fallback=None)
            access_key = access_key or config.get("browserstack", "BROWSERSTACK_ACCESS_KEY", fallback=None)

    if not username or not access_key:
        sys.exit("BrowserStack credentials not set (BROWSERSTACK_USERNAME/BROWSERSTACK_ACCESS_KEY env vars, or [browserstack] section in settings.cfg)")

    return HTTPBasicAuth(username, access_key)


def upload_app(auth, app_env=None):
    apk_path = resolve_apk(app_env)
    app_env = app_env or DEFAULT_APP_ENV
    print(f"Uploading {apk_path.name} for env '{app_env}'...")
    with open(apk_path, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/app",
            auth=auth,
            files={"file": f},
            # Distinct per environment so a prod upload cannot overwrite the staging
            # build under a shared custom_id.
            data={"custom_id": f"CCC_{app_env}"},
        )
    _raise_for_status_with_body(response, f"App upload ({apk_path.name})")
    app_url = response.json()["app_url"]
    print(f"App uploaded: {app_url}")
    return app_url


def upload_test_suite(auth, env=None, flow_env=None):
    """Zip the flows, baking in runtime parameters.

    flow_env: {flow filename: env} - the per-environment worker for that flow.
    env:      values applied to every flow, and they win over flow_env, so an
              explicit caller override beats the resolved worker.
    """
    zip_path = FLOWS_DIR.parent / "flows.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in FLOWS_DIR.iterdir():
            if not file.is_file():
                continue
            file_env = dict((flow_env or {}).get(file.name, {}))
            file_env.update(env or {})
            # BrowserStack requires every file to sit inside a single root folder within the zip.
            if file_env and file.suffix in (".yaml", ".yml"):
                # Bake runtime parameters in - the API takes no env values, and
                # Maestro passes a flow's env down into its runFlow subflows.
                zf.writestr(f"flows/{file.name}", apply_env_overrides(file.read_text(), file_env))
            else:
                zf.write(file, arcname=f"flows/{file.name}")

    try:
        print("Uploading test suite...")
        with open(zip_path, "rb") as f:
            response = requests.post(
                f"{BASE_URL}/test-suite",
                auth=auth,
                files={"file": f},
                data={"custom_id": "connect_mobile_flows"},
            )
    finally:
        zip_path.unlink()

    _raise_for_status_with_body(response, "Test suite upload")
    test_suite_url = response.json()["test_suite_url"]
    print(f"Test suite uploaded: {test_suite_url}")
    return test_suite_url


def trigger_build(auth, app_url, test_suite_url, flows=None, app_env=None):
    app_env = app_env or DEFAULT_APP_ENV
    # Env in the project and build tag so stage and prod builds are distinguishable
    # on the BrowserStack dashboard (and in anything that echoes the build).
    body = {
        "app": app_url,
        "testSuite": test_suite_url,
        "project": f"{PROJECT_NAME} - {app_env.upper()}",
        "buildTag": app_env,
        "devices": [DEVICE],
        "execute": flows or TEST_FLOWS,
    }
    response = requests.post(f"{BASE_URL}/android/build", auth=auth, json=body)
    response.raise_for_status()
    build_id = response.json()["build_id"]
    print(f"Build triggered: {build_id}")
    return build_id


def poll_build(auth, build_id):
    print("Waiting for build to finish...")
    while True:
        response = requests.get(f"{BASE_URL}/builds/{build_id}", auth=auth)
        response.raise_for_status()
        data = response.json()
        status = data.get("status")
        if status not in ("running", "queued"):
            return data
        time.sleep(POLL_INTERVAL_SECONDS)


def fetch_flow_details(auth, build_id, session_id):
    """Fetch per-flow results plus their Maestro step logs and screenshots.

    Everything is pulled through the REST API so the generated report is fully
    readable without a BrowserStack login (only the video stays on their site).
    """
    flows = []
    try:
        response = requests.get(f"{BASE_URL}/builds/{build_id}/sessions/{session_id}", auth=auth)
        response.raise_for_status()
        testcase_groups = response.json().get("testcases", {}).get("data", [])
    except Exception as exc:
        print(f"Could not fetch session details ({session_id}): {exc}")
        return flows

    for group in testcase_groups:
        for case in group.get("testcases", []):
            flow = {
                "name": case.get("name", "?"),
                "status": case.get("status", "?"),
                "duration_seconds": case.get("duration", "?"),
                "log": "",
                "screenshots": [],
            }
            try:
                log_response = requests.get(case["maestro_log"], auth=auth, timeout=60)
                if log_response.ok:
                    flow["log"] = log_response.text
            except Exception as exc:
                flow["log"] = f"Could not fetch Maestro log: {exc}"
            try:
                shots_response = requests.get(case["screenshots"], auth=auth, timeout=60)
                if shots_response.ok and "zip" in shots_response.headers.get("content-type", ""):
                    import base64
                    import io

                    with zipfile.ZipFile(io.BytesIO(shots_response.content)) as zf:
                        for shot_name in zf.namelist():
                            if shot_name.lower().endswith(".png"):
                                encoded = base64.b64encode(zf.read(shot_name)).decode()
                                flow["screenshots"].append({"name": shot_name, "base64": encoded})
            except Exception as exc:
                print(f"Could not fetch screenshots for {flow['name']}: {exc}")
            flows.append(flow)
    return flows


def summarize_build(result, build_id, auth=None, flows=None):
    passed = failed = skipped = 0
    session_rows = []
    for device in result.get("devices", []):
        device_name = f"{device.get('device', '?')} (Android {device.get('os_version', '?')})"
        for session in device.get("sessions", []):
            counts = session.get("testcases", {}).get("status", {})
            s_passed = counts.get("passed", 0)
            s_failed = counts.get("failed", 0) + counts.get("error", 0) + counts.get("timedout", 0)
            s_skipped = counts.get("skipped", 0)
            passed += s_passed
            failed += s_failed
            skipped += s_skipped
            session_rows.append(
                {
                    "device": device_name,
                    "status": session.get("status", "?"),
                    "duration_seconds": session.get("duration", 0),
                    "passed": s_passed,
                    "failed": s_failed,
                    "skipped": s_skipped,
                    "flows": fetch_flow_details(auth, build_id, session["id"]) if auth else [],
                }
            )
    return {
        "status": "SUCCESS" if result.get("status") == "passed" else "FAILURE",
        "build_id": build_id,
        "build_url": f"https://app-automate.browserstack.com/builds/{build_id}",
        "flows": flows or TEST_FLOWS,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "sessions": session_rows,
    }


def write_reports(summary, app_env=None):
    """Delegate to maestro_report - rendering is its own concern, and most of the code."""
    maestro_report.write_reports(summary, app_env or DEFAULT_APP_ENV)


def run_flows(flows=None, env=None, reports=True, session_retries=1, app_env=None):
    """Run flows on a BrowserStack device and return the result summary.

    Importable entry point for hybrid web+mobile tests, which need a device run
    mid-test with runtime parameters (opportunity name, worker phone, ...).
    flows: flow filenames to execute (defaults to TEST_FLOWS).
    env:   Maestro env values baked into the uploaded flows.
    reports: write maestro_report.{json,html} (skip for mid-test runs so the
             suite's own report is not overwritten).
    """
    flows = flows or TEST_FLOWS
    auth = get_credentials()
    app_url = upload_app(auth, app_env=app_env)
    # Each flow signs in as its own worker for this environment; anything the
    # caller passed in env overrides that.
    test_suite_url = upload_test_suite(auth, env=env, flow_env=env_by_flow(flows, app_env=app_env))

    # BrowserStack intermittently answers with build status "error" and
    # "Could not start a session" before running a single step. That is
    # infrastructure, not a test result, so retry it - the uploaded app and test
    # suite are reused. A genuine test failure comes back as "failed" and is
    # never retried.
    attempt = 0
    while True:
        build_id = trigger_build(auth, app_url, test_suite_url, flows=flows, app_env=app_env)
        result = poll_build(auth, build_id)
        if result.get("status") != "error" or attempt >= session_retries:
            break
        attempt += 1
        print(f"Build errored before running (session could not start) - retry {attempt}/{session_retries}")

    summary = summarize_build(result, build_id, auth=auth, flows=flows)
    if reports:
        write_reports(summary, app_env=app_env)
    return summary


def main():
    parser = argparse.ArgumentParser(description="Run Maestro flows on BrowserStack")
    parser.add_argument("--flows", nargs="+", help=f"flow files to run (default: {' '.join(TEST_FLOWS)})")
    parser.add_argument(
        "--env",
        action="append",
        metavar="KEY=VALUE",
        help="Maestro env value baked into the uploaded flows (repeatable)",
    )
    # Named --app-env rather than --env, which is already taken by the Maestro
    # KEY=VALUE pairs above. It selects the APK, since each build targets one server.
    parser.add_argument(
        "--app-env",
        choices=sorted(APK_BY_ENV),
        default=DEFAULT_APP_ENV,
        help=f"environment whose APK to run (default: {DEFAULT_APP_ENV})",
    )
    args = parser.parse_args()

    env = {}
    for item in args.env or []:
        if "=" not in item:
            parser.error(f"--env expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        env[key] = value

    summary = run_flows(flows=args.flows, env=env, app_env=args.app_env)
    print(json.dumps(summary["sessions"], indent=2, default=str)[:2000])
    sys.exit(0 if summary["status"] == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
