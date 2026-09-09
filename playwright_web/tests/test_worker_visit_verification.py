"""Worker Visit Verification Page (WVVP_1-7) - the per-worker Visits page.

Migrated from the Selenium web_tests worker_visit_verification suite. Covers:
  WVVP_1/2 - landing on the Visits page from the worker list, and approving visits
             individually and in bulk
  WVVP_3   - suspending a worker and revoking the suspension
  WVVP_4-7 - the Pending NM Review / Approved / Rejected / All tabs each render

Entry is the shared PM web account (PM_Automation_01) via flows.login_to_connect;
the module logs in once and each test opens its own opportunity/worker (from
WORKER_VISIT_VERIFICATION_PAGE_* test data).
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers, open_deliver_tab
from pages.connect_worker_visits_page import WorkerVisitsPage
from pages.connect_workers_page import ConnectWorkersPage


@pytest.fixture(scope="module")
def connect(browser, config, settings):
    """One authenticated PM session for the whole module. Yields (connect_page,
    opps_url). Login is retried once to absorb the CCHQ login flake."""
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


def test_wvvp_01_02_land_and_approve_visits(connect, test_data):
    """WVVP_1: selecting a worker on the Deliver tab lands on their Visits page.
    WVVP_2: visits can be approved individually and in bulk.

    The approve steps are wrapped like the Selenium original: an opportunity whose
    visits are all already reviewed has no pending rows to approve, so the bulk
    controls are absent - that is not a failure of the landing/approve surface."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_1_2")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    workers.navigate_to_worker_visits(data["worker_name"])
    visits.verify_worker_visits_table_headers_present()
    visits.verify_worker_visits_tabs_present()

    if not visits.has_visit_rows():
        pytest.skip(
            f"No visits to approve for '{data['worker_name']}' in "
            f"'{data['opportunity_name']}' - nothing to exercise the approve controls."
        )

    # WVVP_1 - individual selection then Approve All.
    visits.select_first_row()
    visits.click_approve_all_btn()

    # WVVP_2 - bulk select-all then Approve All (only if rows remain).
    if visits.has_visit_rows():
        visits.set_select_all_checkbox(True)
        visits.click_approve_all_btn()


def test_wvvp_03_suspend_and_revoke(connect, test_data):
    """WVVP_3: a worker can be suspended from their Visits page and un-suspended."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_3")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_connect_workers(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    visits.verify_worker_visits_table_headers_present()

    visits.suspend_user_in_worker_visits(data["reason"])
    visits.revoke_suspension_for_worker()


def test_wvvp_04_05_06_07_review_tabs_render(connect, test_data):
    """WVVP_4-7: the Pending NM Review, Approved, Rejected and All tabs each show
    the visits table. Skipped implicitly on opportunities that expose only the
    Visits/Tasks pair (no NM review), matching the Selenium original."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_4_5_6_7")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    workers.navigate_to_worker_visits(data["worker_name"])
    visits.verify_worker_visits_tabs_present()

    if visits.has_review_tabs():
        # WVVP_4 - Pending NM Review has no Last Activity column.
        visits.click_tab_by_name("Pending NM Review")
        visits.verify_worker_visits_table_headers_present(pending=True)
        # WVVP_5 / WVVP_6 / WVVP_7
        for tab in ("Approved", "Rejected", "All"):
            visits.click_tab_by_name(tab)
            visits.verify_worker_visits_table_headers_present()
    else:
        # This opportunity/worker has no NM-review sub-tabs (only Visits/Tasks), so
        # the four review tabs cannot be exercised here. Still assert the Visits
        # table renders, and flag that WVVP_4-7 needs an NM-review opportunity in
        # test data for full coverage.
        visits.verify_worker_visits_table_headers_present()
        pytest.skip(
            f"'{data['opportunity_name']}' / '{data['worker_name']}' exposes no NM-review "
            "sub-tabs - point WORKER_VISIT_VERIFICATION_PAGE_4_5_6_7 at a manual-review "
            "opportunity to cover the Pending NM Review / Approved / Rejected / All tabs."
        )
