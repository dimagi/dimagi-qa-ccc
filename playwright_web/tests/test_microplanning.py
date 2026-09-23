"""Microplanning (Microplanning_01-40, CCC_Web_Platform_MTP.xlsx).

Read-only/structural cases only - everything that needs clicking a specific
work area on the Mapbox canvas map (no per-feature DOM access - see
connect_microplanning_page.py's module docstring) is deferred to a later batch
that works out a click-coordinate or API-seeded workaround.

Reuses the OPD.microplanning_opp_id_staging fixture (the "OLP Test opp" already
used by test_opd_gaps.py::test_opd_28) - staging only, skips on prod, same as
that module's `session` fixture.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_microplanning_page import (
    WORK_AREA_STATUS_OPTIONS,
    CoverageProgressPage,
    MicroplanningPage,
)
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
    labels = micro.opp_card_metric_labels()
    assert labels, "No opp-card metrics rendered"


# -- Microplanning_03/04/06/07/12/13/14: filter sidebar --------------------------


def test_microplanning_04_filter_fields_present(session):
    micro = _home(session)
    present = micro.filter_fields_present()
    missing = [k for k, v in present.items() if not v]
    assert not missing, f"Missing filter fields: {missing}"


def test_microplanning_07_work_area_status_options(session):
    micro = _home(session)
    options = micro.status_filter_options()
    missing = [o for o in WORK_AREA_STATUS_OPTIONS if o not in options]
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
    return options


def test_microplanning_27_flw_summary_on_assignee_select(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available on this opportunity to select for FLW summary")
    micro.select_assignee_for_flw_summary(options[0])
    micro.page.wait_for_timeout(1500)  # updateFlwSummary() is an async fetch
    assert micro.flw_summary_visible(), "FLW Summary section did not populate after selecting an assignee"


def test_microplanning_28_view_summary_by_flw_nav(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available to open FLW summary")
    micro.select_assignee_for_flw_summary(options[0])
    micro.page.wait_for_timeout(1500)
    if micro.page.locator(micro.FLW_SUMMARY_VIEW_BY_FLW_BTN).count() == 0:
        pytest.skip("'View summary by FLW' control not present for this assignee")
    micro.open_flw_summary_by_flw()
    assert "work" in micro.page.url.lower(), f"Did not land on the work-area-assignments page: {micro.page.url}"


def test_microplanning_29_view_visits_nav(session):
    micro = _home(session)
    micro.enter_assignment_mode()
    options = micro.assignment_assignee_options()
    if not options:
        pytest.skip("No assignees available to open FLW visits")
    micro.select_assignee_for_flw_summary(options[0])
    micro.page.wait_for_timeout(1500)
    if micro.page.locator(micro.FLW_SUMMARY_VIEW_VISITS_BTN).count() == 0:
        pytest.skip("'View Visits' control not present for this assignee")
    micro.open_flw_summary_visits()
    assert "/workers/" in micro.page.url, f"Did not land on the connect workers page: {micro.page.url}"


# -- Microplanning_33/34: Connect Workers page "Work Area Assignments" tab ------


def test_microplanning_33_work_area_assignment_tab_headers(session):
    connect_page, base, slug, opp_id = session
    connect_page.goto(f"{base}/a/{slug}/opportunity/{opp_id}/workers/work-areas/")
    connect_page.wait_for_load_state("load")
    workers = ConnectWorkersPage(connect_page)
    expected = [
        "Name", "Last active", "Assigned Buildings", "Assigned Visits",
        "Assigned work areas", "Assigned work area groups", "Visits Done",
    ]
    workers.verify_table_headers_present(expected)


def test_microplanning_34_sort_arrows_present(session):
    connect_page, base, slug, opp_id = session
    connect_page.goto(f"{base}/a/{slug}/opportunity/{opp_id}/workers/work-areas/")
    connect_page.wait_for_load_state("load")
    workers = ConnectWorkersPage(connect_page)
    workers._header_texts()  # waits for the #table htmx swap to render
    sortable = connect_page.locator("//table[contains(@class,'base-table')]//th[.//a[contains(@href,'sort=')]]")
    assert sortable.count() > 0, "No sortable column headers found on the Work Area Assignments tab"


# -- Microplanning_31/35-40 + unnumbered: Coverage Progress Tracker --------------


def test_microplanning_31_coverage_see_more_nav(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()


def test_microplanning_35_progress_tracker_page_details(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    assert coverage.section_present("Core Metrics")
    assert coverage.section_present("Metrics by Work Area Group")


def test_microplanning_36_core_metrics_table_and_download(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    headers = coverage.section_table_headers("Core Metrics")
    assert "Ward" in " | ".join(headers), f"Core Metrics table missing 'Ward' column: {headers}"
    download = coverage.download_from_section("Core Metrics")
    assert download.suggested_filename


def test_microplanning_37_metrics_by_work_area_group(session):
    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    headers = coverage.section_table_headers("Metrics by Work Area Group")
    assert headers, "Metrics by Work Area Group table has no columns"
    download = coverage.download_from_section("Metrics by Work Area Group")
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


def test_microplanning_40_core_metrics_update_on_date_filter(session):
    import datetime

    micro = _home(session)
    micro.open_coverage_progress()
    coverage = CoverageProgressPage(micro.page)
    coverage.verify_loaded()
    before = coverage.section_table_headers("Core Metrics")
    start = (datetime.date.today() - datetime.timedelta(days=30)).isoformat()
    end = datetime.date.today().isoformat()
    coverage.apply_date_filter(start, end)
    coverage.verify_loaded()
    after = coverage.section_table_headers("Core Metrics")
    assert after, "Core Metrics table disappeared after applying a date filter"
    assert before == after, "Core Metrics columns changed shape after filtering (expected same columns)"
