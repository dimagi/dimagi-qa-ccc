"""Connect Workers invite lifecycle (Connect_worker_02/_03/_05/_08/_12).

  Connect_worker_02 - a not-yet-accepted invite shows the 'Invite pending' status
  Connect_worker_03 - Resend/Delete buttons enable only when an invite is selected
  Connect_worker_05 - pre-invite an unregistered reserved number
  Connect_worker_12 - resending a not-registered number is skipped (naming message)
  Connect_worker_08 - the invite can then be deleted

_02/_03 are zero-mutation (they read an existing pending invite); _05/_12/_08 send
one SMS to a reserved number and self-clean by deleting it. The opportunity and the
reserved number come from test_data (WORKER_INVITES). The seeded-data cases
(_04/_06/_07/_09/_10/_11/_13/_14/_15) live in test_worker_lifecycle.py.
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
    opp = test_data.get("WORKER_INVITES")["opportunity_name"]
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


def test_connect_worker_05_12_08_invite_resend_delete(workers_list, test_data):
    """Connect_worker_05: pre-invite an unregistered reserved number (appears as an
      invite even though it is not registered on PersonalID yet).
    Connect_worker_12: resending an invite for a not-found (unregistered) number is
      skipped, with a message naming the skipped number.
    Connect_worker_08: the invite can then be deleted.

    Sends one SMS to a reserved number and self-cleans by deleting the invite.
    (Connect_worker_09 - the 24h resend cooldown - needs a *registered* pending
    number, so it is deferred to the seeded data.)"""
    workers = workers_list
    reserved = test_data.get("WORKER_INVITES")["reserved_invite"]

    # Clear any leftover from an interrupted prior run.
    if workers.worker_row_present(reserved):
        workers.delete_worker_invite(reserved)

    # _05 - pre-invite an unregistered reserved number; it appears as an invite.
    workers.invite_worker(reserved)
    assert workers.worker_row_present(reserved), "Invited number did not appear as an invite"

    # _12 - resending a not-registered number is skipped with a naming message.
    workers.select_worker_row(reserved)
    body = workers.resend_selected_invite()
    assert "not registered on personalid" in body.lower() and reserved in body, (
        f"Expected a 'skipped - not registered on PersonalID' message naming {reserved}; "
        f"body did not contain it."
    )

    # _08 - delete the invite; it disappears.
    workers.delete_worker_invite(reserved)
    assert not workers.worker_row_present(reserved), "Invite still present after delete"
