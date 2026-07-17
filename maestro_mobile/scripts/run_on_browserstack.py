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


def summarize_build(result, build_id):
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
    with open("maestro_report.json", "w") as f:
        json.dump(summary, f, indent=2)

    rows = "".join(
        f"<tr><td>{s['device']}</td><td>{s['status']}</td><td>{s['duration_seconds']}s</td>"
        f"<td>{s['passed']}</td><td>{s['failed']}</td><td>{s['skipped']}</td></tr>"
        for s in summary["sessions"]
    )
    html = f"""<!DOCTYPE html>
<html><head><title>Maestro Mobile Report</title>
<style>body{{font-family:sans-serif;margin:2em}}table{{border-collapse:collapse}}
td,th{{border:1px solid #ccc;padding:6px 12px}}th{{background:#eee}}</style></head>
<body>
<h2>CommCare-Connect Maestro Mobile Report</h2>
<p><b>Status:</b> {summary['status']}</p>
<p><b>Flows:</b> {', '.join(summary['flows'])}</p>
<p><b>Totals:</b> {summary['passed']} passed, {summary['failed']} failed, {summary['skipped']} skipped</p>
<table><tr><th>Device</th><th>Status</th><th>Duration</th><th>Passed</th><th>Failed</th><th>Skipped</th></tr>
{rows}</table>
<p>Device video, step logs and screenshots:
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
    summary = summarize_build(result, build_id)
    write_reports(summary)
    sys.exit(0 if result.get("status") == "passed" else 1)


if __name__ == "__main__":
    main()
