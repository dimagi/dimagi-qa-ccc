import base64

import pytest

from utils.helpers import ConfigLoader, SettingsLoader, TestDataLoader


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default="stage",
        help="Environment to run tests against: prod or stage (defaults to stage)",
    )


@pytest.fixture(scope="session")
def config(request):
    return ConfigLoader(request.config.getoption("--env"))


@pytest.fixture(scope="session")
def settings():
    return SettingsLoader()


@pytest.fixture(scope="session")
def test_data():
    return TestDataLoader()


def pytest_html_results_summary(prefix):
    """Drop the report's sticky view state so every open starts failures-first.

    pytest-html remembers the sort direction in sessionStorage and mirrors sort
    and collapse choices into the URL, so a reader who clicked around once can
    reopen the report with failures sorted last and rows collapsed. Clearing
    those keys before the report's own script runs makes the ordering from
    pytest.ini (initial_sort / render_collapsed) win every time.
    """
    prefix.append(
        "<script>try {"
        " sessionStorage.removeItem('sortAsc');"
        " sessionStorage.removeItem('collapsedIds');"
        " const url = new URL(window.location.href);"
        " if (url.searchParams.has('sort') || url.searchParams.has('collapsed')) {"
        "   url.searchParams.delete('sort'); url.searchParams.delete('collapsed');"
        "   window.history.replaceState({}, '', url.href);"
        " }"
        "} catch (e) {}</script>"
    )


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Embed screenshots of every open page into the pytest-html report on failure."""
    outcome = yield
    report = outcome.get_result()

    if report.when != "call" or not report.failed:
        return
    pytest_html = item.config.pluginmanager.getplugin("html")
    if pytest_html is None:
        return
    page = item.funcargs.get("page")
    if page is None:
        return

    extras = getattr(report, "extras", [])
    try:
        # Tests may open extra tabs (e.g. the Connect page) - capture all of them.
        for open_page in page.context.pages:
            image = base64.b64encode(open_page.screenshot(full_page=True)).decode()
            extras.append(pytest_html.extras.image(image, mime_type="image/png"))
    except Exception as exc:  # never let reporting break the test run
        extras.append(pytest_html.extras.text(f"Could not capture failure screenshot: {exc}"))
    report.extras = extras
