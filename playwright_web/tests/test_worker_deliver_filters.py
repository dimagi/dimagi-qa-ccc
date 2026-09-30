"""Deliver-tab filter modal (Delivery_tab_10/11/13/14/16).

New automation for plan cases that had no Selenium coverage:
  Delivery_tab_10 - the filter modal opens from the toolbar filter icon
  Delivery_tab_11 - the Last Active dropdown offers the expected options
  Delivery_tab_13 - the Deliveries-with-flags dropdown offers the expected options
  Delivery_tab_14 - the Has-Overlimit dropdown offers the expected options
  Delivery_tab_16 - several filters apply together and the badge counts them

Option sets are asserted against the product source (DeliverFilterSet /
YesNoFilter in commcare_connect/opportunity/filters.py), not guessed. Uses the
manual-review opportunity (WORKER_LIST_VIEW_8 data) so every filter is present -
review_pending and has_duplicates are popped under auto-verify.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_deliver_tab
from pages.connect_workers_page import ConnectWorkersPage

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


@pytest.fixture(scope="module")
def workers_on_deliver(connect, test_data):
    """Open the Deliver tab of the manual-review opportunity once for the module."""
    connect_page, opps_url = connect
    opp = test_data.get("WORKER_DELIVER_FILTERS")["opportunity_name"]
    open_deliver_tab(connect_page, opp, opps_url)
    workers = ConnectWorkersPage(connect_page)
    workers.verify_deliver_table_headers_present()
    return workers


def test_delivery_tab_10_filter_modal_opens(workers_on_deliver):
    """Delivery_tab_10: the filter icon opens the filter modal with its fields."""
    workers = workers_on_deliver
    workers.open_filter_modal()
    assert workers.filter_present(workers.FILTER_LAST_ACTIVE), "Last Active filter missing"
    # has_flags and has_overlimit are present in both verification modes.
    assert workers.filter_present(workers.FILTER_HAS_FLAGS), "Deliveries-with-flags filter missing"
    assert workers.filter_present(workers.FILTER_HAS_OVERLIMIT), "Has-overlimit filter missing"


def test_delivery_tab_11_last_active_options(workers_on_deliver, test_data):
    """Delivery_tab_11: Last Active dropdown offers Any time / 1 / 3 / 7 days ago."""
    workers = workers_on_deliver
    expected = test_data.get("WORKER_DELIVER_FILTERS")["last_active_options"]
    workers.open_filter_modal()
    options = workers.filter_field_options(workers.FILTER_LAST_ACTIVE)
    assert options == expected, f"Last Active options mismatch: {options}"


def test_delivery_tab_13_deliveries_with_flags_options(workers_on_deliver, test_data):
    """Delivery_tab_13: Deliveries-with-flags dropdown offers ---------/Yes/No."""
    workers = workers_on_deliver
    expected = test_data.get("WORKER_DELIVER_FILTERS")["yes_no_options"]
    workers.open_filter_modal()
    options = workers.filter_field_options(workers.FILTER_HAS_FLAGS)
    assert options == expected, f"Deliveries-with-flags options mismatch: {options}"


def test_delivery_tab_14_has_overlimit_options(workers_on_deliver, test_data):
    """Delivery_tab_14: Has-overlimit dropdown offers ---------/Yes/No."""
    workers = workers_on_deliver
    expected = test_data.get("WORKER_DELIVER_FILTERS")["yes_no_options"]
    workers.open_filter_modal()
    options = workers.filter_field_options(workers.FILTER_HAS_OVERLIMIT)
    assert options == expected, f"Has-overlimit options mismatch: {options}"


def test_delivery_tab_16_filter_combination_applies(workers_on_deliver):
    """Delivery_tab_16: multiple filters apply together and the badge counts them."""
    workers = workers_on_deliver
    workers.clear_all_filters_deliver_table()
    applied, badge = workers.apply_filter_combination([
        (workers.FILTER_LAST_ACTIVE, "3 days ago"),
        (workers.FILTER_HAS_FLAGS, "Yes"),
    ])
    assert badge == applied, f"Filter badge {badge} does not match {applied} applied filters"
    assert applied >= 2, f"Expected at least 2 filters applied, got {applied}"
    workers.clear_all_filters_deliver_table()
