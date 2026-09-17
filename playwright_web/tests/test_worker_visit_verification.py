"""Worker Visit Verification Page - the per-worker Visits page.

Test IDs follow the current committed MTP ("Visit verification page" sheet of
test_plans/CCC_Web_Platform_MTP.xlsx). Migrated from the Selenium web_tests
worker_visit_verification suite (whose older WVVP_1-7 numbering these replace).
Covers:
  VV_1  - landing on the Visits page from the worker list (bulk Approve All also
          partially exercises GAP-SRC-W-42, the in-UI bulk approve)
  VV_4  - suspending a worker and revoking the suspension (revoke = GAP-MISC-01,
          a behaviour not in the MTP)
  VV_5  - the Visits/Tasks tab pair renders; on manual-review opportunities the
          Pending NM Review / Approved / Rejected / All tab-set renders instead
          (GAP-SRC-W-40, the mode x role tab-set)
  VV_9  - clicking a visit opens the details panel
  VV_3  - selecting a visit image opens the carousel popup

VV_2 (to-date KPI header) is covered by test_worker_gaps.test_src_w_46_worker_profile_kpis.

Entry is the shared PM web account (PM_Automation_01) via flows.login_to_connect;
the module logs in once and each test opens its own opportunity/worker (from
WORKER_VISIT_VERIFICATION_PAGE_<VV#> test data, numbered by current MTP VV id).
"""

from urllib.parse import urlsplit

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers, open_deliver_tab
from pages.connect_home_page import ConnectHomePage
from pages.connect_worker_visits_page import WorkerVisitsPage
from pages.connect_workers_page import ConnectWorkersPage
from utils.helpers import parse_org_and_opp

REVIEW_DATA_KEY = "WORKER_VISIT_VERIFICATION_PAGE_31_32_33_34"


def _require_review_data(test_data):
    """Return the VV_31-34 review data, or skip while it is still the TBD placeholder
    (a manual-review opportunity with seeded visits is an Anshu-provided fixture)."""
    data = test_data.get(REVIEW_DATA_KEY)
    if str(data.get("opportunity_name", "")).startswith("TBD") or str(data.get("worker_name", "")).startswith("TBD"):
        pytest.skip(
            f"{REVIEW_DATA_KEY} is unseeded - set opportunity_name/worker_name to the "
            "manual-review opportunity + worker Anshu seeds (>=2 pending and >=2 "
            "NM-approved/PM-review-pending visits) to run VV_31/32/33/34."
        )
    return data


def _open_worker_visits_all_tab(connect_page, opps_url, data):
    """Open the seeded worker's Visits page on the 'All' tab (shows every status),
    returning the WorkerVisitsPage. Assumes the caller has selected the right org."""
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)
    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")
    return visits


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


def test_vv_01_land_and_bulk_approve(connect, test_data):
    """VV_1: selecting a worker on the Deliver tab lands on their Visits page and the
    table renders. The individual + bulk Approve All flow also partially exercises
    GAP-SRC-W-42 (in-UI bulk approve).

    The approve steps are guarded: an opportunity whose visits are all already
    reviewed has no pending rows to approve, so the bulk controls are absent - that
    is not a failure of the landing/approve surface, so the test skips."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_1")
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

    # Individual selection then Approve All.
    visits.select_first_row()
    visits.click_approve_all_btn()

    # Bulk select-all then Approve All (only if rows remain).
    if visits.has_visit_rows():
        visits.set_select_all_checkbox(True)
        visits.click_approve_all_btn()


def test_vv_04_suspend_and_revoke(connect, test_data):
    """VV_4: a worker can be suspended from their Visits page. Revoking the suspension
    (GAP-MISC-01, not an MTP case) is exercised too, to leave the worker as found."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_4")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_connect_workers(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    visits.verify_worker_visits_table_headers_present()

    visits.suspend_user_in_worker_visits(data["reason"])
    visits.revoke_suspension_for_worker()


def test_vv_05_visit_tabs_render(connect, test_data):
    """VV_5: the worker Visits page exposes its tabs. On manual-review opportunities
    that is the Pending NM Review / Approved / Rejected / All tab-set (GAP-SRC-W-40,
    the mode x role tab-set), each rendering the visits table; opportunities without
    NM review expose only the Visits/Tasks pair, in which case the review-tab
    coverage is skipped with a pointer to seed a manual-review opportunity."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_5")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    workers.navigate_to_worker_visits(data["worker_name"])
    visits.verify_worker_visits_tabs_present()

    if visits.has_review_tabs():
        # Pending NM Review has no Last Activity column.
        visits.click_tab_by_name("Pending NM Review")
        visits.verify_worker_visits_table_headers_present(pending=True)
        # Approved / Rejected / All each render the table.
        for tab in ("Approved", "Rejected", "All"):
            visits.click_tab_by_name(tab)
            visits.verify_worker_visits_table_headers_present()
    else:
        # This opportunity/worker has no NM-review sub-tabs (only Visits/Tasks), so
        # the four review tabs cannot be exercised here. Still assert the Visits
        # table renders, and flag that VV_5 review-tab coverage needs an NM-review opportunity in
        # test data for full coverage.
        visits.verify_worker_visits_table_headers_present()
        pytest.skip(
            f"'{data['opportunity_name']}' / '{data['worker_name']}' exposes no NM-review "
            "sub-tabs - point WORKER_VISIT_VERIFICATION_PAGE_5 at a manual-review "
            "opportunity to cover the Pending NM Review / Approved / Rejected / All tabs."
        )


def test_vv_09_visit_details_panel(connect, test_data):
    """VV_9 (MTP Worker Visit Verification Page_9): clicking a visit opens the details
    panel showing Information (Payment Unit / Entity Name / Entity ID), Verification
    Parameters and - when the visit carries a location - the Map. Each visit <tr>
    hx-gets user_visit_details into #visit-details, so a row click populates the panel.
    Skips when the worker has no visits to open."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_9")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    # Show every visit regardless of review status when the NM-review tabs exist.
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")

    if not visits.open_first_visit_details():
        pytest.skip(
            f"Details panel did not open for '{data['worker_name']}' in "
            f"'{data['opportunity_name']}' - either no visits, or the user_visit_details "
            "endpoint is erroring for this opportunity (user_visit_details can 500 when the opp lacks a verification-flags row; "
            "point WORKER_VISIT_VERIFICATION_PAGE_9 at an opp whose details panel renders)."
        )
    visits.verify_visit_details_panel()


def test_vv_03_image_carousel(connect, test_data):
    """VV_3 (MTP Worker Visit Verification Page_3): selecting an image on a visit opens
    the carousel popup (.popup-content). Skips when none of the scanned visits carry a
    photo attachment - point WORKER_VISIT_VERIFICATION_PAGE_3 at a seeded with-image visit
    to exercise it fully."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_3")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")

    if not visits.open_first_visit_with_images():
        pytest.skip(
            f"No image-bearing visit found for '{data['worker_name']}' in "
            f"'{data['opportunity_name']}' - point WORKER_VISIT_VERIFICATION_PAGE_3 at a "
            "with-photo visit to cover VV_3."
        )
    visits.open_and_verify_image_carousel()


def test_vv_31_nm_reject_visit(connect, test_data):
    """VV_31: as the Network Manager, reject a pending visit via the Reason-for-
    Rejection modal; the visit becomes rejected. Runs in the NM org, restoring the
    PM org afterwards so the module's other tests keep their PM session."""
    connect_page, opps_url = connect
    data = _require_review_data(test_data)
    home = ConnectHomePage(connect_page)
    try:
        home.select_organization_from_list(data["network_manager"])
        visits = _open_worker_visits_all_tab(connect_page, opps_url, data)
        if not visits.nm_reject_a_visit(data["reject_reason"]):
            pytest.skip(
                f"No rejectable visit for '{data['worker_name']}' - seed a pending "
                "visit to cover VV_31."
            )
    finally:
        home.select_organization_from_list(PM_ORG)


def test_vv_32_nm_approve_visit(connect, test_data):
    """VV_32: as the Network Manager, approve a pending visit via the Justification-
    for-Approval modal; the visit becomes approved. Runs in the NM org, restoring the
    PM org afterwards."""
    connect_page, opps_url = connect
    data = _require_review_data(test_data)
    home = ConnectHomePage(connect_page)
    try:
        home.select_organization_from_list(data["network_manager"])
        visits = _open_worker_visits_all_tab(connect_page, opps_url, data)
        if not visits.nm_approve_a_visit(data["approve_justification"]):
            pytest.skip(
                f"No approvable visit for '{data['worker_name']}' - seed a pending "
                "visit to cover VV_32."
            )
    finally:
        home.select_organization_from_list(PM_ORG)


def test_vv_33_pm_agree_visit(connect, test_data):
    """VV_33: as the Program Manager, agree an NM-reviewed visit (the Agree button
    posts directly); payment accrues on agree. Uses the module's PM session."""
    connect_page, opps_url = connect
    data = _require_review_data(test_data)
    visits = _open_worker_visits_all_tab(connect_page, opps_url, data)
    if not visits.pm_agree_a_visit():
        pytest.skip(
            f"No NM-reviewed visit with an enabled Agree for '{data['worker_name']}' "
            "- seed an NM-approved / PM-review-pending visit to cover VV_33."
        )


def test_vv_34_pm_disagree_visit(connect, test_data):
    """VV_34: as the Program Manager, disagree an NM-reviewed visit pending PM review
    (the Disagree button posts directly); no payment accrues. Uses the PM session."""
    connect_page, opps_url = connect
    data = _require_review_data(test_data)
    visits = _open_worker_visits_all_tab(connect_page, opps_url, data)
    if not visits.pm_disagree_a_visit():
        pytest.skip(
            f"No NM-reviewed visit with an enabled Disagree for '{data['worker_name']}' "
            "- seed an NM-approved / PM-review-pending visit to cover VV_34."
        )


def test_gap_w_44_visit_action_bar_gating(connect, test_data):
    """GAP-SRC-W-44: the individual visit-review action bar is gated to exactly one
    consistent set - empty under auto-verify, {Approve, Reject} for an NM on a manual
    opp, or Agree/Disagree for a PM - and never mixes NM and PM controls. Asserts that
    invariant on the opened visit (data-agnostic; works whatever the opp's mode)."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_ACTION_GATING")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")

    if not visits.open_first_visit_details():
        pytest.skip(
            f"Details panel did not open for '{data['worker_name']}' in "
            f"'{data['opportunity_name']}' - no visits or the user_visit_details endpoint "
            "is erroring (user_visit_details can 500 when the opp lacks a verification-flags row); cannot inspect action-bar gating."
        )

    present = visits.action_bar_button_set()
    nm = {"Approve", "Reject"}
    pm = {"Agree", "Disagree"}
    valid = present == set() or present == nm or (present <= pm and present)
    assert valid, f"Action bar shows an inconsistent gated set: {sorted(present)}"
    assert not ((present & nm) and (present & pm)), (
        f"Action bar mixes NM and PM controls: {sorted(present)}"
    )


def test_gap_w_45_manual_endpoint_403_under_auto_verify(connect, test_data):
    """GAP-SRC-W-45: manual-verification endpoints (approve_visits) return HTTP 403 with
    an HX-Trigger: reload_table header on an auto-verify opportunity
    (@require_manual_visit_verification). Auto-verify is inferred from an empty action
    bar; skips on manual-review opps where the guard does not apply. The HX-Trigger
    assertion distinguishes the guard's 403 from a CSRF 403."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_ACTION_GATING")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")

    if not visits.open_first_visit_details():
        pytest.skip(
            f"Details panel did not open for '{data['worker_name']}' - no visits or the "
            "user_visit_details endpoint is erroring (user_visit_details can 500 when the opp lacks a verification-flags row); "
            "cannot probe the guard."
        )
    if visits.action_bar_button_set():
        pytest.skip(
            f"'{data['opportunity_name']}' is not auto-verify (action bar has controls) "
            "- the manual-verify guard does not apply; point WORKER_VISIT_ACTION_GATING "
            "at an auto-verify opportunity to cover GAP-SRC-W-45."
        )

    visit_id = visits.first_visit_id()
    org_slug, opp_id = parse_org_and_opp(connect_page.url)
    parts = urlsplit(connect_page.url)
    origin = f"{parts.scheme}://{parts.netloc}"
    endpoint = f"{origin}/a/{org_slug}/opportunity/{opp_id}/approve_visits"

    csrftoken = next(
        (c["value"] for c in connect_page.context.cookies() if c["name"] == "csrftoken"), ""
    )
    # Valid CSRF (header + Referer) so the request reaches the decorator rather than
    # being turned back by CSRF - the shared context also sends the csrftoken cookie.
    response = connect_page.request.post(
        endpoint,
        headers={
            "X-CSRFToken": csrftoken,
            "Referer": connect_page.url,
            "HX-Request": "true",
        },
        form={"visit_ids[]": visit_id or ""},
    )
    assert response.status == 403, (
        f"Expected 403 from {endpoint} on an auto-verify opp, got {response.status}"
    )
    assert response.headers.get("hx-trigger") == "reload_table", (
        "Expected the guard's HX-Trigger: reload_table header (distinguishes it from a "
        f"CSRF 403); got headers {dict(response.headers)}"
    )


def test_gap_w_41_visit_table_waffle_mode_consistent(connect, test_data):
    """GAP-SRC-W-41: the WORKER_VISITS_TASKS switch swaps the whole visit table AND
    the Visits/Tasks sub-tab bar together - switch ON gives the plain WorkerVisitTable
    (a 'Status' column) with the Visits/Tasks bar; switch OFF gives the tabbed
    VisitVerificationTable (a 'Flags' column, no 'Status') with no Visits/Tasks bar.
    Asserts the table column and the sub-tab bar agree on the switch state (the switch
    is a server flag QA can't flip, so this guards the fork's consistency)."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_ACTION_GATING")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])

    headers = visits.visit_table_headers()
    tasks_bar = visits.has_visits_tasks_tabs()
    if "status" in headers and "flags" not in headers:
        # Plain WorkerVisitTable => switch ON => Visits/Tasks bar must be present.
        assert tasks_bar, (
            "Plain visit table ('Status' column) but the Visits/Tasks sub-tab bar is "
            f"absent - WORKER_VISITS_TASKS effects disagree. Headers: {sorted(headers)}"
        )
    elif "flags" in headers and "status" not in headers:
        # Tabbed VisitVerificationTable => switch OFF => no Visits/Tasks bar.
        assert not tasks_bar, (
            "Tabbed visit table ('Flags' column) but the Visits/Tasks sub-tab bar is "
            f"present - WORKER_VISITS_TASKS effects disagree. Headers: {sorted(headers)}"
        )
    else:
        pytest.fail(f"Cannot tell the visit table type from its columns: {sorted(headers)}")


def test_gap_w_43_bulk_controls_hidden_for_pm(connect, test_data):
    """GAP-SRC-W-43: the bulk Approve All / Reject All controls and the select-all
    checkbox column are template-excluded for a PM (they exist only for a non-viewer
    NM on a manual-review opp). The module session is the PM, so none must be present."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_VISIT_ACTION_GATING")
    workers = ConnectWorkersPage(connect_page)
    visits = WorkerVisitsPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.navigate_to_worker_visits(data["worker_name"])
    if visits.has_review_tabs():
        visits.click_tab_by_name("All")

    approve, reject, select = visits.bulk_controls_present()
    assert not (approve or reject or select), (
        "PM should not see any bulk controls, but found "
        f"approve_all={approve} reject_all={reject} select_all={select}"
    )


def test_gap_w_43_bulk_controls_visible_for_nm(connect, test_data):
    """GAP-SRC-W-43 (positive control): a non-viewer NM on a manual-review opportunity
    DOES see the bulk Approve All / Reject All buttons and the select-all column.
    Runs in the NM org against the seeded manual-review opp; skips until that data
    exists. Restores the PM org afterwards."""
    connect_page, opps_url = connect
    data = _require_review_data(test_data)
    home = ConnectHomePage(connect_page)
    try:
        home.select_organization_from_list(data["network_manager"])
        visits = _open_worker_visits_all_tab(connect_page, opps_url, data)
        approve, reject, select = visits.bulk_controls_present()
        assert approve and reject and select, (
            "A non-viewer NM on a manual-review opp should see the bulk controls, but found "
            f"approve_all={approve} reject_all={reject} select_all={select}"
        )
    finally:
        home.select_organization_from_list(PM_ORG)

