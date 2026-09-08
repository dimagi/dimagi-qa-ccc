"""Opportunity Dashboard - Tier 2/3, deterministic subset (OD_8/9/13/16/17).

The mutating budget cases (OD_10/11/12/14/15 - actually changing visits) are a
separate follow-up that mutates-then-reverts on staging. This module covers only
the parts that are safe and deterministic on any environment: reaching the Send
Message and Add Connect Workers pages, the number-of-visits min=1 validation, the
confirm modal's computed visit count, and the new-workers total-budget auto-calc.
None of these submit, so nothing is mutated.

Locators derived from the Connect source (opportunity_menu.html,
add_visits_existing_users.html, send_message.html), not guessed. One login per
module via the shared PM account, same shape as test_opd_dashboard.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def _open_dashboard(page, test_data, config, settings):
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()
    # Prefer an opportunity with claimed workers (budget/message forms only render
    # then); fall back to the read-only opp, then the first row.
    name = env_value(test_data.get("OPD"), "budget_opportunity_name", config) or env_value(
        test_data.get("OPD"), "opportunity_name", config
    )
    if not name or connect_page.locator(olp.ROW_LINK_BY_NAME.format(name=name)).count() == 0:
        olp._step(f"Configured opportunity {name!r} not in list - falling back to first row")
        name = olp.first_row_name()
    olp.open_opportunity(name)
    dashboard = OpportunityDashboardPage(connect_page)
    dashboard.verify_loaded()
    dashboard.dashboard_url = dashboard.page.url
    return dashboard


@pytest.fixture(scope="module")
def dashboard(browser, config, settings, test_data):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            dash = _open_dashboard(page, test_data, config, settings)
        except Exception:
            page.close()
            page = context.new_page()
            dash = _open_dashboard(page, test_data, config, settings)
        yield dash
    finally:
        context.close()


def test_opd_08_send_message_page(dashboard):
    """OD_8 (web) - the Send Message option opens a page ready to send. (The mobile
    push + notification-history checks are mobile-only and out of web scope.)"""
    dashboard.goto_dashboard()
    dashboard.open_send_message()
    assert "send_message" in dashboard.page.url, dashboard.page.url
    if not dashboard.send_message_page_ready():
        pytest.skip("Send Message page has no Confirm control - opportunity has no mobile users")


def test_opd_09_add_connect_workers_redirect(dashboard):
    """OD_9 - the Add Connect Workers option redirects to the invite page."""
    dashboard.goto_dashboard()
    if "Add Connect Workers" not in dashboard.hamburger_options():
        pytest.skip("Add Connect Workers not offered (opportunity may have ended)")
    dashboard.open_add_connect_workers()
    assert "user_invite" in dashboard.page.url, dashboard.page.url
    assert dashboard.is_displayed("#id_users", timeout=10000), "Invite page should expose the users input"


def test_opd_13_negative_visits_validation(dashboard):
    """OD_13 - a value below 1 in Number of Visits fails min=1 validation."""
    dashboard.goto_add_budget()
    if not dashboard.add_budget_has_claimed_workers():
        pytest.skip("Opportunity has no claimed workers - the visits form is not rendered")
    validity = dashboard.visits_field_validity(-1)
    assert not validity["valid"] and validity["rangeUnderflow"], validity
    assert "greater than or equal to 1" in (validity["message"] or ""), validity["message"]


def test_opd_16_confirm_modal_shows_computed_visits(dashboard):
    """OD_16 - the confirm modal reflects the entered visits (no submit)."""
    dashboard.goto_add_budget()
    if not dashboard.add_budget_has_claimed_workers():
        pytest.skip("Opportunity has no claimed workers - cannot open the budget confirm modal")
    text = dashboard.open_budget_confirm_modal(visits=2, adjustment="increase_visits")
    lowered = text.lower()
    assert "increase" in lowered and "visit" in lowered, text
    assert "2" in text, f"Confirm modal should show the entered visit count: {text!r}"


def test_opd_17_new_workers_autocalc_total_budget(dashboard):
    """OD_17 - entering a new-worker count auto-updates the total budget."""
    dashboard.goto_add_budget()
    dashboard.open_new_workers_tab()
    before = int(dashboard.total_budget_value() or 0)
    dashboard.set_new_workers_count(2)
    after = int(dashboard.total_budget_value() or 0)
    assert after > before, f"total_budget should increase with added workers (before={before}, after={after})"
