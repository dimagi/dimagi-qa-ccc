import pytest

from flows.ldvp_setup import resume_ldvp_opportunity
from flows.ldvp_values import new_run
from flows.olp_setup import PM_ORG
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_worker_visits_page import WorkerVisitsPage
from pages.connect_workers_page import ConnectWorkersPage
from utils.helpers import poll_until

POLL_SECONDS = 30


# Drives a real device via BrowserStack Maestro builds. Not in the per-PR gate.
@pytest.mark.on_demand
def test_e2e_ldvp_manual_review(page, test_data, config, settings):
    """CCCT-2670 - manual approve/reject, on the reusable manual-review opportunity.

    The LDVP opportunities test_e2e_ldvp.py creates verify visits automatically,
    which cannot be switched off and hides Check Duplicates. This test uses one
    long-lived opportunity with automatic verification off (LDVP.manual_* in
    web_test_data.yaml): Check Duplicates is switched on, the worker submits
    V1, V2, a copy of V1 and V3, and the Network Manager approves V1 and rejects
    V2. Covers TC-DLV-004 (duplicate flagged), TC-VER-001, TC-VER-002 and
    TC-VER-003 (only the approved visit earns).

    The worker accepts, learns and passes the assessment there once; a run that
    finds the invite still pending does that first. The payment unit allows 5
    visits a day and each run counts 4, so it runs once a day per opportunity.
    """
    from flows.mobile_runner import env_by_flow, run_flows

    ldvp = test_data.get("LDVP")
    olp1 = test_data.get("OLP_1")
    run = new_run()
    unit_amount = int(ldvp["amount"])
    sync_timeout = int(ldvp["sync_timeout_seconds_staging" if config.env == "stage" else "sync_timeout_seconds"])
    assert config.env == "prod", "The manual-review opportunity exists on prod only so far"

    worker = env_by_flow(["ldvp_learn.yaml"], config.env)["ldvp_learn.yaml"]
    phone, worker_name = worker["PHONE_NUMBER"], worker["USERNAME"]

    opp = resume_ldvp_opportunity(page, config, settings, ldvp["manual_opportunity_id"],
                                  ldvp["manual_opportunity_name"])
    workers = ConnectWorkersPage(opp.connect_page)
    print(f"STEP [LDVP-M] {opp.opportunity_name!r} ({opp.opp_id}), run stamp {run.stamp}")

    def run_device_flow(flows, **values):
        # Run values only - see test_e2e_ldvp.py: worker keys in env would override
        # each flow's own worker.
        env = {"OPPORTUNITY": opp.opportunity_name, **{k: str(v) for k, v in values.items()}}
        summary = run_flows(flows=flows, env=env, reports=False, app_env=config.env)
        print(f"STEP [LDVP-M] {flows} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"Mobile flows {flows} did not pass: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )

    workers_url = f"{opp.base_url}/a/{opp.org_slug}/opportunity/{opp.opp_id}/workers/"

    def reload_workers(tab=None):
        opp.connect_page.goto(workers_url)
        opp.connect_page.wait_for_load_state("load")
        if tab:
            workers.click_tab_by_name(tab)

    def wait_on_web(check, tab=None):
        reload_workers(tab)
        return poll_until(check, sync_timeout, POLL_SECONDS, lambda: reload_workers(tab))

    # --- 1. WEB: Check Duplicates on (needed for TC-DLV-004) ---
    ConnectOpportunitiesPage(opp.connect_page).ensure_check_duplicates(opp.base_url, opp.org_slug, opp.opp_id)

    # --- 2. One time per opportunity: accept, learn, fail, then pass the assessment ---
    reload_workers()
    if workers.worker_status(phone) == "Invite pending":
        print("STEP [LDVP-M] Worker has not joined yet - accepting, learning and passing the assessment")
        run_device_flow(["ldvp_learn.yaml"])
        wait_on_web(lambda: workers.verify_worker_status(phone, "Invite accepted"))
        run_device_flow(["ldvp_assess_fail.yaml"], FAIL_SCORE=ldvp["assessment_fail_score"])
        wait_on_web(lambda: workers.verify_assessment_status(worker_name, "Failed"), tab="Learn")
        run_device_flow(["ldvp_assess_pass.yaml"], PASS_SCORE=ldvp["assessment_pass_score"])
    wait_on_web(lambda: workers.verify_assessment_status(worker_name, "Passed"), tab="Learn")

    # Earnings accumulate across runs on a reused opportunity, so measure this
    # run's against what was there before it.
    reload_workers("Payments")
    accrued_before = _amount(workers.table_cell(worker_name, "accrued"))

    # --- 3. DEVICE: four visits (claims the job on the first run) ---
    run_device_flow(
        ["ldvp_deliver.yaml"],
        PASS_SCORE=ldvp["assessment_pass_score"],
        MAX_DAILY=ldvp["manual_max_daily"],
        MAX_TOTAL=ldvp["manual_max_total"],
        **run.device_env(),
    )

    # --- 4. WEB: nothing is decided yet; the copy of V1 is flagged (TC-DLV-004) ---
    user_id = workers.worker_user_id(opp.base_url, opp.org_slug, opp.opp_id, worker_name)
    workers.goto_worker_visits_page(opp.base_url, opp.org_slug, opp.opp_id, user_id)
    v1, v2, v3 = (run.visits[k][0] for k in ("V1", "V2", "V3"))
    for name in (v1, v2, v3):
        workers.wait_for_visit(name, timeout_seconds=sync_timeout)
    visits = WorkerVisitsPage(opp.connect_page)
    poll_until(lambda: _assert_statuses(visits, v1, ["duplicate", "pending"]),
               sync_timeout, POLL_SECONDS, opp.connect_page.reload)
    _assert_statuses(visits, v2, ["pending"])
    _assert_statuses(visits, v3, ["pending"])

    # --- 5. WEB: the Network Manager approves V1 and rejects V2 (TC-VER-001/002) ---
    home = ConnectHomePage(opp.connect_page)
    home.select_organization_from_list(olp1["network_manager"])
    workers.goto_worker_visits_page(opp.base_url, olp1["network_manager_slug"], opp.opp_id, user_id)
    visits.review_visit(v1, approve=True, text="LDVP automation - approved")
    visits.review_visit(v2, approve=False, text=ldvp["reject_reason"])
    home.select_organization_from_list(PM_ORG)

    # --- 6. WEB: only the approved visit earns (TC-VER-003) ---
    earned = accrued_before + unit_amount
    wait_on_web(lambda: _assert_amount(workers.table_cell(worker_name, "accrued"), earned, "Accrued"),
                tab="Payments")

    # --- 7. DEVICE: V2 shows rejected; earned matches web ---
    run_device_flow(["ldvp_manual_review.yaml"], VISIT_NAME_V2=v2, EARNED=earned)
    print(f"STEP [LDVP-M] Done: V1 approved, V2 rejected, copy duplicate, V3 pending; earned {earned}")


def _assert_statuses(visits, name, expected):
    statuses = sorted(visits.visit_statuses(name))
    assert statuses == sorted(expected), f"Visit {name!r} rows have statuses {statuses}, expected {expected}"


def _amount(text):
    digits = "".join(ch for ch in text.split(".")[0] if ch.isdigit())
    return int(digits) if digits else 0


def _assert_amount(text, expected, column):
    assert _amount(text) == expected, f"{column} reads {text!r}, expected {expected}"
