import os
from pathlib import Path

from appium import webdriver
from appium.options.android import UiAutomator2Options
import requests
from requests.auth import HTTPBasicAuth

from utils.helpers import PROJECT_ROOT


def create_mobile_driver(config, settings, run_on, request):
    caps = config.caps(run_on)

    options = UiAutomator2Options()
    if run_on == "browserstack":

        # Credentials
        bs_user = settings.get(
            section="browserstack",
            key="BROWSERSTACK_USERNAME",
            env_var="BROWSERSTACK_USERNAME"
            )
        bs_key = settings.get(
            section="browserstack",
            key="BROWSERSTACK_ACCESS_KEY",
            env_var="BROWSERSTACK_ACCESS_KEY"
            )

        if not bs_user or not bs_key:
            raise Exception("BrowserStack credentials not set")

        # 🔥 Determine APK based on env
        env = config.env.lower()
        project_root = PROJECT_ROOT

        if env == "prod":
            apk_path = os.path.join(project_root, "app", "app-commcare-release.apk")
        elif env == "stage":
            apk_path = os.path.join(project_root, "app", "app-cccStaging-release.apk")
        else:
            raise Exception(f"Unknown env: {env}")

        # 🔥 Upload dynamically
        # custom_id = f"commcare_{env}"

        bs_app_url = bstack_upload_apk_with_curl(
            apk_path=apk_path,
            bs_user=bs_user,
            bs_key=bs_key
            )

        options.set_capability("app", bs_app_url)

        test_name = request.node.name
        dynamic_session_name = f"Connect Tests - {env.upper()} - {test_name}"
        # dynamic_build_name = f"PID Regression - {env.upper()}"

        bstack_opts = caps.get("bstack:options", {}).copy()
        bstack_opts["userName"] = bs_user
        bstack_opts["accessKey"] = bs_key
        bstack_opts["sessionName"] = dynamic_session_name
        options.set_capability("bstack:options", bstack_opts)

    # Set remaining capabilities (avoid overriding bstack:options)
    for key, value in caps.items():
        if key != "bstack:options":
            options.set_capability(key, value)

    # 3Create driver with correct hub URL
    driver = webdriver.Remote(
        command_executor=config.get(
            "browserstack_url" if run_on == "browserstack" else "appium_local_url"
        ),
        options=options
    )

    return driver


def bstack_upload_apk_with_curl(apk_path: str, bs_user: str, bs_key: str, custom_id: str | None = None) -> str:
    apk_path = os.path.abspath(apk_path)

    if not os.path.exists(apk_path):
        raise RuntimeError(f"APK not found at: {apk_path}")

    url = "https://api-cloud.browserstack.com/app-automate/upload"

    with open(apk_path, "rb") as apk_file:
        response = requests.post(
            url,
            auth=HTTPBasicAuth(bs_user, bs_key),
            files={"file": apk_file},
            timeout=900
        )

    if response.status_code != 200:
        raise RuntimeError(f"Upload failed: {response.text}")

    payload = response.json()

    app_url = payload.get("app_url")
    if isinstance(app_url, str) and app_url.startswith("bs://"):
        return app_url

    raise RuntimeError(f"Unexpected BrowserStack response: {payload}")