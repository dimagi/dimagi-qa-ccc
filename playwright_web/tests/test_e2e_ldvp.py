import os
from datetime import date, timedelta

import pytest
from playwright.sync_api import Error as PlaywrightError

from flows.ldvp_setup import create_ldvp_opportunity, invite_and_wait, resume_ldvp_opportunity
from flows.ldvp_values import assert_percent, expected_earned, new_run
from pages.connect_worker_visits_page import WorkerVisitsPage
from pages.connect_workers_page import ConnectWorkersPage
from utils.helpers import poll_until

POLL_SECONDS = 30


# Device sessions on BrowserStack, about an hour a run. Each run creates an
# opportunity, app copies, payments and a rollback, so it is opt-in only: a manual
# dispatch with include_seed_consuming, never PR or post-deploy.
@pytest.mark.on_demand
@pytest.mark.consumes_seed_data
def test_e2e_ldvp(page, test_data, config, settings):
    """CCCT-2670 - Learn, Deliver, Verify, Payment, end to end.

    A fresh opportunity per run, then web stages alternating with device
    sessions. A session ends wherever web has to act before the device can see
    the result, since a Maestro build cannot pause.

    Plan: test_plans/CCCT-2670_LDVP_Automation_Test_Plan.xlsx. Covers TC-INV-001..004,
    TC-LRN-001..005, TC-DLV-001..003 and 005, TC-VER-001 and 003, TC-PAY-001..004 and
    TC-REG-002 (every session after the first recovers the account on a cleared app).

    Resume a run with LDVP_RESUME_OPP_ID and LDVP_RESUME_OPP_NAME, and
    LDVP_RESUME_AT one of:
      deliver (default) - the worker has passed the assessment
      assess            - the worker has learned
      pass              - the worker has failed the assessment once
      verify            - the visits are made; also set LDVP_RESUME_STAMP to their run stamp
      payment           - the worker has been paid what it earned
    """
    from flows.mobile_runner import env_by_flow, run_flows

    ldvp = test_data.get("LDVP")
    run = new_run()
    unit_amount = int(ldvp["amount"])
    # How long web waits for Connect to process a device submission: instant on
    # prod, slow on staging.
    sync_timeout = int(ldvp["sync_timeout_seconds_staging" if config.env == "stage" else "sync_timeout_seconds"])

    # The same worker entry the device signs in with.
    worker = env_by_flow(["ldvp_learn.yaml"], config.env)["ldvp_learn.yaml"]
    phone, worker_name = worker["PHONE_NUMBER"], worker["USERNAME"]
    full_number = f"{worker['COUNTRY_CODE']}{phone}"

    def run_device_flow(flows, **values):
        # Run values only: env wins over each flow's own worker, so a worker key
        # here would sign the uninvited check in as the invited worker.
        env = {"OPPORTUNITY": opp.opportunity_name, **{k: str(v) for k, v in values.items()}}
        summary = run_flows(flows=flows, env=env, reports=False, app_env=config.env)
        print(f"STEP [LDVP] {flows} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"Mobile flows {flows} did not pass: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )

    resume_id = os.environ.get("LDVP_RESUME_OPP_ID")
    resume_at = os.environ.get("LDVP_RESUME_AT", "deliver") if resume_id else None
    assert resume_at in (None, "assess", "pass", "deliver", "verify", "payment"), (
        f"LDVP_RESUME_AT must be assess, pass, deliver, verify or payment, not {resume_at!r}")
    if resume_at == "verify":
        # A stamp is the last six digits of an epoch, so it round-trips through new_run.
        run = new_run(now=int(os.environ["LDVP_RESUME_STAMP"]))
    if resume_id:
        opp = resume_ldvp_opportunity(page, config, settings, resume_id, os.environ["LDVP_RESUME_OPP_NAME"])
        workers = ConnectWorkersPage(opp.connect_page)
        print(f"STEP [LDVP] Resuming {opp.opportunity_name!r} ({opp.opp_id}) at {resume_at}, run stamp {run.stamp}")
    else:
        # --- 1. WEB: fresh opportunity, invite (TC-INV-001) ---
        opp = create_ldvp_opportunity(page, config, settings, test_data)
        print(f"STEP [LDVP] Opportunity {opp.opportunity_name!r} ({opp.opp_id}), run stamp {run.stamp}")
        workers = invite_and_wait(opp, full_number, phone)
        # An invite to a number PersonalID does not know stays "User not found",
        # even after the number signs up.
        status = workers.worker_status(phone)
        assert status == "Invite pending", (
            f"Invited worker shows {status!r}, expected 'Invite pending'. 'User not found' means "
            f"{full_number} is not registered on this environment - run seed_ldvp_worker.yaml once "
            f"(see MAESTRO_LDVP_WORKER in test_data/mobile_workers.yaml)."
        )

    workers_url = f"{opp.base_url}/a/{opp.org_slug}/opportunity/{opp.opp_id}/workers/"

    def reload_workers(tab=None):
        # Staging page loads can overrun the default 30s.
        opp.connect_page.goto(workers_url, timeout=90000)
        opp.connect_page.wait_for_load_state("load", timeout=90000)
        if tab:
            workers.click_tab_by_name(tab)

    def wait_on_web(check, tab=None):
        def attempt():
            # A load timeout or dropped connection is one more "not yet", not the end.
            try:
                reload_workers(tab)
            except PlaywrightError as error:
                raise AssertionError(f"Workers page did not load: {error}") from None
            return check()

        return poll_until(attempt, sync_timeout, POLL_SECONDS, lambda: None)

    if resume_at not in ("deliver", "verify", "payment"):
        # Each learn session is followed by a web wait for Connect to process it.

        if not resume_at:
            # --- 2. DEVICE: uninvited worker looks; invited worker accepts and learns ---
            run_device_flow(["ldvp_uninvited.yaml", "ldvp_learn.yaml"])

        if resume_at != "pass":
            # --- 3. WEB: accepted (TC-INV-003); both modules counted (TC-LRN-001/003) ---
            # Also when resumed at the assessment: it needs both modules counted.
            wait_on_web(lambda: workers.verify_worker_status(phone, "Invite accepted"))
            wait_on_web(lambda: assert_percent(workers.table_cell(worker_name, "modules completed"), 100,
                                               "Modules completed"), tab="Learn")

        if resume_at != "pass":
            # --- 4. DEVICE: 2 of 2 (TC-LRN-002); fail the assessment (TC-LRN-004) ---
            run_device_flow(["ldvp_assess_fail.yaml"], FAIL_SCORE=ldvp["assessment_fail_score"])
            wait_on_web(lambda: workers.verify_assessment_status(worker_name, "Failed"), tab="Learn")

        # --- 5. DEVICE: failed state shown (TC-LRN-004); pass it (TC-LRN-005) ---
        run_device_flow(["ldvp_assess_pass.yaml"], PASS_SCORE=ldvp["assessment_pass_score"])
        wait_on_web(lambda: workers.verify_assessment_status(worker_name, "Passed"), tab="Learn")

    if resume_at not in ("verify", "payment"):
        # --- 6. DEVICE: certificate (TC-LRN-005), details (TC-DLV-001), claim, visits ---
        run_device_flow(
            ["ldvp_deliver.yaml"],
            PASS_SCORE=ldvp["assessment_pass_score"],
            MAX_DAILY=ldvp["max_daily"],
            MAX_TOTAL=ldvp["max_total"],
            SUBMIT_DUPLICATE="false",
            **run.device_env(),
        )

    payments_url = workers_url + "payments/"

    def reload_payments():
        reload_workers("Payments")

    approved = 2
    want = expected_earned(approved=approved, unit_amount=unit_amount)

    if resume_at != "payment":
        # --- 7. WEB: what each visit became (TC-DLV-002..005, TC-VER-001) ---
        user_id = workers.worker_user_id(opp.base_url, opp.org_slug, opp.opp_id, worker_name)
        workers.goto_worker_visits_page(opp.base_url, opp.org_slug, opp.opp_id, user_id)
        v1, v2, v3 = (run.visits[k][0] for k in ("V1", "V2", "V3"))
        for name in (v1, v2, v3):
            workers.wait_for_visit(name, timeout_seconds=sync_timeout)
        visits = WorkerVisitsPage(opp.connect_page)

        # LDVP opportunities verify automatically, and an auto-verified one approves
        # and pays a duplicate (known behaviour), so no duplicate is submitted here;
        # TC-DLV-004 is covered by the manual-review test.
        poll_until(lambda: _assert_statuses(visits, v1, ["approved"]),
                   sync_timeout, POLL_SECONDS, opp.connect_page.reload)
        _assert_statuses(visits, v2, ["approved"])  # TC-DLV-003: recorded without location
        _assert_statuses(visits, v3, ["over_limit"])  # TC-DLV-005

        # --- TC-VER-003: only the approved visits are earned (V1 and V2) ---
        reload_payments()
        poll_until(lambda: _assert_amount(workers.table_cell(worker_name, "accrued"), want, "Accrued"),
                   sync_timeout, POLL_SECONDS, reload_payments)

        # Pay exactly what was earned. Dated yesterday: Rollback Last Payment picks
        # the newest by date only, so it must not tie with the second payment.
        workers.make_payment_for_worker(worker_name, amount=want, paid_on=date.today() - timedelta(days=1))
        workers.wait_for_last_paid_populated(worker_name)

    # --- 8. DEVICE: statuses, earned, transferred; confirm the payment (Yes) ---
    # The payment notification reaches one sign-in only, so a resumed session skips it.
    run_device_flow(["ldvp_payment.yaml"], APPROVED=approved, EARNED=want, TRANSFERRED=want,
                    CHECK_PAYMENT_PUSH="false" if resume_at == "payment" else "true")

    # --- 9. WEB: the confirmation shows (TC-PAY-002); a second payment ---
    reload_payments()
    poll_until(lambda: _assert_confirmed(workers.table_cell(worker_name, "confirm")),
               sync_timeout, POLL_SECONDS, reload_payments)
    second = int(ldvp["second_payment"])
    workers.make_payment_for_worker(worker_name, amount=second)

    # --- 10. DEVICE: answering No leaves it unconfirmed (TC-PAY-003) ---
    run_device_flow(["ldvp_decline_confirm.yaml"], SECOND_PAYMENT=second, TRANSFERRED=want + second)

    # --- 11. WEB: roll the second payment back (from the Last-paid history popup) ---
    reload_payments()
    workers.click_last_paid_and_verify_history(worker_name)
    workers.rollback_last_payment()
    reload_payments()
    poll_until(lambda: _assert_amount(workers.table_cell(worker_name, "total paid"), want, "Total paid"),
               sync_timeout, POLL_SECONDS, reload_payments)

    # --- 12. DEVICE: the rollback is reflected (TC-PAY-004) ---
    run_device_flow(["ldvp_rollback.yaml"], TRANSFERRED=want)
    print(f"STEP [LDVP] Chain complete for {opp.opportunity_name!r}; payments page {payments_url}")


def _assert_statuses(visits, name, expected):
    statuses = sorted(visits.visit_statuses(name))
    assert statuses == sorted(expected), f"Visit {name!r} rows have statuses {statuses}, expected {expected}"


def _assert_amount(text, expected, column):
    digits = "".join(ch for ch in text.split(".")[0] if ch.isdigit())
    assert digits == str(expected), f"{column} reads {text!r}, expected {expected}"


def _assert_confirmed(text):
    # Anything but the empty dash means a confirmation arrived.
    assert text and text not in ("—", "-"), f"Confirm column still empty: {text!r}"
