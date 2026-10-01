"""Microplanning (Microplanning_01-40, CCC_Web_Platform_MTP.xlsx).

Mostly read-only/structural cases. The Mapbox canvas has no per-feature DOM, so
tests that need a selected work area (16/17 and the review cases 09-11) set the
map component's Alpine `selectedFeature` state from JavaScript instead of
clicking the canvas - they exercise the side panel for that work area, not the
click-to-select itself. The deny/approve cases (10/11) change seeded data.

Reuses the OPD.microplanning_opp_id_staging fixture (the "OLP Test opp" already
used by test_opd_gaps.py::test_opd_28) - staging only, skips on prod, same as
that module's `session` fixture.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_microplanning_page import CoverageProgressPage, MicroplanningPage
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_workers_page import ConnectWorkersPage


def _opp(test_data, config):
    opd = test_data.get("OPD") or {}
    opp_id = env_value(opd, "microplanning_opp_id", config)
    slug = env_value(opd, "gap_org_slug", config)
    if not opp_id or not slug:
        pytest.skip("OPD.microplanning_opp_id/gap_org_slug not configured for this env")
    return opp_id, slug


@pytest.fixture(scope="module")
def session(browser, config, settings, test_data):
    if config.env == "prod":
        pytest.skip("Microplanning fixture opp exists on staging only")
    opp_id, slug = _opp(test_data, config)
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        connect_page = login_to_connect(page, config, settings, PM_ORG)
        base = config.get("connect_url")
        dash = OpportunityDashboardPage(connect_page)
        dash.goto_opp(base, slug, opp_id)
        dash.wait_for_stats()
        dash.click_stat_panel("microplanning")
        micro = MicroplanningPage(connect_page)
        micro.verify_loaded()
        yield connect_page, base, slug, opp_id
    finally:
        context.close()


def _home(session):
    connect_page, base, slug, opp_id = session
    connect_page.goto(f"{base}/a/{slug}/microplanning/{opp_id}/")
    connect_page.wait_for_load_state("load")
    micro = MicroplanningPage(connect_page)
    micro.verify_loaded()
    return micro


# -- Microplanning_01/30: land + opp-card metrics --------------------------------


def test_microplanning_01_lands_on_select_opportunity_area(session):
    micro = _home(session)  # verify_loaded() already ran and would have raised
    assert micro.page.locator(micro.PAGE_TITLE).count() > 0


def test_microplanning_30_opp_card_details(session):
    micro = _home(session)
    cards = micro.opp_card_metrics()
    assert cards, "No opp-card metrics rendered"


# -- Microplanning_03/04/06/07/12/13/14: filter sidebar --------------------------


def test_microplanning_04_filter_fields_present(session):
    micro = _home(session)
    present = micro.filter_fields_present()
    missing = [k for k, v in present.items() if not v]
    assert not missing, f"Missing filter fields: {missing}"


def test_microplanning_07_work_area_status_options(session, test_data):
    micro = _home(session)
    options = micro.status_filter_options()
    expected = test_data.get("MICROPLANNING_UI")["work_area_status_options"]
    missing = [o for o in expected if o not in options]
    assert not missing, f"Missing Work Area Status options {missing}. Present: {options}"


def test_microplanning_06_show_only_unassigned_filter_present(session):
    micro = _home(session)
    assert micro.unassigned_filter_present(), "'Show Only Unassigned' filter checkbox missing"


def test_microplanning_12_assignee_filter_present(session):
    micro = _home(session)
    assert micro.filter_fields_present()["assignee"], "Assignee filter field missing"


def test_microplanning_13_start_date_field(session):
    micro = _home(session)
    assert micro.date_field_type(micro.FILTER_START_DATE) == "date"


def test_microplanning_14_end_date_field(session):
    micro = _home(session)
    assert micro.date_field_type(micro.FILTER_END_DATE) == "date"


def test_microplanning_03_download_work_area_summary(session):
    micro = _home(session)
    assert micro.download_button_present(), "Download work-area-summary button missing"
    download = micro.click_download()
    assert download.suggested_filename, "Download did not produce a file"


# -- Microplanning_18/21: assignment mode -----------------------------------------


def test_microplanning_18_enter_assignment_mode(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    assert micro.page.locator(micro.UNASSIGNED_ONLY_TOGGLE).count() > 0, (
        "Assignment-mode sidebar did not render"
    )


def test_microplanning_21_show_only_unassigned_toggle(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    before = micro.unassigned_toggle_state()
    micro.toggle_show_only_unassigned()
    after = micro.unassigned_toggle_state()
    assert after != before, f"Toggle state did not change: {before!r} -> {after!r}"


# -- Microplanning_22/25/27/28/29: assignment-mode panels ------------------------


def test_microplanning_22_group_dropdown_present(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    assert micro.page.locator(micro.ASSIGNMENT_GROUP_SELECT).count() > 0, (
        "'Select Work Areas to Assign' group field missing"
    )


def test_microplanning_25_select_new_assignee_dropdown(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    assert options, "'Select new Assignee' dropdown has no connect workers listed"


def test_microplanning_27_flw_summary_on_assignee_select(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available on this opportunity to select for FLW summary")
    micro.select_assignee_for_flw_summary(options[0])
    assert micro.wait_for_flw_summary(), "FLW Summary section did not populate after selecting an assignee"


def test_microplanning_28_view_summary_by_flw_nav(session, test_data):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available to open FLW summary")
    micro.select_assignee_for_flw_summary(options[0])
    micro.wait_for_flw_summary()
    if micro.page.locator(micro.FLW_SUMMARY_VIEW_BY_FLW_BTN).count() == 0:
        pytest.skip("'View summary by FLW' control not present for this assignee")
    micro.open_flw_summary_by_flw()
    path = test_data.get("MICROPLANNING_UI")["work_area_assignments_path"]
    assert path in micro.page.url, f"Did not land on the work-area-assignments page ({path}): {micro.page.url}"


def test_microplanning_29_view_visits_nav(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available to open FLW visits")
    micro.select_assignee_for_flw_summary(options[0])
    micro.wait_for_flw_summary()
    if micro.page.locator(micro.FLW_SUMMARY_VIEW_VISITS_BTN).count() == 0:
        pytest.skip("'View Visits' control not present for this assignee")
    micro.open_flw_summary_visits()
    assert "/workers/" in micro.page.url, f"Did not land on the connect workers page: {micro.page.url}"


# -- Microplanning_33/34: Connect Workers page "Work Area Assignments" tab ------


def test_microplanning_33_work_area_assignment_tab_headers(session, test_data):
    connect_page, base, slug, opp_id = session
    ui = test_data.get("MICROPLANNING_UI")
    connect_page.goto(f"{base}/a/{slug}/opportunity/{opp_id}/{ui['work_area_assignments_path']}/")
    connect_page.wait_for_load_state("load")
    workers = ConnectWorkersPage(connect_page)
    workers.verify_table_headers_present(ui["work_area_assignments_headers"])


def test_microplanning_34_sort_arrows_present(session, test_data):
    connect_page, base, slug, opp_id = session
    ui = test_data.get("MICROPLANNING_UI")
    connect_page.goto(f"{base}/a/{slug}/opportunity/{opp_id}/{ui['work_area_assignments_path']}/")
    connect_page.wait_for_load_state("load")
    workers = ConnectWorkersPage(connect_page)
    workers._header_texts()  # waits for the #table htmx swap to render
    sortable = connect_page.locator(MicroplanningPage.WORK_AREA_ASSIGNMENTS_SORTABLE_HEADERS)
    assert sortable.count() > 0, "No sortable column headers found on the Work Area Assignments tab"


# -- Microplanning_16/17: select/modify a work area, driven via JS (no map click) --


def test_microplanning_16_select_work_area_section(session, test_data):
    """Checks the Select Work Area side panel for a work area. The work area is
    selected by setting the map's Alpine state from JS, NOT by clicking it on the
    canvas, so this covers the panel's content, not click-to-select."""
    connect_page, base, slug, opp_id = session
    micro = _home(session)
    micro.enter_assignment_mode()  # cheapest path to a real assignee id
    work_area = micro.fetch_a_real_work_area(base, slug, opp_id)
    micro.exit_assignment_mode()
    if work_area is None:
        pytest.skip("No assignee on this opportunity has any assigned work areas to select")
    micro = _home(session)
    micro.select_work_area_via_js(work_area)
    text = micro.select_work_area_section_text()
    for label in test_data.get("MICROPLANNING_UI")["select_work_area_labels"]:
        assert label in text, f"'{label}' missing from the Select Work Area section: {text!r}"


def test_microplanning_17_modify_work_area_form_fields(session):
    """Opens the Modify Work Area form and checks its fields render - does NOT
    submit/save, so this stays non-mutating against the shared fixture opp. The
    work area is selected via JS state (not a canvas click), as in test 16."""
    connect_page, base, slug, opp_id = session
    micro = _home(session)
    micro.enter_assignment_mode()
    work_area = micro.fetch_a_real_work_area(base, slug, opp_id)
    micro.exit_assignment_mode()
    if work_area is None:
        pytest.skip("No assignee on this opportunity has any assigned work areas to select")
    micro = _home(session)
    micro.select_work_area_via_js(work_area)
    micro.open_modify_work_area_modal()
    text = micro.modify_work_area_modal_text()
    assert text.strip(), "Modify Work Area modal opened empty"


# -- Microplanning_31/35-40 + unnumbered: Coverage Progress Tracker --------------


def test_microplanning_31_coverage_see_more_nav(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()


def test_microplanning_35_progress_tracker_page_details(session, test_data):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    sections = test_data.get("MICROPLANNING_UI")["coverage_sections"]
    assert coverage.section_present(sections["core_metrics"])
    assert coverage.section_present(sections["by_group"])


def test_microplanning_36_core_metrics_table_and_download(session, test_data):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    ui = test_data.get("MICROPLANNING_UI")
    section = ui["coverage_sections"]["core_metrics"]
    headers = coverage.section_table_headers(section)
    ward = ui["core_metrics_ward_column"]
    assert ward in " | ".join(headers), f"Core Metrics table missing '{ward}' column: {headers}"
    download = coverage.download_from_section(section)
    assert download.suggested_filename


def test_microplanning_37_metrics_by_work_area_group(session, test_data):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    section = test_data.get("MICROPLANNING_UI")["coverage_sections"]["by_group"]
    headers = coverage.section_table_headers(section)
    assert headers, f"{section} table has no columns"
    download = coverage.download_from_section(section)
    assert download.suggested_filename


def test_microplanning_38_date_filter(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    assert coverage.page.locator(coverage.DATE_FROM).count() > 0
    assert coverage.page.locator(coverage.DATE_TO).count() > 0


def test_microplanning_39_ward_saturation_goal(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    text = coverage.ward_saturation_text()
    assert "%" in text or any(ch.isdigit() for ch in text), f"No percentage shown: {text!r}"


def test_microplanning_40_core_metrics_update_on_date_filter(session, test_data):
    ui = test_data.get("MICROPLANNING_UI")
    section = ui["coverage_sections"]["core_metrics"]
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    before = coverage.section_table_body_text(section)
    if not any(ch.isdigit() and ch != "0" for ch in before):
        pytest.skip("Core Metrics shows no non-zero values to react to a date filter on this opportunity")
    start, end = ui["empty_date_range"]
    coverage.apply_date_filter(start, end)
    coverage.verify_loaded()
    after = coverage.section_table_body_text(section)
    assert after != before, (
        f"Core Metrics values did not change after filtering to {start}..{end} (a range with no activity)"
    )


# -- Microplanning_09/10/11: review an inaccessible-work-area request ------------
# Separate disposable opp (MICROPLANNING_REVIEW, not the shared OLP Test opp) -
# see test_data/web_test_data.yaml for why. It was seeded with exactly 3 work areas
# in REQUEST_FOR_INACCESSIBLE status. Each test uses its OWN work area, named by id
# in the test data (details / deny / approve), so a skipped or failed test can never
# make two tests act on the same one. Deny and approve permanently consume theirs and
# nothing restores them, so once they have run the next run skips with a message
# saying exactly what to ask for.
#
# MTP note: the committed sheet's title/steps look swapped for 10 and 11 -
# "Microplanning_10 ... approve the inaccessible request" whose own steps click
# Deny, and "Microplanning_11 ... deny the inaccessible request" whose own steps
# click "Approve as inaccessible". Followed the steps/expected-result text (the
# unambiguous part) rather than the titles - not fixing the xlsx here, out of
# scope for this batch.


@pytest.fixture(scope="module")
def review_session(browser, config, settings, test_data):
    review = test_data.get("MICROPLANNING_REVIEW") or {}
    opp_id = env_value(review, "opportunity_id", config)
    slug = env_value(review, "org_slug", config)
    if not opp_id or not slug:
        pytest.skip("MICROPLANNING_REVIEW.opportunity_id/org_slug not configured for this env")
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        connect_page = login_to_connect(page, config, settings, PM_ORG)
        base = config.get("connect_url")
        connect_page.goto(f"{base}/a/{slug}/microplanning/{opp_id}/")
        connect_page.wait_for_load_state("load")
        micro = MicroplanningPage(connect_page)
        micro.verify_loaded()
        yield connect_page, base, slug, opp_id
    finally:
        context.close()


def _review_home(review_session):
    connect_page, base, slug, opp_id = review_session
    connect_page.goto(f"{base}/a/{slug}/microplanning/{opp_id}/")
    connect_page.wait_for_load_state("load")
    micro = MicroplanningPage(connect_page)
    micro.verify_loaded()
    return micro


def _pending_work_area(micro, test_data, config, base, slug, opp_id, key):
    """The seeded work area named by MICROPLANNING_REVIEW.<key>, fetched fresh so
    it reflects what earlier runs consumed. Skips (naming the reseed request) if it
    is gone or no longer REQUEST_FOR_INACCESSIBLE."""
    work_area_id = env_value(test_data.get("MICROPLANNING_REVIEW"), key, config)
    if work_area_id is None:
        pytest.skip(f"MICROPLANNING_REVIEW.{key} not configured for this env")
    by_id = {wa["id"]: wa for wa in micro.fetch_all_work_areas(base, slug, opp_id)}
    work_area = by_id.get(work_area_id)
    if work_area is None or work_area.get("status") != "REQUEST_FOR_INACCESSIBLE":
        status = work_area.get("status") if work_area else "not found"
        pytest.skip(
            f"Work area {work_area_id} on opportunity {opp_id} is no longer REQUEST_FOR_INACCESSIBLE "
            f"(now: {status}). Deny/approve consume it - ask Anshu to reseed that work area (or point "
            f"MICROPLANNING_REVIEW.{key} at a fresh one)."
        )
    return work_area


def _require_review_ui(micro):
    """Skip cleanly if the 'Review Inaccessible' trigger isn't deployed yet -
    confirmed live 2026-09-23 that staging's backend is fully functional
    (GET .../review_inaccessibility/<id>/ -> 200, real request data) but the
    frontend button/JS aren't rendered anywhere on the page. See
    MicroplanningPage.review_button_ready's docstring."""
    if not micro.review_button_ready():
        pytest.skip(
            "'Review Inaccessible' UI not deployed on this env yet (backend endpoint "
            "is live, but no trigger button/JS in the rendered page) - re-run once deployed"
        )


def test_microplanning_09_review_inaccessibility_details(review_session, test_data, config):
    connect_page, base, slug, opp_id = review_session
    micro = _review_home(review_session)
    work_area = _pending_work_area(micro, test_data, config, base, slug, opp_id, "details_work_area_id")
    micro.select_work_area_via_js(work_area)
    _require_review_ui(micro)
    micro.open_review_inaccessibility_modal()
    present = micro.review_modal_fields_present()
    for field in ("visit_date", "reason", "photo_evidence", "return_to_map", "deny", "approve"):
        assert present[field], f"Review-inaccessibility modal missing '{field}': {present}"
    assert micro.review_visit_date(), "Visit date is empty"
    assert micro.review_reason(), "Reason is empty"


def test_microplanning_10_deny_inaccessibility_request(review_session, test_data, config):
    """Steps/expected in the MTP: click Deny -> push notification sent, work
    area status updates (to NOT_VISITED - see act_on_inaccessibility_request).
    Consumes MICROPLANNING_REVIEW.deny_work_area_id."""
    connect_page, base, slug, opp_id = review_session
    micro = _review_home(review_session)
    work_area = _pending_work_area(micro, test_data, config, base, slug, opp_id, "deny_work_area_id")
    micro.select_work_area_via_js(work_area)
    _require_review_ui(micro)
    micro.open_review_inaccessibility_modal()
    micro.deny_inaccessibility_request()
    assert micro.selected_feature_status() == "NOT_VISITED", "Work area status did not update to NOT_VISITED after deny"


def test_microplanning_11_approve_inaccessibility_request(review_session, test_data, config):
    """Steps/expected in the MTP: click Approve as Inaccessible -> work area is
    marked inaccessible (status INACCESSIBLE). Consumes
    MICROPLANNING_REVIEW.approve_work_area_id."""
    connect_page, base, slug, opp_id = review_session
    micro = _review_home(review_session)
    work_area = _pending_work_area(micro, test_data, config, base, slug, opp_id, "approve_work_area_id")
    micro.select_work_area_via_js(work_area)
    _require_review_ui(micro)
    micro.open_review_inaccessibility_modal()
    micro.approve_inaccessibility_request()
    assert micro.selected_feature_status() == "INACCESSIBLE", "Work area status did not update to INACCESSIBLE after approve"
