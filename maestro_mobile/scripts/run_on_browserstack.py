import argparse
import configparser
import json
import os
import sys
import time
import zipfile
from pathlib import Path

import requests
from requests.auth import HTTPBasicAuth

BASE_URL = "https://api-cloud.browserstack.com/app-automate/maestro/v2"
PROJECT_ROOT = Path(__file__).parent.parent.parent
FLOWS_DIR = Path(__file__).parent.parent / "flows"
APK_PATH = PROJECT_ROOT / "app" / "app-cccStaging-release.apk"
DEVICE = "Google Pixel 7-13.0"
PROJECT_NAME = "Connect Mobile Automation"
TEST_FLOWS = ["login_signup_success.yaml", "login_account_locked.yaml"]
POLL_INTERVAL_SECONDS = 15


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


def upload_app(auth):
    print(f"Uploading {APK_PATH.name}...")
    with open(APK_PATH, "rb") as f:
        response = requests.post(
            f"{BASE_URL}/app",
            auth=auth,
            files={"file": f},
            data={"custom_id": "CCC_Staging"},
        )
    _raise_for_status_with_body(response, f"App upload ({APK_PATH.name})")
    app_url = response.json()["app_url"]
    print(f"App uploaded: {app_url}")
    return app_url


def upload_test_suite(auth, env=None):
    zip_path = FLOWS_DIR.parent / "flows.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in FLOWS_DIR.iterdir():
            if not file.is_file():
                continue
            # BrowserStack requires every file to sit inside a single root folder within the zip.
            if env and file.suffix in (".yaml", ".yml"):
                # Bake runtime parameters in - the API takes no env values, and
                # Maestro passes a flow's env down into its runFlow subflows.
                zf.writestr(f"flows/{file.name}", apply_env_overrides(file.read_text(), env))
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


def trigger_build(auth, app_url, test_suite_url, flows=None):
    body = {
        "app": app_url,
        "testSuite": test_suite_url,
        "project": PROJECT_NAME,
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


def write_reports(summary):
    # Keep the JSON machine-readable but small - screenshots stay in the HTML only.
    json_summary = json.loads(json.dumps(summary))
    for session in json_summary["sessions"]:
        for flow in session.get("flows", []):
            flow.pop("screenshots", None)
            flow.pop("log", None)
    with open("maestro_report.json", "w") as f:
        json.dump(json_summary, f, indent=2)

    def pill(status):
        ok = status in ("passed", "SUCCESS")
        cls = "pill--pass" if ok else "pill--fail"
        icon = "&#10003;" if ok else "&#10007;"
        return f'<span class="pill {cls}">{icon} {status.lower()}</span>'

    rows = "".join(
        f"<tr><td>{s['device']}</td><td>{pill(s['status'])}</td><td class='num'>{s['duration_seconds']}s</td>"
        f"<td class='num'>{s['passed']}</td><td class='num'>{s['failed']}</td><td class='num'>{s['skipped']}</td></tr>"
        for s in summary["sessions"]
    )

    flow_sections = ""
    for session in summary["sessions"]:
        for flow in session.get("flows", []):
            shots = "".join(
                f"<figure><img src='data:image/png;base64,{shot['base64']}' alt='{shot['name']}' loading='lazy'>"
                f"<figcaption>{shot['name']}</figcaption></figure>"
                for shot in flow.get("screenshots", [])
            )
            log_text = (flow.get("log") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            flow_sections += f"""
<section class="card flow">
  <div class="flow__head">
    <h3>{flow['name']}</h3>
    {pill(flow['status'])}
    <span class="meta">{flow['duration_seconds']}s &middot; {session['device']}</span>
  </div>
  <details>
    <summary>Maestro step log</summary>
    <pre>{log_text}</pre>
  </details>
  <details>
    <summary>Screenshots ({len(flow.get('screenshots', []))})</summary>
    <div class="shots">{shots}</div>
  </details>
</section>"""

    total = summary["passed"] + summary["failed"] + summary["skipped"]
    if total:
        segments = "".join(
            f'<div class="comp__seg comp__seg--{name}" style="width:{count / total * 100:.1f}%" '
            f'title="{count} {name}"></div>'
            for name, count in (("passed", summary["passed"]), ("failed", summary["failed"]),
                                ("skipped", summary["skipped"])) if count
        )
        legend = "".join(
            f'<span class="legend__item"><span class="dot dot--{name}"></span>{name.capitalize()} '
            f'<b>{count}</b></span>'
            for name, count in (("passed", summary["passed"]), ("failed", summary["failed"]),
                                ("skipped", summary["skipped"]))
        )
        composition = f"""
  <section class="card">
    <h2 class="card__title">Results</h2>
    <div class="comp">{segments}</div>
    <div class="legend">{legend}</div>
  </section>"""
    else:
        composition = ""

    all_flows = [(f, s) for s in summary["sessions"] for f in s.get("flows", [])]
    durations = [f for f, _ in all_flows if isinstance(f.get("duration_seconds"), (int, float))]
    if durations:
        max_duration = max(f["duration_seconds"] for f in durations) or 1
        duration_rows = "".join(
            f"""<div class="dur__row" title="{f['name']}: {f['duration_seconds']}s">
      <span class="dur__name">{f['name']}</span>
      <span class="dur__track"><span class="dur__bar dur__bar--{'passed' if f['status'] == 'passed' else 'failed'}"
        style="width:{max(f['duration_seconds'] / max_duration * 100, 2):.1f}%"></span></span>
      <span class="dur__value">{f['duration_seconds']}s</span>
    </div>"""
            for f in durations
        )
        duration_chart = f"""
  <section class="card">
    <h2 class="card__title">Flow duration</h2>
    {duration_rows}
  </section>"""
    else:
        duration_chart = ""

    status_pill = pill(summary["status"])
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Maestro Mobile Report</title>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e;
  --muted: #898781; --line: #e1e0d9; --border: rgba(11,11,11,0.10);
  --good: #0ca30c; --good-text: #006300; --critical: #d03b3b;
  --good-bg: rgba(12,163,12,0.10); --critical-bg: rgba(208,59,59,0.10);
  --series: #2a78d6;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7;
    --muted: #898781; --line: #2c2c2a; --border: rgba(255,255,255,0.10);
    --good-text: #0ca30c;
    --good-bg: rgba(12,163,12,0.16); --critical-bg: rgba(208,59,59,0.16);
    --series: #3987e5;
  }}
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0; padding: 32px 16px; background: var(--page); color: var(--ink);
  font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif;
}}
main {{ max-width: 62em; margin: 0 auto; display: grid; gap: 16px; }}
header.card {{ display: flex; flex-wrap: wrap; align-items: center; gap: 12px 16px; }}
h1 {{ font-size: 18px; margin: 0; flex: 1 1 auto; }}
h3 {{ font-size: 14px; margin: 0; }}
.card {{
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px 20px;
}}
.meta {{ color: var(--muted); font-size: 12px; }}
.pill {{
  display: inline-flex; align-items: center; gap: 6px; padding: 2px 10px;
  border-radius: 999px; font-size: 12px; font-weight: 600; white-space: nowrap;
}}
.pill--pass {{ color: var(--good-text); background: var(--good-bg); }}
.pill--fail {{ color: var(--critical); background: var(--critical-bg); }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 16px; }}
.tile {{ padding: 14px 20px; }}
.tile .label {{ color: var(--ink-2); font-size: 12px; }}
.tile .value {{ font-size: 28px; font-weight: 650; margin-top: 2px; }}
.tile .value.zero {{ color: var(--muted); font-weight: 500; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid var(--line); }}
th {{ color: var(--ink-2); font-size: 12px; font-weight: 600; }}
tr:last-child td {{ border-bottom: none; }}
td.num {{ font-variant-numeric: tabular-nums; }}
.flow__head {{ display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; margin-bottom: 8px; }}
details {{ border-top: 1px solid var(--line); }}
summary {{
  cursor: pointer; padding: 10px 0; color: var(--ink-2); font-weight: 600; font-size: 13px;
}}
summary:hover {{ color: var(--ink); }}
pre {{
  background: var(--page); border: 1px solid var(--line); border-radius: 8px;
  padding: 12px 14px; overflow: auto; max-height: 28em; font-size: 12px; margin: 0 0 12px;
}}
.shots {{ display: flex; flex-wrap: wrap; gap: 16px; padding-bottom: 12px; }}
.shots figure {{ margin: 0; }}
.shots img {{ max-width: 260px; border: 1px solid var(--border); border-radius: 8px; display: block; }}
.shots figcaption {{ font-size: 11px; color: var(--muted); text-align: center; margin-top: 4px; }}
a {{ color: inherit; }}
footer {{ color: var(--muted); font-size: 12px; text-align: center; }}
.card__title {{ font-size: 12px; font-weight: 600; color: var(--ink-2); margin: 0 0 12px; }}
.comp {{ display: flex; gap: 2px; height: 16px; border-radius: 4px; overflow: hidden; }}
.comp__seg {{ min-width: 4px; }}
.comp__seg--passed {{ background: var(--good); }}
.comp__seg--failed {{ background: var(--critical); }}
.comp__seg--skipped {{ background: var(--muted); }}
.legend {{ display: flex; flex-wrap: wrap; gap: 8px 20px; margin-top: 10px; font-size: 12px; color: var(--ink-2); }}
.legend__item {{ display: inline-flex; align-items: center; gap: 6px; }}
.legend__item b {{ color: var(--ink); font-variant-numeric: tabular-nums; }}
.dot {{ width: 8px; height: 8px; border-radius: 2px; display: inline-block; }}
.dot--passed {{ background: var(--good); }}
.dot--failed {{ background: var(--critical); }}
.dot--skipped {{ background: var(--muted); }}
.dur__row {{ display: grid; grid-template-columns: minmax(120px, 220px) 1fr 48px; gap: 12px;
  align-items: center; padding: 4px 0; }}
.dur__name {{ font-size: 12px; color: var(--ink-2); overflow: hidden; text-overflow: ellipsis;
  white-space: nowrap; }}
.dur__track {{ height: 8px; }}
.dur__bar {{ display: block; height: 100%; border-radius: 0 4px 4px 0; background: var(--series); }}
.dur__bar--failed {{ background: var(--critical); }}
.dur__value {{ font-size: 12px; color: var(--ink); text-align: right;
  font-variant-numeric: tabular-nums; }}
</style></head>
<body>
<main>
  <header class="card">
    <h1>CommCare-Connect &middot; Maestro Mobile Report</h1>
    {status_pill}
    <span class="meta">{len(summary['flows'])} flows &middot; build {summary['build_id'][:12]}&hellip;</span>
  </header>
  <div class="tiles">
    <div class="card tile"><div class="label">Tests run</div>
      <div class="value">{total}</div></div>
    <div class="card tile"><div class="label">&#10003; Passed</div>
      <div class="value">{summary['passed']}</div></div>
    <div class="card tile"><div class="label">&#10007; Failed</div>
      <div class="value{' zero' if not summary['failed'] else ''}">{summary['failed']}</div></div>
    <div class="card tile"><div class="label">&#8618; Skipped</div>
      <div class="value{' zero' if not summary['skipped'] else ''}">{summary['skipped']}</div></div>
  </div>
  {composition}
  {duration_chart}
  <section class="card">
    <table>
      <tr><th>Device</th><th>Status</th><th>Duration</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr>
      {rows}
    </table>
  </section>
  {flow_sections}
  <footer>Device video requires BrowserStack access:
    <a href="{summary['build_url']}">{summary['build_url']}</a></footer>
</main>
</body></html>"""
    with open("maestro_report.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("Reports written: maestro_report.json, maestro_report.html")


def run_flows(flows=None, env=None, reports=True, session_retries=1):
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
    app_url = upload_app(auth)
    test_suite_url = upload_test_suite(auth, env=env)

    # BrowserStack intermittently answers with build status "error" and
    # "Could not start a session" before running a single step. That is
    # infrastructure, not a test result, so retry it - the uploaded app and test
    # suite are reused. A genuine test failure comes back as "failed" and is
    # never retried.
    attempt = 0
    while True:
        build_id = trigger_build(auth, app_url, test_suite_url, flows=flows)
        result = poll_build(auth, build_id)
        if result.get("status") != "error" or attempt >= session_retries:
            break
        attempt += 1
        print(f"Build errored before running (session could not start) - retry {attempt}/{session_retries}")

    summary = summarize_build(result, build_id, auth=auth, flows=flows)
    if reports:
        write_reports(summary)
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
    args = parser.parse_args()

    env = {}
    for item in args.env or []:
        if "=" not in item:
            parser.error(f"--env expects KEY=VALUE, got {item!r}")
        key, value = item.split("=", 1)
        env[key] = value

    summary = run_flows(flows=args.flows, env=env)
    print(json.dumps(summary["sessions"], indent=2, default=str)[:2000])
    sys.exit(0 if summary["status"] == "SUCCESS" else 1)


if __name__ == "__main__":
    main()
