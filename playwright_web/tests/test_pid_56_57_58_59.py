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


@pytest.fixture(scope="module")
def workers(browser, config, settings):
    """One CCHQ login for the whole module; each test re-navigates to a clean
    Mobile Workers list with workers.open(config). Retries the flaky login once."""
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            wk = _login_and_open_workers(page, config, settings)
        except Exception:
            page.close()
            page = context.new_page()
            wk = _login_and_open_workers(page, config, settings)
        yield wk
    finally:
        context.close()


def test_pid_56_57_58_personalid_unlink_on_mobile_workers(workers, config):
    """PID_56 + PID_57 + PID_58 as a single read-only journey (shared session)."""
    workers.open(config)  # reset to a clean Mobile Workers list

    # PID_56 - PersonalID Status column present and showing valid values.
    workers.verify_personalid_status_column_present()
    workers.verify_personalid_statuses_are_valid()

    # PID_57 - Unlink PersonalID action available for a linked worker.
    workers.verify_unlink_button_present()

    # PID_58 - Unlink shows the confirmation modal; dismiss it (non-destructive).
    workers.open_unlink_confirmation_for_first_worker()
    workers.verify_unlink_confirmation_modal()
    workers.cancel_unlink()


# Preferred worker to unlink for PID_59. Falls back to any currently-linked
# worker if this one is not available. Override with PID_UNLINK_WORKER.
PID_UNLINK_WORKER = os.getenv("PID_UNLINK_WORKER", "CCC-Automationuser1")


def _pick_linked_target(workers, config):
    """Return the first-name of a worker with an active PersonalID link to use as
    the unlink target - preferring PID_UNLINK_WORKER, restoring it if it was left
    unlinked, then falling back to any other linked worker. None if none exist."""
    if workers.worker_personalid_status(PID_UNLINK_WORKER) == "Active":
        return PID_UNLINK_WORKER
    if workers.worker_has_link_action(PID_UNLINK_WORKER):
        workers.link_worker(PID_UNLINK_WORKER)
        workers.open(config)
        if workers.worker_personalid_status(PID_UNLINK_WORKER) == "Active":
            return PID_UNLINK_WORKER
    return workers.first_linked_worker_name()


def test_pid_59_confirm_unlink_flips_status(workers, config):
    """PID_59 (destructive, self-restoring) - confirming the unlink flips a linked
    worker to Not Linked / Inactive.

    Runs every time and actually unlinks a live worker, then RE-LINKS it so the
    test is idempotent (HQ restores the worker's prior PersonalID association with
    no input). Targets the dedicated PID_UNLINK_WORKER, or any other linked worker
    if that one isn't available. Only skips if the domain has no linked worker at
    all (nothing to unlink)."""
    workers.open(config)  # reset to a clean Mobile Workers list

    target = _pick_linked_target(workers, config)
    if not target:
        pytest.skip("No worker with an active PersonalID link on this domain to unlink.")

    # --- the actual test: unlink and confirm the status flips ---
    workers.open_unlink_confirmation_for_worker(target)
    workers.verify_unlink_confirmation_modal()
    workers.confirm_unlink()

    workers.open(config)  # refresh the list
    status = workers.worker_personalid_status(target)
    assert status in ("Not Linked", "Inactive"), (
        f"Expected '{target}' unlinked after confirm; saw '{status}'"
    )

    # --- restore state so the test is idempotent for the next run ---
    workers.link_worker(target)
    workers.open(config)
    restored = workers.worker_personalid_status(target)
    assert restored == "Active", (
        f"Failed to restore link for '{target}'; status={restored!r}"
    )
