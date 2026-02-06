import os

import allure
import pytest
from allure_commons.types import AttachmentType

from utils.helpers import ConfigLoader, SettingsLoader
from drivers.appium_driver import create_mobile_driver
from drivers.web_driver import create_web_driver
from utils.reporting import attach_mobile_screenshot, attach_web_screenshot
from utils.helpers import TestDataLoader


# Load environment (prod/stage)
def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Environment to run tests against: prod or stage"
    )
    # parser.addoption(
    #     "--run_on",
    #     action="store",
    #     default="browserstack",
    #     help="Execution target: local or browserstack")


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
    # return request.config.getoption("--run_on")


# MOBILE DRIVER FIXTURE (only created if test needs it)
@pytest.fixture
def mobile_driver(request, config, settings, run_on):
    # only create the driver if the test asks for it
    if "mobile" not in request.keywords:
        yield None
        return None

    driver = create_mobile_driver(config, settings, run_on)
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


# Attach screenshots on failure (mobile & web)
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item):
    outcome = yield
    result = outcome.get_result()

    if result.when == "call" and result.failed:
        # Attach failure reason
        allure.attach(
            str(result.longrepr),
            name="Failure Reason",
            attachment_type=AttachmentType.TEXT
        )

        # Attach screenshots
        mobile = item.funcargs.get("mobile_driver")
        web = item.funcargs.get("web_driver")

        try:
            if mobile:
                attach_mobile_screenshot(mobile, "Mobile Failure Screenshot")

            if web:
                attach_web_screenshot(web, "Web Failure Screenshot")

        except Exception as e:
            print(f"take screenshot failed {e}")

    # Append Bugasura TC IDs to test name in xml results
    marker = item.get_closest_marker("bugasura")
    if marker:
        tc_ids = ",".join(marker.args)
        result.user_properties.append(("bugasura_tc_ids", tc_ids))
        result.nodeid = f"[{tc_ids}]{item.name}"


@pytest.fixture(scope="session")
def test_data():
    return TestDataLoader()
