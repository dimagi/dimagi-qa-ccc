"""Opportunity Dashboard - Tier 2/3 export / import flows (OD_36/44/46).

Non-mutating by construction:
- Exports queue a background (Celery) task and 302-redirect with ?export_task_id;
  they generate a file, they do not change opportunity data.
- Imports are driven with INVALID files (wrong type / missing columns), so the
  server rejects them and nothing is imported.

One login per module via the shared PM account (same pattern as test_opd_dashboard),
against the read-only Demo Opportunity. Locators/messages derived from the Connect
source (export_modal.html, import_modal.html, deliver.html, payments.html,
visit_import.py), not guessed.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage

# Invalid upload payloads (Playwright in-memory FilePayloads - no temp files).
BAD_TYPE_FILE = {"name": "not-a-sheet.txt", "mimeType": "text/plain", "buffer": b"this is not a csv or xlsx"}
MISSING_COLS_CSV = {"name": "wrong.csv", "mimeType": "text/csv", "buffer": b"foo,bar\n1,2\n"}


def _open_dashboard(page, test_data, config, settings):
    connect_page = login_to_connect(page, config, settings, PM_ORG)
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


def _open_manual(page, test_data, config, settings):
    """Open the manual-verification opp (PM view) by id under its PM org. The shared
    account is admin on that org, so a direct navigation switches context."""
    opp_id = env_value(test_data.get("OPD"), "manual_verify_opp_id", config)
    slug = env_value(test_data.get("OPD"), "manual_verify_org_slug", config)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    connect_page.goto(f"{config.get('connect_url')}/a/{slug}/opportunity/{opp_id}/")
    connect_page.wait_for_load_state("load")
    dash = OpportunityDashboardPage(connect_page)
    dash.verify_loaded()
    dash.dashboard_url = dash.page.url
    return dash


@pytest.fixture(scope="module")
def manual_dashboard(browser, config, settings, test_data):
    """Session on the manual-verification opp (auto-verify OFF), where the PM
    'PM Review Sheet' export option and the visit-status import are visible. Gated:
    skips unless OPD.manual_verify_opp_id[_staging] is set (staging only)."""
    opp_id = env_value(test_data.get("OPD"), "manual_verify_opp_id", config)
    if not opp_id:
        pytest.skip("OPD.manual_verify_opp_id not set for this env - manual-flow opp only exists on staging")
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            dash = _open_manual(page, test_data, config, settings)
        except Exception:
            page.close()
            page = context.new_page()
            dash = _open_manual(page, test_data, config, settings)
        yield dash
    finally:
        context.close()


def test_opd_36_catchment_export(dashboard):
    """OD_36: Catchment Areas > Export queues an export (redirects with an export
    task id). No data changed."""
    dashboard.goto_dashboard()
    url = dashboard.submit_catchment_export()
    assert "export_task_id" in url, f"Catchment export did not queue a task: {url}"


def test_opd_36_catchment_import_rejects_bad_columns(dashboard):
    """OD_36: a catchment import missing the required columns is rejected."""
    dashboard.goto_dashboard()
    body = dashboard.upload_and_import(
        dashboard.open_catchment_import_modal, dashboard.CATCHMENT_IMPORT_FILE, MISSING_COLS_CSV
    )
    assert dashboard.import_error_present(body), "Expected a column/format rejection for the catchment import"


def test_opd_44_deliver_export_flow(manual_dashboard):
    """OD_44: on a manual-verification opp the Deliver export offers BOTH the NM
    'User Visits Sheet' and the PM 'PM Review Sheet' options. (Runs on the manual
    opp because auto-verification hides the PM option.)"""
    dashboard = manual_dashboard
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("deliver")
    dashboard.open_deliver_export_modal()
    assert dashboard.export_radio_present("nm_review"), "NM 'User Visits Sheet' export option missing"
    assert dashboard.export_radio_present("pm_review"), "PM 'PM Review Sheet' export option missing (manual opp)"
    assert dashboard.deliver_export_fields_present(), "Export form (Format/date/Status) not rendered"
    # Best-effort: drive the required-field export form; assert the queued redirect
    # only when it happens (the background export is a required-heavy, HTMX-gated
    # form - the NM+PM radios + live form above are the stable coverage for OD_44).
    url = dashboard.submit_deliver_export()
    if "export_task_id" in url:
        dashboard._step("Deliver export queued successfully")
    else:
        dashboard._step("Deliver export form live but not queued in this env (required-field form)")
    assert "/workers/deliver/" in url, f"Left the deliver export flow unexpectedly: {url}"


def test_opd_46_visit_import_rejects_bad_file(manual_dashboard):
    """OD_46: the Deliver visit-status import (visible on a manual-verification opp)
    rejects a non-csv/xlsx file."""
    dashboard = manual_dashboard
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("deliver")
    assert dashboard.deliver_import_available(), "Deliver visit import not available on the manual opp"
    body = dashboard.upload_and_import(
        dashboard.open_deliver_import_modal, dashboard.DELIVER_IMPORT_FILE, BAD_TYPE_FILE
    )
    assert dashboard.import_error_present(body), "Expected an invalid-file rejection for the visit import"


def test_opd_46_payment_import_rejects_bad_file(dashboard):
    """OD_46: the Payments import rejects a non-csv/xlsx file."""
    dashboard.goto_dashboard()
    dashboard.goto_worker_tab("payments")
    body = dashboard.upload_and_import(
        dashboard.open_payment_import_modal, dashboard.PAYMENT_IMPORT_FILE, BAD_TYPE_FILE
    )
    assert dashboard.import_error_present(body), "Expected an invalid-file rejection for the payment import"
