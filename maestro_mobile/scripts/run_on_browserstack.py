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


def main():
    auth = get_credentials()
    app_url = upload_app(auth)
    test_suite_url = upload_test_suite(auth)
    build_id = trigger_build(auth, app_url, test_suite_url)
    result = poll_build(auth, build_id)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("status") == "passed" else 1)


if __name__ == "__main__":
    main()
