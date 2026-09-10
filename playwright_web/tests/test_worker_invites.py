"""Connect Workers invite lifecycle (Connect_worker_02, _03).

Phase 1: the zero-mutation cases that read an existing pending invite on the
Connect Workers tab (no SMS sent):
  Connect_worker_02 - a not-yet-accepted invite shows the 'Invite pending' status
  Connect_worker_03 - Resend/Delete buttons enable only when an invite is selected

Runs against covid_opp_test, which keeps a reserved pending invite (+74267426006).
The mutating invite cases (_05/_08/_09, which send an SMS and self-clean) are in a
separate module once the seeded accepted/suspended data lands for the full tab.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers
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
def workers_list(connect, test_data):
    connect_page, opps_url = connect
    opp = test_data.get("WORKER_LIST_VIEW_8")["opportunity_name"]  # covid_opp_test
    open_connect_workers(connect_page, opp, opps_url)
    return ConnectWorkersPage(connect_page)


def test_connect_worker_02_pending_invite_status(workers_list):
    """Connect_worker_02: an invited-but-not-accepted worker shows 'Invite pending'."""
    workers_list.verify_connect_workers_table_headers_present()
    workers_list.verify_pending_invite_status_present()


def test_connect_worker_03_resend_delete_gated_by_selection(workers_list):
    """Connect_worker_03: Resend/Delete invite buttons are enabled only when an
    invite is selected."""
    workers_list.verify_resend_delete_gated_by_selection()
