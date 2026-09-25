"""Shared setup for the Opportunity Dashboard test modules (test_opd_dashboard,
test_opd_exports): open the configured OPD opportunity as PM and land on its
dashboard, with a retry-once-on-flake login."""

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage
from utils.helpers import with_page_size


def open_opd_dashboard(page, test_data, config, settings):
    """Log in as PM, open the configured OPD opportunity by exact name (falling
    back to the first row if it's missing), return its dashboard page."""
    connect_page = login_to_connect(page, config, settings, PM_ORG)

    # Load the whole list on one page so the flood of "Demo Opportunity_<date>" rows
    # doesn't hide the target, then open the configured opp by EXACT name so we don't
    # land on a look-alike dated row.
    connect_page.goto(with_page_size(connect_page.url))
    connect_page.wait_for_load_state("load")
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()

    name = env_value(test_data.get("OPD"), "opportunity_name", config)
    if name and olp.has_opportunity(name, exact=True):
        olp.open_opportunity(name, exact=True)
    else:
        olp._step(f"Exact opportunity {name!r} not found - falling back to first row (non-deterministic)")
        olp.open_opportunity(olp.first_row_name(), exact=True)

    dashboard = OpportunityDashboardPage(connect_page)
    dashboard.verify_loaded()
    dashboard.dashboard_url = dashboard.page.url
    return dashboard


def dashboard_session(browser, config, settings, test_data):
    """Module-scoped fixture body: one authenticated session for the whole module -
    log in, open the OPD dashboard, yield it, close the context (logout) at the end.
    Login is retried once to absorb the occasional CommCareHQ login flake."""
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            dash = open_opd_dashboard(page, test_data, config, settings)
        except Exception:
            page.close()
            page = context.new_page()
            dash = open_opd_dashboard(page, test_data, config, settings)
        yield dash
    finally:
        context.close()
