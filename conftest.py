import os

import allure
import pytest
from pytest_html import extras
from allure_commons.types import AttachmentType
import base64
from utils.helpers import ConfigLoader, SettingsLoader
from drivers.appium_driver import create_mobile_driver
from drivers.web_driver import create_web_driver
from utils.helpers import TestDataLoader
from selenium.common import TimeoutException, WebDriverException


# Load environment (prod/stage)
def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Environment to run tests against: prod or stage"
    )


@pytest.fixture(scope="session")
def config(request):
    env = request.config.getoption("--env")
    return ConfigLoader(env)

@pytest.fixture(scope="session")
def settings():
    return SettingsLoader()

@pytest.fixture(scope="session")
def run_on(settings):
    env_value = os.getenv("RUN_ON")
    if env_value:
        return env_value.lower()

    # 2️⃣ Local settings.cfg
    return settings.get(
        section="execution",
        key="run_on",
        default="local"
        )


# MOBILE DRIVER FIXTURE (only created if test needs it)
@pytest.fixture
def mobile_driver(request, config, settings, run_on):
    # only create the driver if the test asks for it
    if "mobile" not in request.keywords:
        yield None
        return None

    driver = create_mobile_driver(config, settings, run_on, request)
    driver.run_on = run_on
    yield driver
    try:
        driver.terminate_app("org.commcare.dalvik")
    except Exception as e:
        print(f"[WARN] App terminate failed: {e}")

    driver.quit()


# WEB DRIVER FIXTURE (only created if test needs it)
@pytest.fixture
def web_driver(request, config):
    if "web" not in request.keywords:
        yield None
        return None

    driver = create_web_driver()
    yield driver
    driver.quit()


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    pytest_html = item.config.pluginmanager.getplugin("html")

    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:

        mobile_driver = item.funcargs.get("mobile_driver")
        web_driver = item.funcargs.get("web_driver")

        extra = getattr(report, "extra", [])

        def attach(driver, label):
            if not driver:
                return
            try:
                png = driver.get_screenshot_as_png()
                if not png:
                    return

                # ✅ Allure (raw bytes)
                allure.attach(
                    png,
                    name=label,
                    attachment_type=AttachmentType.PNG
                )

                # ✅ pytest-html (base64 string)
                if pytest_html:
                    b64 = base64.b64encode(png).decode("utf-8")
                    extra.append(pytest_html.extras.image(b64))

            except Exception as e:
                print(f"[WARN] Screenshot failed: {e}")

        attach(mobile_driver, "Mobile Screenshot")
        attach(web_driver, "Web Screenshot")

        report.extra = extra

def _capture_screenshot(driver):
    if not driver:
        return None
    try:
        # quick health check; fails fast if renderer is dead
        driver.execute_script("return 1")
        png = driver.get_screenshot_as_png()
        return base64.b64encode(png).decode("utf-8")
    except (TimeoutException, WebDriverException, Exception) as e:
        print(f"[WARN] Screenshot capture failed (ignored): {type(e).__name__}: {e}")
        return None

@pytest.fixture(scope="session")
def test_data():
    return TestDataLoader()
