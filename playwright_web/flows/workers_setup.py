"""Shared navigation for the Connect Workers module (Worker List View + Worker
Visit Verification Page). Migrated from the Selenium web_tests worker suite.

Entry is the shared PM web account (PM_Automation_01) via flows.login_to_connect,
exactly as the OPD and tasking modules do. The Selenium tests reached the workers
surfaces by clicking the opportunity in Connect and then a dashboard stat panel;
these helpers keep that path (list row -> dashboard -> stat panel) so the panel
links themselves stay exercised, rather than deep-linking by URL.
"""

from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def goto_opportunity_list(connect_page, opps_url):
    """Return to the Connect opportunity list before opening an opportunity.

    The module logs in once and each test opens a different opportunity, so a test
    that finished deep in a worker page must come back to the list first. opps_url
    is the list URL captured by the module fixture right after login/org-select.
    """
    olp = ConnectOpportunityListPage(connect_page)
    if "/opportunity" not in connect_page.url or connect_page.locator(olp.HEADING).count() == 0:
        connect_page.goto(opps_url)
        connect_page.wait_for_load_state("load")
    olp.verify_loaded()
    return olp


def open_opportunity_dashboard(connect_page, opportunity_name, opps_url=None):
    """From the Connect opportunity list, open `opportunity_name` and return its
    loaded OpportunityDashboardPage. Pass opps_url to re-navigate to the list first."""
    if opps_url is not None:
        olp = goto_opportunity_list(connect_page, opps_url)
    else:
        olp = ConnectOpportunityListPage(connect_page)
        olp.verify_loaded()
    assert connect_page.locator(olp.ROW_LINK_BY_NAME.format(name=opportunity_name)).count() > 0, (
        f"Opportunity '{opportunity_name}' is not in the list for this account/environment - "
        f"check the WORKER_* test data against the current env."
    )
    olp.open_opportunity(opportunity_name)

    dashboard = OpportunityDashboardPage(connect_page)
    dashboard.verify_loaded()
    dashboard.dashboard_url = connect_page.url
    return dashboard


def open_connect_workers(connect_page, opportunity_name, opps_url=None):
    """Reach the Connect Workers list (the default /workers/ view) via the
    dashboard's 'Connect Workers' stat panel - Selenium's navigate_to_connect_workers."""
    dashboard = open_opportunity_dashboard(connect_page, opportunity_name, opps_url)
    dashboard.wait_for_stats()
    dashboard.click_stat_panel("connect_workers")
    return dashboard


def open_deliver_tab(connect_page, opportunity_name, opps_url=None):
    """Reach the Deliver tab via the dashboard's 'Services Delivered' stat panel -
    Selenium's navigate_to_services_delivered."""
    dashboard = open_opportunity_dashboard(connect_page, opportunity_name, opps_url)
    dashboard.wait_for_stats()
    dashboard.click_stat_panel("services_delivered")
    return dashboard


def open_payments_tab(connect_page, opportunity_name, opps_url=None):
    """Reach the Payments tab via the dashboard's 'Payments Earned' stat panel -
    Selenium's navigate_to_payments_earned."""
    dashboard = open_opportunity_dashboard(connect_page, opportunity_name, opps_url)
    dashboard.wait_for_stats()
    dashboard.click_stat_panel("payments_earned")
    return dashboard
