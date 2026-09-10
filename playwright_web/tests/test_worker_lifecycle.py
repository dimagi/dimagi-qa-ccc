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
    w = ConnectWorkersPage(connect_page)
    w._workers_url = connect_page.url  # for resend navigation (redirects to dashboard)
    return w


def test_connect_worker_04_accepted_status(workers, test_data):
    """Connect_worker_04: an accepted worker shows 'Invite accepted'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.verify_worker_status(data["accepted_worker"], "Invite accepted")


def test_connect_worker_07_suspended_status(workers, test_data):
    """Connect_worker_07: a suspended worker shows 'User suspended'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.verify_worker_status(data["suspended_worker"], "User suspended")


def test_connect_worker_11_resend_skipped_for_accepted(workers, test_data):
    """Connect_worker_11: resending an accepted worker's invite is skipped."""
    data = test_data.get("WORKER_LIFECYCLE")
    body = workers.resend_worker_and_message(data["accepted_worker_phone"])
    assert "already accepted" in body.lower() and data["accepted_worker_phone"] in body, (
        "Expected a 'skipped - already accepted' message for the accepted worker"
    )


def test_connect_worker_14_resend_skipped_for_suspended(workers, test_data):
    """Connect_worker_14: resending a suspended worker's invite is skipped."""
    data = test_data.get("WORKER_LIFECYCLE")
    body = workers.resend_worker_and_message(data["suspended_worker_phone"])
    assert "skipped" in body.lower() and data["suspended_worker_phone"] in body, (
        "Expected a 'skipped' message for the suspended worker"
    )


def test_connect_worker_10_resend_allowed_for_pending(workers, test_data):
    """Connect_worker_10: resending a pending invite succeeds.

    (Connect_worker_09 - the 24h resend cooldown - cannot be automated: demo
    numbers do not enforce the cooldown, so a resend always succeeds.)"""
    data = test_data.get("WORKER_LIFECYCLE")
    body = workers.resend_worker_and_message(data["pending_invite_phone"])
    assert "successfully resent" in body.lower(), (
        "Expected a 'Successfully resent' message for the pending invite"
    )


def test_connect_worker_15_bulk_resend_messages(workers, test_data):
    """Connect_worker_15: bulk-resending a mix of worker states shows the
    appropriate combined messages - accepted/suspended are skipped while a pending
    invite is resent. Non-destructive (resend)."""
    data = test_data.get("WORKER_LIFECYCLE")
    body = workers.bulk_resend_and_message([
        data["accepted_worker_phone"],
        data["suspended_worker_phone"],
        data["pending_invite_phone"],
    ])
    low = body.lower()
    assert "already accepted" in low, "Bulk resend should skip the accepted/suspended workers"
    assert "successfully resent" in low, "Bulk resend should resend the pending invite"


def test_connect_worker_06_not_found_display(workers, test_data):
    """Connect_worker_06: a not-found worker shows status 'User not found' with no
    display name (only the mobile number)."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers._goto_workers_list()
    workers.verify_not_found_display(data["not_found_phone"])


def test_connect_worker_13_not_found_deletable(workers, test_data):
    """Connect_worker_13: a not-found user is deletable (Delete control enables on
    selection). Not executed, to preserve the seeded not-found worker."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers._goto_workers_list()
    workers.verify_not_found_deletable(data["not_found_phone"])


def test_connect_worker_09_resend_cooldown(workers, test_data):
    """Connect_worker_09: resending a registered invite within 24h is refused with
    a cooldown message (real number; demo numbers don't enforce the cooldown)."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.verify_resend_cooldown(data["cooldown_phone"])


def test_learn_tab_03_assessment_failed(workers, test_data):
    """Learn_tab_03: a worker who failed the assessment shows Assessment 'Failed'."""
    data = test_data.get("WORKER_LIFECYCLE")
    workers.click_tab_by_name("Learn")
    workers.verify_learn_table_headers_present()
    workers.verify_assessment_status(data["failed_assessment_worker"], "Failed")
