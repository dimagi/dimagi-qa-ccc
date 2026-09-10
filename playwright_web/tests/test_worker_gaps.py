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
from flows.workers_setup import open_connect_workers, open_deliver_tab, open_payments_tab
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
