"""Shared setup for the Opportunity Dashboard test modules (test_opd_dashboard,
test_opd_exports, test_opd_budget, test_opd_budget_mutations, test_opd_gaps):
open the configured OPD opportunity as PM and land on its dashboard, with a
retry-once-on-flake login.

The opportunity is always matched by EXACT name (or opened by id). If it is not
found the module SKIPS with a message naming what was looked for, so a wrong name
or a deleted opportunity shows up as a data problem in the report instead of the
suite quietly running against whatever the first row happens to be."""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage
from utils.helpers import with_page_size

PM_ORG_SLUG = "pm_automation_01"


def open_opd_dashboard(page, test_data, config, settings, *, names=None, opp_id=None, organization=PM_ORG):
    """Log in (as `organization`, default the PM org) and return the opportunity's
    dashboard page.

    opp_id: open the dashboard directly by id under the PM org slug.
    names:  candidate opportunity names, tried in order by EXACT match; defaults to
            [OPD.opportunity_name]. Skips the module if none is in the list.
    """
    connect_page = login_to_connect(page, config, settings, organization)
    dashboard = OpportunityDashboardPage(connect_page)

    if opp_id:
        connect_page.goto(f"{config.get('connect_url')}/a/{PM_ORG_SLUG}/opportunity/{opp_id}/")
        connect_page.wait_for_load_state("load")
    else:
        if names is None:
            names = [env_value(test_data.get("OPD"), "opportunity_name", config)]
        names = [n for n in names if n]
        # Load the whole list on one page so the flood of "Demo Opportunity_<date>" rows
        # doesn't hide the target.
        connect_page.goto(with_page_size(connect_page.url))
        connect_page.wait_for_load_state("load")
        olp = ConnectOpportunityListPage(connect_page)
        olp.verify_loaded()
        name = next((n for n in names if olp.has_opportunity(n, exact=True)), None)
        if name is None:
            pytest.skip(
                f"OPD opportunity not found by exact name in the {organization} list (looked for {names}) - "
                "check OPD.* in web_test_data.yaml / that the opportunity still exists"
            )
        olp.open_opportunity(name, exact=True)

    dashboard.verify_loaded()
    dashboard.dashboard_url = dashboard.page.url
    return dashboard


def dashboard_session(browser, config, settings, test_data, **open_kwargs):
    """Module-scoped fixture body: one authenticated session for the whole module -
    log in, open the OPD dashboard, yield it, close the context (logout) at the end.
    Login is retried once to absorb the occasional CommCareHQ login flake.
    `open_kwargs` go to open_opd_dashboard (names / opp_id / organization)."""
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            dash = open_opd_dashboard(page, test_data, config, settings, **open_kwargs)
        except Exception:
            page.close()
            page = context.new_page()
            dash = open_opd_dashboard(page, test_data, config, settings, **open_kwargs)
        yield dash
    finally:
        context.close()
