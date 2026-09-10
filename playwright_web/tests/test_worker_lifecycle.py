"""Connect Workers lifecycle statuses against the seeded Worker_Lifecycle_Automation
opportunity (Connect_worker_04, _07, Learn_tab_03).

These read seeded worker states (no mutation):
  Connect_worker_04 - an accepted worker shows 'Invite accepted'
  Connect_worker_07 - a suspended worker shows 'User suspended'
  Learn_tab_03      - a worker who failed the assessment shows Assessment 'Failed'

The mutating lifecycle cases (resend/delete gating for accepted/suspended, bulk)
live in test_worker_invites.py once probed.
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
def workers(connect, test_data):
    connect_page, opps_url = connect
    opp = test_data.get("WORKER_LIFECYCLE")["opportunity_name"]
    open_connect_workers(connect_page, opp, opps_url)
    return ConnectWorkersPage(connect_page)


def test_connect_worker_04_accepted_status(workers, test_data):
    """Connect_worker_04: an accepted worker shows 'Invite accepted'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.verify_worker_status(data["accepted_worker"], "Invite accepted")


def test_connect_worker_07_suspended_status(workers, test_data):
    """Connect_worker_07: a suspended worker shows 'User suspended'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.verify_worker_status(data["suspended_worker"], "User suspended")


def test_learn_tab_03_assessment_failed(workers, test_data):
    """Learn_tab_03: a worker who failed the assessment shows Assessment 'Failed'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.click_tab_by_name("Learn")
    workers.verify_learn_table_headers_present()
    workers.verify_assessment_status(data["failed_assessment_worker"], "Failed")
