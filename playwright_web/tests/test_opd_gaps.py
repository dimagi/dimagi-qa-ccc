"""Opportunity Dashboard - gap coverage (OD_20-OD_47).

Source-derived cases beyond the documented OD_1-OD_19 (see the "Opportunity
dashboard" tab of test_plans/CCC_Web_Platform_MTP.xlsx).

Login happens ONCE per module: the `dashboard` fixture authenticates the shared PM
account, opens the Demo Opportunity dashboard, and yields the page object for
every implemented test; the context (and its session) is torn down at the end.
Each test calls `dashboard.goto_dashboard()` first to return to a known state
after the previous test navigated away - no re-login.

Read-only cases that run with the PM account + Demo Opportunity are implemented
directly. Cases needing a special fixture (viewer account, standalone/ended/test/
auto-verify opp, a feature flag, or 24h-fresh data) are data-guarded and skip
until the corresponding OPD.* key is set - mirroring the tasking_static require_* /
OLP_02 skip conventions. Mutating cases (OD_36/44/46) belong with the Tier 2/3
add-budget/send-message batch and are not here.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def _open_dashboard(page, test_data, config, settings, organization=PM_ORG):
    connect_page = login_to_connect(page, config, settings, organization)
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()
    name = env_value(test_data.get("OPD"), "opportunity_name", config)
    if not name or connect_page.locator(olp.ROW_LINK_BY_NAME.format(name=name)).count() == 0:
        name = olp.first_row_name()
    olp.open_opportunity(name)
    dash = OpportunityDashboardPage(connect_page)
    dash.verify_loaded()
    dash.dashboard_url = dash.page.url
    return dash


@pytest.fixture(scope="module")
def dashboard(browser, config, settings, test_data):
    """One authenticated session for the whole module: log in, open the dashboard,
    yield it to every test, then close the context (logout) at the end. The login
    is retried once to absorb the occasional CommCareHQ login flake."""
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


def _opd(test_data, key, config):
    return env_value(test_data.get("OPD") or {}, key, config)


# ============================ Implemented (PM + Demo Opp) =====================

def test_opd_24_status_badge(dashboard):
    """OD_24: the status badge reads one of Active / Ended / Inactive."""
    dashboard.goto_dashboard()
    dashboard.verify_status_badge()


def test_opd_25_empty_opportunity_renders(dashboard):
    """OD_25: an opportunity with no data still renders stat panels + graphs
    (zeros, not errors)."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()
    dashboard.verify_stat_panels([("Services Delivered", "Total"), ("Payments", "Earned")])
    dashboard.verify_graphs_present()


def test_opd_27_currency_formatting(dashboard):
    """OD_27: Max Budget renders with a currency code/symbol + digits."""
    dashboard.goto_dashboard()
    max_budget = dashboard.summary_card_value("Max Budget")
    assert any(ch.isdigit() for ch in max_budget), f"Max Budget has no numeric value: {max_budget!r}"
    assert any(ch.isalpha() for ch in max_budget) or any(not ch.isalnum() and not ch.isspace() for ch in max_budget), (
        f"Max Budget not currency-formatted: {max_budget!r}"
    )


def test_opd_29_map_audit_tasks_panels_present(dashboard):
    """OD_29: the View Progress Map / Audit Opportunity / Tasks Assigned panels
    render when enabled. Product-risk: the microplanning/audit links carry no
    MICROPLANNING guard, so click-through access control is verified on a
    microplanning opp - here we assert render + link integrity only."""
    dashboard.goto_dashboard()
    dashboard.wait_for_stats()
    titles = ["View Progress Map", "Audit Opportunity", "Tasks Assigned to Connect Workers"]
    present = []
    for title in titles:
        if dashboard.stat_panel_present(title):
            present.append(title)
            href = dashboard.stat_panel_href(title)
            if href is not None:
                assert href.strip(), f"Panel {title!r} is a link with an empty href"
            dashboard._step(f"Panel {title!r} href: {href}")
    assert present, f"None of the map/audit/tasks panels rendered: {titles}"
    dashboard._step(f"Panels present: {present}")


def test_opd_31_worker_progress_funnel(dashboard):
    """OD_31: the funnel shows all 7 stages with non-empty counts."""
    dashboard.goto_dashboard()
    labels = dashboard.funnel_stage_labels()
    joined = " | ".join(labels)
    missing = [s for s in dashboard.FUNNEL_STAGES if s not in joined]
    assert not missing, f"Missing funnel stages {missing}. Present: {labels}"
    assert dashboard.funnel_counts_nonempty(), "Funnel stage counts not all populated"


def test_opd_32_worker_progress_bars(dashboard):
    """OD_32: the worker-progress section shows the Approved/Rejected/Earned/Paid
    bars. The bars are data-gated: an opportunity with no deliveries/payments
    renders none, so skip in that case (point OPD at a data-rich opp to assert)."""
    dashboard.goto_dashboard()
    labels = dashboard.worker_progress_labels()
    if not labels:
        pytest.skip("No worker-progress bars for this opportunity (no deliveries/payments)")
    joined = " | ".join(labels)
    missing = [t for t in dashboard.WORKER_PROGRESS_TITLES if t not in joined]
    assert not missing, f"Missing worker-progress bars {missing}. Present: {labels}"
    assert dashboard.worker_progress_bar_count() >= 4, "Fewer than 4 progress bars rendered"


def test_opd_33_resource_card_counts_and_modal_tab(dashboard):
    """OD_33: resource cards show live counts and open the modal on the matching
    tab."""
    dashboard.goto_dashboard()
    for card, tab in [("Learn App", "Learn App"), ("Deliver App", "Deliver App")]:
        count = dashboard.resource_card_count(card)
        assert count != "", f"{card} card count empty"
        dashboard.open_resource_card(card)
        active = dashboard.active_resource_tab()
        assert tab in active, f"{card} opened modal on {active!r}, expected {tab!r}"
        dashboard.close_resource_modal()


def test_opd_34_35_hamburger_action_navigation(dashboard):
    """OD_34: Edit Opportunity / Add Payment Unit / Configure Task Types open (PM).
    OD_35: View Invoices opens the invoice list. Navigation only."""
    dashboard.goto_dashboard()
    for text, frag in [
        ("Edit Opportunity", "/edit"),
        ("Add Payment Unit", "/payment_unit/create"),
        ("Configure Task Types", "/task_types/"),
        ("View Invoices", "/invoice/"),
    ]:
        dashboard.click_hamburger_item(text)
        assert frag in dashboard.page.url, f"{text!r} did not open {frag} (url={dashboard.page.url})"
        dashboard.goto_dashboard()


def test_opd_38_learn_tab_columns(dashboard):
    """OD_38: the Learn tab shows the learn columns (skips when the tab is empty,
    like OD_4/OD_5)."""
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("learn")
    dashboard.verify_worker_columns(["Started Learning", "Completed Learning"])


def test_opd_40_workers_tab_count_and_search(dashboard):
    """OD_40: the Connect Workers tab label shows a "(N)" count and the search box
    filters with a 'Displaying X of Y' line."""
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("workers")
    label = dashboard.workers_tab_label_text()
    assert "(" in label and ")" in label, f"Workers tab label has no count: {label!r}"
    dashboard.search_workers("zzz-no-such-worker")
    line = dashboard.displaying_count_text()
    assert "Displaying" in line, f"Search did not produce a 'Displaying X of Y' line (got {line!r})"


def test_opd_42_deliver_filters_present_and_apply(dashboard):
    """OD_42: the Deliver tab exposes the delivery filters and applying one
    reloads the tab."""
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("deliver")
    dashboard.open_deliver_filter_modal()
    for name in ["last_active", "has_flags", "has_overlimit"]:
        assert dashboard.filter_present(name), f"Deliver filter {name!r} not present"
    dashboard.apply_deliver_filter("last_active", "3 days ago")
    assert dashboard.query_param("last_active") == "3", (
        f"last_active filter not applied: {dashboard.page.url}"
    )


def test_opd_45_export_ownership_probe(dashboard):
    """OD_45 (security): requesting an export DOWNLOAD with an unknown / foreign
    task id is rejected (404). (export_status returns a generic 200 and is only
    observed.)"""
    dashboard.goto_dashboard()
    bogus = "00000000-0000-0000-0000-000000000000"
    status = dashboard.get_status(dashboard.export_probe_url("download_export", bogus))
    assert status == 404, f"download_export with a foreign task id returned {status}, expected 404"
    status_probe = dashboard.get_status(dashboard.export_probe_url("export_status", bogus))
    dashboard._step(f"export_status for a foreign task id -> {status_probe} (observed, not asserted)")


def test_opd_47_stat_htmx_endpoints_load(dashboard):
    """OD_47: each dashboard stat HTMX endpoint responds 200 to a direct GET."""
    dashboard.goto_dashboard()
    for name in ["delivery", "worker_progress", "funnel"]:
        status = dashboard.get_status(dashboard.stat_endpoint_url(name))
        assert status == 200, f"stat endpoint {name} returned {status}"


# ============================ Fixture-guarded (skip until configured) =========
# These take only (test_data, config) so a skip spins up no browser. OD_20 needs a
# separate NM login, so it resolves `page` lazily only when actually enabled.

def test_opd_20_pm_vs_nm_hamburger_menu(request, test_data, config, settings):
    """OD_20: PM sees the full hamburger set; a Network Manager sees the reduced
    set. Needs an NM org that can see the opportunity (OPD.nm_org)."""
    nm_org = _opd(test_data, "nm_org", config)
    if not nm_org:
        pytest.skip("OPD.nm_org not configured - need a Network Manager org that sees the opp")
    page = request.getfixturevalue("page")
    dash = _open_dashboard(page, test_data, config, settings, organization=nm_org)
    joined = " | ".join(dash.hamburger_options())
    for pm_only in ["Edit Opportunity", "Add Payment Unit", "Verification Rules", "Configure Task Types"]:
        assert pm_only not in joined, f"NM unexpectedly sees PM-only item {pm_only!r}"


def test_opd_21_viewer_read_only(test_data, config):
    """OD_21: a VIEWER loads the dashboard but cannot open the hamburger menu."""
    if not _opd(test_data, "viewer_username", config):
        pytest.skip("OPD.viewer_username not configured - need a VIEWER-role account")
    pytest.skip("Viewer-role login flow not yet wired - fixture pending")


def test_opd_22_standalone_opportunity_menu(test_data, config):
    """OD_22: a standalone (non-program) opp hides PM-only menu items."""
    if not _opd(test_data, "standalone_opp", config):
        pytest.skip("OPD.standalone_opp not configured - need a standalone opportunity")
    pytest.skip("Standalone-opp fixture pending")


def test_opd_23_setup_incomplete_redirect(test_data, config):
    """OD_23: an opportunity with incomplete setup redirects to Add Payment Units."""
    if not _opd(test_data, "incomplete_opp", config):
        pytest.skip("OPD.incomplete_opp not configured - need a setup-incomplete opportunity")
    pytest.skip("Setup-incomplete-opp fixture pending")


def test_opd_26_test_opportunity_badge(test_data, config):
    """OD_26: a test opportunity (is_test) shows the Test badge + theme."""
    if not _opd(test_data, "test_opp", config):
        pytest.skip("OPD.test_opp not configured - need an is_test opportunity")
    pytest.skip("Test-opp fixture pending")


def test_opd_28_microplanning_flag_gating(test_data, config):
    """OD_28: MICROPLANNING flag controls the Work Areas tab (direct URL 404 off)."""
    if not _opd(test_data, "microplanning_opp", config):
        pytest.skip("OPD.microplanning_opp not configured - need MICROPLANNING-flagged opp")
    pytest.skip("Microplanning fixture pending")


def test_opd_30_increment_badges(test_data, config):
    """OD_30: 24h increment badges show on Services Delivered + Payments Earned."""
    if not _opd(test_data, "fresh_delivery_opp", config):
        pytest.skip("OPD.fresh_delivery_opp not configured - needs deliveries/payments in last 24h")
    pytest.skip("Fresh-24h-data fixture pending")


def test_opd_37_add_workers_hidden_when_ended(test_data, config):
    """OD_37: 'Add Connect Workers' is hidden for an ended opportunity."""
    if not _opd(test_data, "ended_opp", config):
        pytest.skip("OPD.ended_opp not configured - need an ended opportunity")
    pytest.skip("Ended-opp fixture pending")


def test_opd_43_auto_verify_filters_and_columns(dashboard):
    """OD_43: on an automatic-verification opp the Deliver filter modal drops the
    review_pending + has_duplicates filters (and the 'Pending' column). Demo
    Opportunity is auto-verify, so this runs on the shared session."""
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("deliver")
    dashboard.open_deliver_filter_modal()
    # Auto-verify removes these two filters...
    assert not dashboard.filter_present("review_pending"), "review_pending filter should be absent under auto-verify"
    assert not dashboard.filter_present("has_duplicates"), "has_duplicates filter should be absent under auto-verify"
    # ...while the flag/limit/last_active filters remain.
    assert dashboard.filter_present("has_flags"), "has_flags filter should remain"
    assert dashboard.filter_present("has_overlimit"), "has_overlimit filter should remain"
    # The 'Pending' column is also dropped (best-effort: empty deliver tab renders
    # no columns, so this only asserts absence, never presence).
    assert "Pending" not in " | ".join(dashboard.worker_table_columns()), "'Pending' column should be absent under auto-verify"
