"""Opportunity Dashboard - read-only tier (OD_1-OD_19).

The dashboard is the page a user lands on after clicking an opportunity in the
list. This module covers the non-mutating cases: landing, the detail/stat panels
and graphs, panel drill-downs into the worker sub-tabs, the hamburger menu
contents, the read-only Learn/Deliver/Payment-units modal, and the inactive-worker
prefilter. All of it is safe to run identically on prod and staging - the mutating
cases (add budget, send message: OD_8-OD_17) are a separate module.

Every locator is derived from the Connect source (opportunity/templates,
opportunity_menu.html, opportunity_resource_modal.html, views.py delivery_stats,
tables.py, filters.py), not guessed against a live page.

Entry is the shared PM web account (PM_Automation_01) via flows.login_to_connect.
The opportunity is chosen from test data (OPD.opportunity_name, the seeded "Demo
Opportunity") with a fall-back to the first row so the suite is not seed-coupled.
"""

import pytest

from flows.opd_setup import dashboard_session

# PM hamburger items. NB the UI labels differ from the manual test case wording:
# "Verification Flags" renders as "Verification Rules" (the URL is still
# verification_flags_config) and "Add Worker Budget" as "Add Budget".
# "Add Connect Workers" only shows while the opportunity has not ended, so it is
# checked softly.
REQUIRED_HAMBURGER = [
    "Edit Opportunity",
    "Add Payment Unit",
    "View Invoices",
    "Add Budget",
    "Verification Rules",
    "Send Message",
    "Configure Task Types",
]
# "Add Connect Workers" only shows while the opportunity has not ended.
OPTIONAL_HAMBURGER = ["Add Connect Workers"]

# Summary info cards that are always present (opportunity config, not live counts).
SUMMARY_CARDS = ["Start Date", "End Date", "Max Connect Workers", "Max Service Deliveries", "Max Budget"]


@pytest.fixture(scope="module")
def dashboard(browser, config, settings, test_data):
    """One authenticated session for the whole module: log in, open the OPD
    dashboard, yield it to every test, then close the context (logout) at the end."""
    yield from dashboard_session(browser, config, settings, test_data)


def test_opd_01_02_land_on_dashboard_and_details(dashboard):
    """OD_1: selecting an opportunity lands on its dashboard.
    OD_2: the dashboard shows the opportunity detail cards, live stat panels and
    the funnel / worker-progress graphs."""
    dashboard.goto_dashboard()

    # OD_1 - landed on a dashboard (verify_loaded already asserted h1 + url).
    # OD_2 - opportunity config cards + status badge.
    dashboard.verify_summary_cards(SUMMARY_CARDS)
    dashboard.verify_status_badge()

    # OD_2 - live delivery stat panels (async HTMX). Counts may legitimately be 0
    # but must render (non-empty value node), so a fresh opportunity still passes.
    dashboard.wait_for_stats()
    dashboard.verify_stat_panels([
        ("Connect Workers", "Inactive last 3 days"),
        ("Services Delivered", "Total"),
        ("Payments", "Earned"),
        ("Payments", "Due"),
    ])

    # OD_2 - progress funnel + delivery/worker-progress graphs.
    dashboard.verify_graphs_present()


def test_opd_03_connect_workers_drilldown(dashboard):
    """OD_3: the Connect Workers button lands on the connect workers page."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()

    url = dashboard.click_stat_panel("connect_workers")
    assert "/workers/" in url, f"Connect Workers button did not open the workers page: {url}"


def test_opd_04_services_delivered_tab(dashboard):
    """OD_4: the Services Delivered button opens the deliver tab with its columns."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()

    url = dashboard.click_stat_panel("services_delivered")
    assert "/workers/deliver/" in url, f"Services Delivered did not open the deliver tab: {url}"
    dashboard.verify_worker_columns(["Name", "Delivered", "Approved", "Rejected"])


def test_opd_05_payments_tab(dashboard):
    """OD_5: the Payments Earned button opens the payments tab with its columns."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()

    url = dashboard.click_stat_panel("payments_earned")
    assert "/workers/payments/" in url, f"Payments Earned did not open the payments tab: {url}"
    dashboard.verify_worker_columns(["Accrued", "Total Paid", "Confirm"])


def test_opd_06_07_hamburger_menu_and_verification_flags(dashboard):
    """OD_6: the hamburger menu exposes the management options.
    OD_7: 'Verification Flags' opens the verification-flags config page (PM)."""
    dashboard.goto_dashboard()

    # OD_6
    options = dashboard.hamburger_options()
    joined = " | ".join(options)
    missing = [o for o in REQUIRED_HAMBURGER if o not in joined]
    assert not missing, f"Missing hamburger options {missing}. Present: {options}"
    present_optional = [o for o in OPTIONAL_HAMBURGER if o in joined]
    dashboard._step(f"Optional hamburger options present: {present_optional}")

    # OD_7 - the menu is already open; navigate to the verification rules page.
    dashboard.click_hamburger_item("Verification Rules")
    assert "verification_flags_config" in dashboard.page.url, (
        f"Verification Rules did not open the config page: {dashboard.page.url}"
    )


def test_opd_18_19_learn_deliver_payment_modal(dashboard):
    """OD_18: the Learn & Deliver apps modal shows app/module info (non-editable).
    OD_19: the Payment Units tab lists every payment unit with its details."""
    dashboard.goto_dashboard()

    dashboard.open_resource_modal()
    dashboard.verify_resource_tabs_present(["Learn App", "Deliver App", "Payment Units"])

    # OD_18 - Learn App modules.
    dashboard.select_resource_tab("Learn App")
    dashboard.verify_resource_columns(["Module Name", "Module Description"])

    # OD_18 - Deliver App units.
    dashboard.select_resource_tab("Deliver App")
    dashboard.verify_resource_columns(["Delivery Unit ID", "Name"])

    # OD_19 - Payment Units.
    dashboard.select_resource_tab("Payment Units")
    dashboard.verify_resource_columns(["Payment Unit Name", "Total Deliveries", "Delivery Units"])

    # OD_18 - the dialog is informational only.
    dashboard.verify_resource_modal_readonly()
    dashboard.close_resource_modal()


def test_opd_inactive_workers_prefilter(dashboard):
    """OD_18 (inactive-worker variant): the 'Inactive last 3 days' panel lands on
    the deliver page with the last_active=3 filter pre-applied."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()

    url = dashboard.click_stat_panel("inactive")
    assert "/workers/deliver/" in url, f"Inactive button did not open the deliver tab: {url}"
    assert dashboard.query_param("last_active") == "3", (
        f"Inactive prefilter not applied - last_active={dashboard.query_param('last_active')!r} in {url}"
    )

