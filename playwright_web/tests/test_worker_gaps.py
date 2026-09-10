"""Gap-derived worker-page cases promoted from Gap Analysis (GAP-SRC-W-46/49/52).

  GAP-SRC-W-46 - the per-worker profile page shows its KPI header tiles
  GAP-SRC-W-49 - the Work Area Assignments tab is present + reachable under the
                 MICROPLANNING flag (covid_opp_test has it on)
  GAP-SRC-W-52 - the Payments tab currency columns carry a currency-code suffix

All read-only, against the data-rich covid_opp_test opportunity.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import (
    open_connect_workers,
    open_deliver_tab,
    open_opportunity_dashboard,
    open_payments_tab,
)
from pages.connect_opportunity_list_page import ConnectOpportunityListPage
from pages.connect_workers_page import ConnectWorkersPage

OPP = "covid_opp_test"
WORKER = "Deb Test 8/12"


@pytest.fixture(scope="module")
def connect(browser, config, settings):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        except Exception:
            page.close()
            page = context.new_page()
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        connect_page.wait_for_load_state("load")
        yield connect_page, connect_page.url
    finally:
        context.close()


def test_src_w_46_worker_profile_kpis(connect):
    """GAP-SRC-W-46: the per-worker profile page shows the KPI header tiles."""
    connect_page, opps_url = connect
    workers = ConnectWorkersPage(connect_page)
    open_deliver_tab(connect_page, OPP, opps_url)
    workers.navigate_to_worker_visits(WORKER)
    workers.verify_worker_profile_kpis()


def test_src_w_49_work_area_tab_present(connect):
    """GAP-SRC-W-49: the Work Area Assignments tab is present and reachable when
    MICROPLANNING is on."""
    connect_page, opps_url = connect
    workers = ConnectWorkersPage(connect_page)
    open_connect_workers(connect_page, OPP, opps_url)
    workers.verify_work_area_tab_present()


def test_src_w_50_cross_tab_filter_persistence(connect):
    """GAP-SRC-W-50: a Deliver-tab filter persists when navigating between worker
    tabs, but is cleared when the Deliver tab is entered from an unrelated page."""
    connect_page, opps_url = connect
    workers = ConnectWorkersPage(connect_page)

    open_deliver_tab(connect_page, OPP, opps_url)
    workers.clear_all_filters_deliver_table()
    workers.open_filter_modal()
    workers.select_by_visible_text(workers.FILTER_LAST_ACTIVE, "3 days ago")
    workers.apply_filters()
    assert workers.filter_badge_count() == 1, "Filter did not apply"

    # Hop to another worker tab and back - the filter should persist (session).
    workers.click_tab_by_name("Learn")
    workers.click_tab_by_name("Deliver")
    persisted = workers.filter_badge_count()
    print("BADGE AFTER TAB HOP:", persisted)
    assert persisted == 1, "Filter did not persist across worker-tab navigation"

    # Re-enter the Deliver tab from the dashboard (unrelated) - filter cleared.
    open_deliver_tab(connect_page, OPP, opps_url)
    cleared = workers.filter_badge_count()
    print("BADGE AFTER DASHBOARD RE-ENTRY:", cleared)
    assert cleared == 0, "Filter should be cleared when entering from an unrelated page"


def test_src_w_52_payments_currency_headers(connect):
    """GAP-SRC-W-52: the Payments tab currency columns carry a currency-code suffix."""
    connect_page, opps_url = connect
    workers = ConnectWorkersPage(connect_page)
    open_payments_tab(connect_page, OPP, opps_url)
    workers.verify_tab_active("Payments")
    workers.verify_payments_currency_suffixed_headers()


def test_src_w_48_suspended_users_list(connect, test_data):
    """GAP-SRC-W-48 (partial): the suspended-users list shows a Revoke column and
    lists the suspended worker. (The suspend-modal content + re-suspend idempotency
    need a reliable path to the modal and are deferred.)"""
    connect_page, opps_url = connect
    wl = test_data.get("WORKER_LIFECYCLE")
    dash = open_opportunity_dashboard(connect_page, wl["opportunity_name"], opps_url)
    host, slug, opp_id = dash.base_url_parts()
    connect_page.goto(f"{host}/a/{slug}/opportunity/{opp_id}/suspended_users/")
    connect_page.wait_for_load_state("load")
    connect_page.wait_for_timeout(2000)

    headers = [h.strip() for h in connect_page.locator("table thead th").all_inner_texts()]
    assert any("revoke" in h.lower() for h in headers), f"No Revoke column in suspended-users list: {headers}"
    assert wl["suspended_worker"] in connect_page.inner_text("body"), (
        f"Suspended worker {wl['suspended_worker']!r} not listed"
    )


def test_src_w_47_viewer_read_only_gating(browser, config, settings):
    """GAP-SRC-W-47 (viewer half): a viewer cannot add workers - the Add Worker
    control is disabled/absent on the Connect Workers page. The has_ended half
    needs an ended opportunity and is not covered here.

    Uses the Connect-native viewer account (direct sign-in), like OD_21."""
    if config.env == "prod":
        pytest.skip("Viewer fixture exists on staging only")
    vu = settings.get(section="viewer", key="hq_username", env_var="viewer_username")
    vp = settings.get(section="viewer", key="hq_password", env_var="viewer_password")
    if not vu or not vp:
        pytest.skip("Viewer creds not configured (settings.cfg [viewer])")

    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        base = config.get("connect_url")
        page.goto(f"{base}/accounts/login/")
        page.wait_for_load_state("load")
        page.locator("#id_login").fill(vu)
        page.locator("#id_password").fill(vp)
        page.locator("xpath=//button[@type='submit'][.//span[normalize-space()='Login']]").first.click()
        page.wait_for_load_state("load")

        olp = ConnectOpportunityListPage(page)
        olp.verify_loaded()
        olp.open_opportunity(olp.first_row_name())
        page.wait_for_load_state("load")

        workers = ConnectWorkersPage(page)
        # Navigate to the workers list of whichever opportunity the viewer opened.
        workers_url = page.url.rstrip("/") + "/workers/"
        page.goto(workers_url)
        page.wait_for_load_state("load")
        page.wait_for_timeout(2000)

        add = page.locator(workers.ADD_WORKER_BTN)
        # A viewer must not be able to add workers: the control is either absent or
        # disabled (both satisfy the read-only guarantee).
        if add.count() == 0:
            workers._step("Add Worker control absent for viewer (read-only)")
        else:
            assert add.first.is_disabled(), "Add Worker should be disabled for a viewer"
            workers._step("Add Worker control disabled for viewer")
    finally:
        context.close()
