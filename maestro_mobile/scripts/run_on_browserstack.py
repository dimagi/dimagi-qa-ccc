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
    response.raise_for_status()
    app_url = response.json()["app_url"]
    print(f"App uploaded: {app_url}")
    return app_url


def upload_test_suite(auth):
    zip_path = FLOWS_DIR.parent / "flows.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for file in FLOWS_DIR.iterdir():
            if file.is_file():
                # BrowserStack requires every file to sit inside a single root folder within the zip.
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

    response.raise_for_status()
    test_suite_url = response.json()["test_suite_url"]
    print(f"Test suite uploaded: {test_suite_url}")
    return test_suite_url


def trigger_build(auth, app_url, test_suite_url):
    body = {
        "app": app_url,
        "testSuite": test_suite_url,
        "project": PROJECT_NAME,
        "devices": [DEVICE],
        "execute": TEST_FLOWS,
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


def summarize_build(result, build_id, auth=None):
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
        "flows": TEST_FLOWS,
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

    rows = "".join(
        f"<tr><td>{s['device']}</td><td>{s['status']}</td><td>{s['duration_seconds']}s</td>"
        f"<td>{s['passed']}</td><td>{s['failed']}</td><td>{s['skipped']}</td></tr>"
        for s in summary["sessions"]
    )

    flow_sections = ""
    for session in summary["sessions"]:
        for flow in session.get("flows", []):
            badge = "#2e7d32" if flow["status"] == "passed" else "#c62828"
            shots = "".join(
                f"<figure><img src='data:image/png;base64,{shot['base64']}' alt='{shot['name']}'>"
                f"<figcaption>{shot['name']}</figcaption></figure>"
                for shot in flow.get("screenshots", [])
            )
            log_text = (flow.get("log") or "").replace("<", "&lt;").replace(">", "&gt;")
            flow_sections += f"""
<h3>{flow['name']} <span style="color:{badge}">[{flow['status']}]</span>
<small>({flow['duration_seconds']}s on {session['device']})</small></h3>
<details><summary>Maestro step log</summary><pre>{log_text}</pre></details>
<details><summary>Screenshots ({len(flow.get('screenshots', []))})</summary>
<div class="shots">{shots}</div></details>"""

    html = f"""<!DOCTYPE html>
<html><head><title>Maestro Mobile Report</title>
<style>body{{font-family:sans-serif;margin:2em;max-width:70em}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:6px 12px}}th{{background:#eee}}
pre{{background:#f6f6f6;padding:1em;overflow-x:auto;max-height:30em}}
.shots{{display:flex;flex-wrap:wrap;gap:1em}}
.shots img{{max-width:280px;border:1px solid #ccc}}
figure{{margin:0}}figcaption{{font-size:0.8em;color:#666;text-align:center}}</style></head>
<body>
<h2>CommCare-Connect Maestro Mobile Report</h2>
<p><b>Status:</b> {summary['status']}</p>
<p><b>Flows:</b> {', '.join(summary['flows'])}</p>
<p><b>Totals:</b> {summary['passed']} passed, {summary['failed']} failed, {summary['skipped']} skipped</p>
<table><tr><th>Device</th><th>Status</th><th>Duration</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr>
{rows}</table>
{flow_sections}
<p>Device video (requires BrowserStack access):
<a href="{summary['build_url']}">{summary['build_url']}</a></p>
</body></html>"""
    with open("maestro_report.html", "w") as f:
        f.write(html)
    print("Reports written: maestro_report.json, maestro_report.html")


def main():
    auth = get_credentials()
    app_url = upload_app(auth)
    test_suite_url = upload_test_suite(auth)
    build_id = trigger_build(auth, app_url, test_suite_url)
    result = poll_build(auth, build_id)
    print(json.dumps(result, indent=2))
    summary = summarize_build(result, build_id, auth=auth)
    write_reports(summary)
    sys.exit(0 if result.get("status") == "passed" else 1)


if __name__ == "__main__":
    main()
