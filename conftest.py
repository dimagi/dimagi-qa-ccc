import os

import allure
import pytest
from pytest_html import extras
from allure_commons.types import AttachmentType
import base64
from utils.helpers import ConfigLoader, SettingsLoader
from drivers.appium_driver import create_mobile_driver
from drivers.web_driver import create_web_driver
# from utils.reporting import attach_mobile_screenshot, attach_web_screenshot
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


# Attach screenshots on failure (mobile & web)
# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item):
#     outcome = yield
#     result = outcome.get_result()
#
#     if result.when == "call" and result.failed:
#         # Attach failure reason
#         allure.attach(
#             str(result.longrepr),
#             name="Failure Reason",
#             attachment_type=AttachmentType.TEXT
#         )
#
#         # Attach screenshots
#         mobile = item.funcargs.get("mobile_driver")
#         web = item.funcargs.get("web_driver")
#
#         try:
#             if mobile:
#                 attach_mobile_screenshot(mobile, "Mobile Failure Screenshot")
#
#             if web:
#                 attach_web_screenshot(web, "Web Failure Screenshot")
#
#         except Exception as e:
#             print(f"take screenshot failed {e}")
#
#     # Append Bugasura TC IDs to test name in xml results
#     marker = item.get_closest_marker("bugasura")
#     if marker:
#         tc_ids = ",".join(marker.args)
#         result.user_properties.append(("bugasura_tc_ids", tc_ids))
#         result.nodeid = f"[{tc_ids}]{item.name}"

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

# @pytest.hookimpl(hookwrapper=True)
# def pytest_runtest_makereport(item):
#     pytest_html = item.config.pluginmanager.getplugin("html")
#
#     outcome = yield
#     report = outcome.get_result()
#
#     if report.when not in ("call", "setup"):
#         return
#
#     if report.failed:
#         mobile = getattr(item, "mobile_driver", None)
#         web = getattr(item, "web_driver", None)
#
#         extra = getattr(report, "extra", [])
#
#         def capture(driver):
#             if not driver:
#                 return None
#             try:
#                 driver.execute_script("return 1")
#                 png = driver.get_screenshot_as_png()
#                 return png
#             except Exception as e:
#                 print(f"[WARN] Screenshot failed: {e}")
#                 return None
#
#         for driver in [mobile, web]:
#             png = capture(driver)
#             if png:
#                 # ✅ Allure
#                 allure.attach(
#                     png,
#                     name="Failure Screenshot",
#                     attachment_type=AttachmentType.PNG
#                 )
#
#                 # ✅ pytest-html (base64 embed)
#                 if pytest_html:
#                     screen_img = _capture_screenshot(driver)
#                     html_img = (
#                             '<div><img src="data:image/png;base64,%s" alt="screenshot" '
#                             'style="width:600px;height:300px;" '
#                             'onclick="window.open(this.src)" align="right"/></div>'
#                             % screen_img
#                     )
#                     extra.append(pytest_html.extras.html(html_img))
#
#         report.extra = extra

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
