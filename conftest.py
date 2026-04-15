import os
import base64
from io import BytesIO
from pathlib import Path

import allure
import pytest
from pytest_html import extras
from allure_commons.types import AttachmentType
from utils.helpers import ConfigLoader, SettingsLoader

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from PIL import Image
    _CHARTS_AVAILABLE = True
except ImportError:
    _CHARTS_AVAILABLE = False
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
    #
    # # Sign out so the next test always starts from a logged-out state,
    # # while noReset:true (BrowserStack) keeps the FCM token intact.
    # if run_on == "browserstack":
    #     try:
    #         from pages.mobile_pages.home_page import HomePage
    #         home = HomePage(driver)
    #         if home.is_displayed(home.HEADER_USERNAME, timeout=5):
    #             home.sign_out()
    #     except Exception as e:
    #         print(f"[WARN] Sign-out in teardown failed: {e}")

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


# ─── Summary Charts ──────────────────────────────────────────────────────────

_test_stats: dict = {}


def pytest_sessionfinish(session, exitstatus):
    if not _CHARTS_AVAILABLE:
        print("[charts] matplotlib/Pillow not installed — skipping chart generation.")
        return
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if not tr:
        return
    global _test_stats
    _test_stats = {
        "passed":  len(tr.stats.get("passed",  [])),
        "failed":  len(tr.stats.get("failed",  [])),
        "skipped": len(tr.stats.get("skipped", [])),
        "error":   len(tr.stats.get("error",   [])),
        "reruns":  len(tr.stats.get("rerun",   [])),
    }
    _save_summary_charts(_test_stats)


def _save_summary_charts(stats: dict) -> None:
    out_dir = Path("slack_charts")
    out_dir.mkdir(exist_ok=True)

    passed  = stats.get("passed",  0)
    failed  = stats.get("failed",  0)
    skipped = stats.get("skipped", 0)
    reruns  = stats.get("reruns",  0)

    # Donut pie chart
    fig, ax = plt.subplots()
    wedges, _ = ax.pie(
        [passed, failed, skipped],
        labels=None,
        colors=["#66bb6a", "#ef5350", "#fad000"],
        startangle=90,
        wedgeprops=dict(width=0.4),
    )
    ax.axis("equal")
    ax.set_title("Test Summary")
    ax.legend(
        [f"Passed: {passed}", f"Failed: {failed}", f"Skipped: {skipped}"],
        loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.15),
    )
    fig.savefig(out_dir / "summary_pie.png", bbox_inches="tight")
    plt.close(fig)

    # Bar chart — only when there are failures or reruns
    bar_path = None
    if failed > 0 or reruns > 0:
        fig, ax = plt.subplots()
        bars = ax.bar(["Failed", "Reruns"], [failed, reruns], color=["#ef5350", "#ffa726"])
        ax.set_ylabel("Number of Tests")
        ax.set_title("Failures and Reruns")
        ax.legend(bars, [f"Failed: {failed}", f"Reruns: {reruns}"],
                  loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.15))
        bar_path = out_dir / "summary_bar.png"
        fig.savefig(bar_path, bbox_inches="tight")
        plt.close(fig)

    _combine_charts(out_dir / "summary_pie.png", bar_path, out_dir / "summary_combined.png")


def _combine_charts(pie_path: Path, bar_path, combined_path: Path) -> None:
    pie = Image.open(pie_path)
    if bar_path and bar_path.exists():
        bar = Image.open(bar_path)
        bar = bar.resize((bar.width * pie.height // bar.height, pie.height))
        combined = Image.new("RGB", (pie.width + bar.width, pie.height), (255, 255, 255))
        combined.paste(pie, (0, 0))
        combined.paste(bar, (pie.width, 0))
    else:
        combined = pie.copy()
    combined.save(combined_path)
    print(f"[charts] Combined chart saved: {combined_path}")


def _matplotlib_img(fig) -> str:
    buf = BytesIO()
    plt.tight_layout()
    fig.savefig(buf, format="png")
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def pytest_html_results_summary(prefix, summary, postfix, session):
    if not _CHARTS_AVAILABLE:
        return
    tr = session.config.pluginmanager.get_plugin("terminalreporter")
    if not tr:
        return
    stats = tr.stats if hasattr(tr, "stats") else {}

    passed  = len(stats.get("passed",  []))
    failed  = len(stats.get("failed",  []))
    skipped = len(stats.get("skipped", []))
    reruns  = len(stats.get("rerun",   []))

    # Donut pie
    fig, ax = plt.subplots()
    wedges, _ = ax.pie(
        [passed, failed, skipped],
        labels=None,
        colors=["#66bb6a", "#ef5350", "#fad000"],
        startangle=90,
        wedgeprops=dict(width=0.4),
    )
    ax.axis("equal")
    plt.legend(wedges,
               [f"Passed: {passed}", f"Failed: {failed}", f"Skipped: {skipped}"],
               title="Results", loc="upper center",
               bbox_to_anchor=(0.5, -0.08), ncol=3)
    pie_img = _matplotlib_img(fig)

    # Bar chart
    bar_img = None
    if failed > 0 or reruns > 0:
        fig, ax = plt.subplots()
        bars = ax.bar(["Failed", "Reruns"], [failed, reruns], color=["#ef5350", "#ff9933"])
        ax.set_title("Failures and Reruns")
        ax.set_ylabel("Number of Tests")
        plt.legend(bars, [f"Failed: {failed}", f"Reruns: {reruns}"],
                   loc="upper center", bbox_to_anchor=(0.5, -0.12), ncol=2)
        bar_img = _matplotlib_img(fig)

    html = "<div style='text-align:center; margin-top:20px;'>"
    html += f"<h3>Test Summary</h3><img src='data:image/png;base64,{pie_img}' style='max-width:500px;'/>"
    if bar_img:
        html += f"<h3>Failures and Reruns</h3><img src='data:image/png;base64,{bar_img}' style='max-width:500px;'/>"
    html += "</div>"
    summary.append(html)
