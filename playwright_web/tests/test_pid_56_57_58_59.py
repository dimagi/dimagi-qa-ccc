"""Personal ID - Traditional App Install & Login (web/HQ portion).

Covers the CommCare HQ Mobile Workers admin surface from the Personal ID master
plan (sheet: "CCC_ Mobile App Regression [Master] [v2]", Personal ID Tests tab):

  PID_56  "PersonalID Status" column present with valid values on Mobile Workers
  PID_57  "Unlink PersonalID" action available for a linked (Active) worker
  PID_58  clicking Unlink shows the confirmation modal (Cancel / Unlink) -> Cancel
  PID_59  confirming the unlink flips the worker to unlinked  [DESTRUCTIVE - opt-in]

PID_56-58 are read-only checks on the same page, so they run as one journey in a
single login session (matching the suite convention, e.g. test_olp_01_02_03).
The mobile-side cases (PID_48-55, 60-62) live in maestro_mobile/.
"""
import os

import pytest

from pages.cchq_login_page import LoginPage
from pages.cchq_mobile_workers_page import MobileWorkersPage


def _login_and_open_workers(page, config, settings):
    LoginPage(page).valid_login_cchq(config, settings)
    workers = MobileWorkersPage(page)
    workers.open(config)
    return workers


def test_pid_56_57_58_personalid_unlink_on_mobile_workers(page, config, settings):
    """PID_56 + PID_57 + PID_58 as a single login/logout journey."""
    workers = _login_and_open_workers(page, config, settings)

    # PID_56 - PersonalID Status column present and showing valid values.
    workers.verify_personalid_status_column_present()
    workers.verify_personalid_statuses_are_valid()

    # PID_57 - Unlink PersonalID action available for a linked worker.
    workers.verify_unlink_button_present()

    # PID_58 - Unlink shows the confirmation modal; dismiss it (non-destructive).
    workers.open_unlink_confirmation_for_first_worker()
    workers.verify_unlink_confirmation_modal()
    workers.cancel_unlink()


# Dedicated worker to unlink for PID_59, so no other worker/test is affected
# (per QA guidance). Override with PID_UNLINK_WORKER for a different worker.
PID_UNLINK_WORKER = os.getenv("PID_UNLINK_WORKER", "av_connectautomation")


def test_pid_59_confirm_unlink_flips_status(page, config, settings):
    """PID_59 (destructive) - confirming the unlink flips the dedicated worker to
    Not Linked / Inactive.

    This actually unlinks a live worker and is non-idempotent (re-linking needs
    the mobile PersonalID flow, PID_51). To stay safe it only acts on the one
    dedicated worker PID_UNLINK_WORKER, and skips - rather than fails - when that
    worker is not present-and-linked on the current domain, so CI never reddens
    when the linked state has been consumed. Re-link the worker (mobile PID_51 on
    this domain) and it runs on the next pass.
    """
    workers = _login_and_open_workers(page, config, settings)

    status = workers.worker_personalid_status(PID_UNLINK_WORKER)
    if status != "Active":
        pytest.skip(
            f"Dedicated worker '{PID_UNLINK_WORKER}' is not linked (status={status!r}) "
            "on this domain - re-link it via the mobile flow (PID_51), then PID_59 runs."
        )

    workers.open_unlink_confirmation_for_worker(PID_UNLINK_WORKER)
    workers.verify_unlink_confirmation_modal()
    workers.confirm_unlink()

    workers.open(config)  # refresh the list
    status = workers.worker_personalid_status(PID_UNLINK_WORKER)
    assert status in ("Not Linked", "Inactive"), (
        f"Expected '{PID_UNLINK_WORKER}' unlinked after confirm; saw '{status}'"
    )
