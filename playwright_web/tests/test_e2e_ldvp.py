import pytest

from flows.ldvp_setup import create_ldvp_opportunity, invite_and_wait
from flows.olp_setup import PM_ORG
from flows.ldvp_values import expected_earned, new_run
from pages.connect_home_page import ConnectHomePage
from pages.connect_worker_visits_page import WorkerVisitsPage
from utils.helpers import poll_until

# How long web waits for something the device did to show up. The device ->
# CommCare HQ -> Connect hop takes minutes on staging.
SYNC_TIMEOUT = 900
POLL_SECONDS = 20


# Drives a real device via BrowserStack Maestro builds - six device sessions, so
# a full run takes about an hour. Not in the per-PR gate.
@pytest.mark.on_demand
def test_e2e_ldvp(page, test_data, config, settings):
    """CCCT-2670 - Learn, Deliver, Verify, Payment, end to end.

    A fresh opportunity per run (a worker learns and takes the assessment once
    per opportunity), the worker invited on web, then web stages alternating
    with device sessions. A session ends wherever web has to act before the
    device can see the result, since a Maestro build cannot pause.

    Plan: test_plans/CCCT-2670_LDVP_Automation_Test_Plan.xlsx. Covers TC-INV-001..004,
    TC-LRN-001..005, TC-DLV-001..005, TC-VER-001..003, TC-PAY-001..004 and, for
    free, TC-REG-002 (every session after the first starts from a cleared app and
    recovers the account, and progress has to be there).
    """
    from flows.mobile_runner import env_by_flow, run_flows

    ldvp = test_data.get("LDVP")
    run = new_run()
    unit_amount = int(ldvp["amount"])

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

    # --- 1. WEB: fresh opportunity, invite (TC-INV-001) ---
    opp = create_ldvp_opportunity(page, config, settings, test_data)
    print(f"STEP [LDVP] Opportunity {opp.opportunity_name!r} ({opp.opp_id}), run stamp {run.stamp}")
    workers = invite_and_wait(opp, full_number, phone)
    # The first run on an environment invites a number PersonalID does not know
    # yet - the device registers it later - and Connect labels that "User not
    # found". Every later run invites a registered number: "Invite pending".
    status = workers.worker_status(phone)
    assert status in ("Invite pending", "User not found"), f"Invited worker shows {status!r}"
    print(f"STEP [LDVP] Invited {full_number}: {status!r}")

    # --- 2. DEVICE: uninvited worker looks; invited worker learns ---
    run_device_flow(
        ["ldvp_uninvited.yaml", "ldvp_learn.yaml"],
        FAIL_SCORE=ldvp["assessment_fail_score"],
        PASS_SCORE=ldvp["assessment_pass_score"],
        PASSING_SCORE=test_data.get("OLP_1")["passing_score"],
        MAX_DAILY=ldvp["max_daily"],
        MAX_TOTAL=ldvp["max_total"],
    )

    # --- 3. WEB: accepted (TC-INV-003) and passed (TC-LRN-003 / TC-LRN-005) ---
    workers_url = f"{opp.base_url}/a/{opp.org_slug}/opportunity/{opp.opp_id}/workers/"

    def reload_workers(tab=None):
        opp.connect_page.goto(workers_url)
        opp.connect_page.wait_for_load_state("load")
        if tab:
            workers.click_tab_by_name(tab)

    reload_workers()
    poll_until(lambda: workers.verify_worker_status(phone, "Invite accepted"),
               SYNC_TIMEOUT, POLL_SECONDS, reload_workers)
    reload_workers("Learn")
    poll_until(lambda: workers.verify_assessment_status(worker_name, "Passed"),
               SYNC_TIMEOUT, POLL_SECONDS, lambda: reload_workers("Learn"))

    # --- 4. DEVICE: four visits ---
    run_device_flow(["ldvp_deliver.yaml"], **run.device_env())

    # --- 5. WEB: what each visit became, then review (TC-DLV-002..005) ---
    user_id = workers.worker_user_id(opp.base_url, opp.org_slug, opp.opp_id, worker_name)
    workers.goto_worker_visits_page(opp.base_url, opp.org_slug, opp.opp_id, user_id)
    v1, v2, v3 = (run.visits[k][0] for k in ("V1", "V2", "V3"))
    for name in (v1, v2, v3):
        workers.wait_for_visit(name, timeout_seconds=SYNC_TIMEOUT)
    visits = WorkerVisitsPage(opp.connect_page)

    # The duplicate shares V1's name, so V1 must show exactly two rows: the
    # original still pending and the copy marked duplicate (TC-DLV-004).
    poll_until(lambda: _assert_statuses(visits, v1, ["duplicate", "pending"]),
               SYNC_TIMEOUT, POLL_SECONDS, opp.connect_page.reload)
    _assert_statuses(visits, v2, ["pending"])  # TC-DLV-003: recorded without location
    _assert_statuses(visits, v3, ["over_limit"])  # TC-DLV-005

    # Review as the Network Manager, the org that approves and rejects visits.
    home = ConnectHomePage(opp.connect_page)
    nm = test_data.get("OLP_1")["network_manager"]
    home.select_organization_from_list(nm)
    nm_slug = test_data.get("OLP_1")["network_manager_slug"]
    workers.goto_worker_visits_page(opp.base_url, nm_slug, opp.opp_id, user_id)
    visits.review_visit(v1, approve=True, text="LDVP automation - approved")  # TC-VER-001
    visits.review_visit(v2, approve=False, text=ldvp["reject_reason"])  # TC-VER-002
    home.select_organization_from_list(PM_ORG)

    # --- TC-VER-003: only the approved visit is earned ---
    payments_url = workers_url + "payments/"

    def reload_payments():
        reload_workers("Payments")

    reload_payments()
    want = expected_earned(approved=1, unit_amount=unit_amount)
    poll_until(lambda: _assert_amount(workers.payments_cell(worker_name, "accrued"), want, "Accrued"),
               SYNC_TIMEOUT, POLL_SECONDS, reload_payments)

    # Pay exactly what was earned, so the device's transferred total can only be
    # right one way.
    workers.make_payment_for_worker(worker_name, amount=want)
    workers.wait_for_last_paid_populated(worker_name)

    # --- 6. DEVICE: statuses, earned, the confirmation card; tap Yes ---
    run_device_flow(["ldvp_payment.yaml"], VISIT_NAME_V2=v2, EARNED=want, TRANSFERRED=want)

    # --- 7. WEB: the confirmation shows (TC-PAY-002); a second payment ---
    reload_payments()
    poll_until(lambda: _assert_confirmed(workers.payments_cell(worker_name, "confirm")),
               SYNC_TIMEOUT, POLL_SECONDS, reload_payments)
    second = int(ldvp["second_payment"])
    workers.make_payment_for_worker(worker_name, amount=second)

    # --- 8. DEVICE: Ask me later (TC-PAY-003) ---
    run_device_flow(["ldvp_ask_later.yaml"], TRANSFERRED=want + second)

    # --- 9. WEB: roll the second payment back ---
    reload_payments()
    workers.rollback_last_payment()

    # --- 10. DEVICE: the rollback is reflected (TC-PAY-004) ---
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
