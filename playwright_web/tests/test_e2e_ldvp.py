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


# Drives a real device via BrowserStack Maestro builds - eight device sessions,
# each gated on web, so a full run takes an hour or more on staging. Not in the
# per-PR gate.
@pytest.mark.on_demand
def test_e2e_ldvp(page, test_data, config, settings):
    """CCCT-2670 - Learn, Deliver, Verify, Payment, end to end.

    A fresh opportunity per run (a worker learns and takes the assessment once
    per opportunity), the worker invited on web, then web stages alternating
    with device sessions. A session ends wherever web has to act before the
    device can see the result, since a Maestro build cannot pause.

    Plan: test_plans/CCCT-2670_LDVP_Automation_Test_Plan.xlsx. Covers TC-INV-001..004,
    TC-LRN-001..005, TC-DLV-001..003 and 005, TC-VER-001 and 003, TC-PAY-001..004 and, for
    free, TC-REG-002 (every session after the first starts from a cleared app and
    recovers the account, and progress has to be there).

    To resume a run, set LDVP_RESUME_OPP_ID and LDVP_RESUME_OPP_NAME to its
    opportunity. By default it resumes at delivery (the worker has passed the
    assessment; stages 1-5 are skipped). LDVP_RESUME_AT=assess resumes at the
    assessment instead (the worker has learned; stages 1-2 are skipped and the
    web waits of stage 3 still run), and
    LDVP_RESUME_AT=pass at passing it (the worker has already failed it once;
    stages 1-4 are skipped - the fail flow needs a never-taken assessment), and
    LDVP_RESUME_AT=verify at the web check of the visits (stages 1-6 are
    skipped; set LDVP_RESUME_STAMP to the run stamp the visits were made with),
    and LDVP_RESUME_AT=payment at the device payment session (the worker has
    been paid what it earned; stages 1-7 are skipped).
    """
    from flows.mobile_runner import env_by_flow, run_flows

    ldvp = test_data.get("LDVP")
    run = new_run()
    unit_amount = int(ldvp["amount"])
    # How long web waits for Connect to process something the device submitted.
    # The device -> CommCare HQ -> Connect hop is instant on prod but can take a
    # long while on staging, so the limit is per environment test data.
    sync_timeout = int(ldvp["sync_timeout_seconds_staging" if config.env == "stage" else "sync_timeout_seconds"])

    # The worker comes from mobile_workers.yaml - the same entry the device signs
    # in with - so web asserts on the identity the device actually used.
    worker = env_by_flow(["ldvp_learn.yaml"], config.env)["ldvp_learn.yaml"]
    phone, worker_name = worker["PHONE_NUMBER"], worker["USERNAME"]
    full_number = f"{worker['COUNTRY_CODE']}{phone}"

    def run_device_flow(flows, **values):
        # Run values only. Worker keys must not go in here: run_flows lets env win
        # over each flow's own worker, which would sign the uninvited check in as
        # the invited worker.
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
        # The visits already exist under the stamp they were made with; a stamp
        # is the last six digits of an epoch, so it round-trips through new_run.
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
        # The worker has to be registered before it is invited: an invite to a number
        # PersonalID does not know reads "User not found" and never attaches to the
        # account when the number signs up later.
        status = workers.worker_status(phone)
        assert status == "Invite pending", (
            f"Invited worker shows {status!r}, expected 'Invite pending'. 'User not found' means "
            f"{full_number} is not registered on this environment - run seed_ldvp_worker.yaml once "
            f"(see MAESTRO_LDVP_WORKER in test_data/mobile_workers.yaml)."
        )


    workers_url = f"{opp.base_url}/a/{opp.org_slug}/opportunity/{opp.opp_id}/workers/"

    def reload_workers(tab=None):
        # 90s: a staging page load overran the default 30s mid-run (2026-11-03).
        opp.connect_page.goto(workers_url, timeout=90000)
        opp.connect_page.wait_for_load_state("load", timeout=90000)
        if tab:
            workers.click_tab_by_name(tab)

    def wait_on_web(check, tab=None):
        def attempt():
            # A load that still times out, or a dropped connection
            # (ERR_NETWORK_CHANGED ended a 3-hour staging wait, 2026-11-03), is
            # one more "not yet" for the wait, not the end of the run.
            try:
                reload_workers(tab)
            except PlaywrightError as error:
                raise AssertionError(f"Workers page did not load: {error}") from None
            return check()

        return poll_until(attempt, sync_timeout, POLL_SECONDS, lambda: None)

    if resume_at not in ("deliver", "verify", "payment"):
        # The learn part is three device sessions, each followed by a web wait for
        # Connect to have processed what it submitted: on staging that can take far
        # longer than a device session should sit re-syncing.

        if not resume_at:
            # --- 2. DEVICE: uninvited worker looks; invited worker accepts and learns ---
            run_device_flow(["ldvp_uninvited.yaml", "ldvp_learn.yaml"])

        if resume_at != "pass":
            # --- 3. WEB: accepted (TC-INV-003); both modules counted (TC-LRN-001/003) ---
            # Also on a run resumed at the assessment: staging can still be
            # processing the learn modules, and the assessment session needs them
            # counted (2026-11-03 it started too early and saw fewer than 2 of 2).
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
        # --- 6. DEVICE: certificate (TC-LRN-005), details (TC-DLV-001), claim, four visits ---
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

        # LDVP opportunities verify visits automatically (it cannot be switched off;
        # manual approve/reject is its own test on a manual-review opportunity).
        # This chain submits no duplicate: an auto-verified opportunity cannot flag
        # one, approves and pays it, and the app then counts it differently from web
        # (known behaviour, prod 2026-11-02). Duplicates (TC-DLV-004) are covered on
        # the manual-review opportunity.
        poll_until(lambda: _assert_statuses(visits, v1, ["approved"]),
                   sync_timeout, POLL_SECONDS, opp.connect_page.reload)
        _assert_statuses(visits, v2, ["approved"])  # TC-DLV-003: recorded without location
        _assert_statuses(visits, v3, ["over_limit"])  # TC-DLV-005

        # --- TC-VER-003: only the approved visits are earned (V1 and V2) ---
        reload_payments()
        poll_until(lambda: _assert_amount(workers.table_cell(worker_name, "accrued"), want, "Accrued"),
                   sync_timeout, POLL_SECONDS, reload_payments)

        # Pay exactly what was earned, so the device's transferred total can only be
        # right one way. Dated yesterday: Rollback Last Payment picks the newest by
        # date_paid, a date with no time, so two payments made today tie and it can
        # roll back this one instead of the second (prod 2026-11-02).
        workers.make_payment_for_worker(worker_name, amount=want, paid_on=date.today() - timedelta(days=1))
        workers.wait_for_last_paid_populated(worker_name)

    # --- 8. DEVICE: statuses, earned, transferred; confirm the payment (Yes) ---
    # A resumed session cannot see the payment notification again: the server
    # delivers it to one sign-in only.
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

    # --- 11. WEB: roll the second payment back ---
    reload_payments()
    # Rollback lives in the Last-paid history popup, not on the Payments tab.
    workers.click_last_paid_and_verify_history(worker_name)
    workers.rollback_last_payment()
    # It must have removed the second payment, leaving only what was earned.
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
    # Plan Q4: what the Confirm column shows once the worker taps Yes is not
    # documented; anything but the empty dash means a confirmation arrived.
    assert text and text not in ("—", "-"), f"Confirm column still empty: {text!r}"
