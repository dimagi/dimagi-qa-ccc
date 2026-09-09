"""Worker List View (WLV_1-8) - Connect Workers list / Learn / Deliver tables.

Migrated from the Selenium web_tests worker_list_view suite. Covers:
  WLV_1/2/3 - the Connect Workers, Learn and Deliver tab tables render their columns
  WLV_4     - per-worker status count breakdown popups (Delivered/Pending/Approved/Rejected)
  WLV_5     - the Total row's status count breakdown popups
  WLV_8     - the Deliver-tab Last Active filter (1 day ago) applies and badges

Entry is the shared PM web account (PM_Automation_01) via flows.login_to_connect;
the module logs in once and each test opens its own opportunity (from WORKER_*
test data) through the dashboard stat panels, mirroring the Selenium navigation.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers, open_deliver_tab
from pages.connect_workers_page import ConnectWorkersPage


@pytest.fixture(scope="module")
def connect(browser, config, settings):
    """One authenticated PM session for the whole module. Yields (connect_page,
    opps_url); opps_url is the opportunity-list URL each test returns to before
    opening its opportunity. Login is retried once to absorb the CCHQ login flake."""
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


def test_wlv_01_02_03_tabs_render_their_tables(connect, test_data):
    """WLV_1: 'Connect Workers' opens the workers list with its columns.
    WLV_2: the Learn tab shows the learn-progress columns.
    WLV_3: the Deliver tab shows the delivery columns."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_LIST_VIEW_1_2_3")
    workers = ConnectWorkersPage(connect_page)

    open_connect_workers(connect_page, data["opportunity_name"], opps_url)
    workers.verify_connect_workers_table_headers_present()

    workers.click_tab_by_name("Learn")
    workers.verify_learn_table_headers_present()

    workers.click_tab_by_name("Deliver")
    workers.verify_deliver_table_headers_present()


def test_wlv_04_worker_status_count_breakdown(connect, test_data):
    """WLV_4: clicking a worker's Delivered/Pending/Approved/Rejected count opens
    its breakdown popup."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_LIST_VIEW_4")
    workers = ConnectWorkersPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    columns = workers.present_deliver_count_columns()
    assert columns, "Deliver tab shows no status count columns to break down"
    for column in columns:
        workers.click_and_verify_status_count_breakdown_for_item(data["worker_name"], column)


def test_wlv_05_total_row_count_breakdown(connect, test_data):
    """WLV_5: the Total row's status counts open their breakdown popups."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_LIST_VIEW_5")
    workers = ConnectWorkersPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    columns = workers.present_deliver_count_columns()
    assert columns, "Deliver tab shows no status count columns to break down"
    for column in columns:
        workers.click_and_verify_status_count_breakdown_for_item("Total", column)


def test_wlv_08_last_active_filter_1_day_ago(connect, test_data):
    """WLV_8: the Deliver-tab 'Last active: 1 day ago' filter applies and shows a
    single active-filter badge."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_LIST_VIEW_8")
    workers = ConnectWorkersPage(connect_page)

    open_deliver_tab(connect_page, data["opportunity_name"], opps_url)
    workers.verify_deliver_table_headers_present()

    workers.clear_all_filters_deliver_table()
    workers.apply_and_verify_last_active_1_day_ago()


def test_connect_worker_17_sort_list_by_header(connect, test_data):
    """Connect_worker_17: the Connect Workers list can be sorted by clicking a
    column header; the sort is reflected in the page's ?sort= param."""
    connect_page, opps_url = connect
    data = test_data.get("WORKER_LIST_VIEW_1_2_3")
    workers = ConnectWorkersPage(connect_page)

    open_connect_workers(connect_page, data["opportunity_name"], opps_url)
    workers.verify_connect_workers_table_headers_present()

    sortable = workers.sortable_list_columns()
    assert sortable, "Connect Workers list exposes no sortable column headers"

    # The list loads sorted by -last_active; sorting by a different column must
    # change the ?sort= param. Pick a sortable header that is not the default.
    target = next((c for c in sortable if "last active" not in c.lower()), sortable[0])
    new_sort = workers.click_list_column_sort(target)
    assert new_sort, f"Sorting by '{target}' produced no ?sort= param"
    assert "last_active" not in new_sort, (
        f"Sort by '{target}' did not change the sort away from the default: {new_sort!r}"
    )
