from datetime import date

import pytest

from flows.landing_setup import create_new_fixture
from flows.ldvp_setup import resume_ldvp_opportunity

# Drives a real device via BrowserStack Maestro builds. Not in the per-PR gate.
FLOWS = ["landing_list.yaml", "landing_tabs.yaml"]


@pytest.mark.on_demand
def test_connect_landing_and_delivery_tabs(page, test_data, config, settings):
    """Connect landing page (the list behind "Go to Connect menu") and the 2.65
    delivery tabs, on long-lived fixture opportunities.

    Plan: test_plans/Connect_Landing_And_Delivery_Tabs_Test_Plan.xlsx. Nothing is
    created per run: web checks each fixture is still in its state, reads the
    values the device must show, and two device sessions compare. A fixture
    that has moved fails here with how to rebuild it - except New (F5), which
    is rebuilt on the spot because accepting it once is enough to spoil it.
    """
    from flows.mobile_runner import env_by_flow, run_flows

    landing, ldvp = test_data.get("LANDING"), test_data.get("LDVP")
    suffix = "_staging" if config.env == "stage" else ""

    def fixture(key):
        opp_id = landing.get(f"{key}_opportunity_id{suffix}")
        assert opp_id, f"No LANDING.{key}_opportunity_id{suffix} - build the fixture first (see web_test_data.yaml)"
        return opp_id, landing[f"{key}_opportunity_name{suffix}"]

    worker = env_by_flow(["landing_list.yaml"], config.env)["landing_list.yaml"]
    phone, worker_name = worker["PHONE_NUMBER"], worker["USERNAME"]

    f1_id, f1_name = fixture("delivering")
    opp = resume_ldvp_opportunity(page, config, settings, f1_id, f1_name)
    from pages.connect_workers_page import ConnectWorkersPage
    workers = ConnectWorkersPage(opp.connect_page)

    def open_workers(opp_id, tab=None):
        opp.connect_page.goto(f"{opp.base_url}/a/{opp.org_slug}/opportunity/{opp_id}/workers/", timeout=90000)
        opp.connect_page.wait_for_load_state("load", timeout=90000)
        if tab:
            workers.click_tab_by_name(tab)

    # --- F1 Delivering: active, an approved visit and a payment; read its numbers ---
    open_workers(f1_id, "Deliver")
    approved = _count(workers.table_cell(worker_name, "approved"))
    # An auto-verify opportunity's Deliver tab has a Status column instead of
    # Pending: nothing there waits for review (prod 2026-11-05).
    pending = (_count(workers.table_cell(worker_name, "pending"))
               if "pending" in [c.lower() for c in workers.present_deliver_count_columns()] else 0)
    open_workers(f1_id, "Payments")
    earned = _count(workers.table_cell(worker_name, "accrued"))
    transferred = _count(workers.table_cell(worker_name, "total paid"))
    assert approved >= 1 and transferred >= 1, (
        f"F1 {f1_name!r} has {approved} approved visits and {transferred} paid - it needs both. Rebuild it: "
        f"test_e2e_ldvp.py with LDVP_DAYS=300, then record it as LANDING.delivering_opportunity_id{suffix}")
    print(f"STEP [LANDING] F1 from web: approved {approved}, pending {pending}, earned {earned}, "
          f"transferred {transferred}")

    # --- F5 New: still only invited; rebuilt if someone accepted it ---
    f5_id, f5_name = fixture("new")
    open_workers(f5_id)
    status = workers.worker_status(phone)
    if status != "Invite pending":
        print(f"STEP [LANDING] F5 {f5_name!r} reads {status!r}, not 'Invite pending' - building a new one")
        full_number = f"{worker['COUNTRY_CODE']}{phone}"
        new_opp, workers = create_new_fixture(page, config, settings, test_data, full_number, phone)
        f5_id, f5_name = new_opp.opp_id, new_opp.opportunity_name
        print(f"STEP [LANDING] Record the new F5: LANDING.new_opportunity_id{suffix}: \"{f5_id}\" / "
              f"new_opportunity_name{suffix}: \"{f5_name}\"")
        opp = new_opp

    # --- F6 Learning: accepted, assessment never passed ---
    f6_id, f6_name = fixture("learning")
    open_workers(f6_id)
    status = workers.worker_status(phone)
    open_workers(f6_id, "Learn")
    assessment = workers.table_cell(worker_name, "assessment")
    assert status == "Invite accepted" and assessment.lower() != "passed", (
        f"F6 {f6_name!r} reads {status!r} / assessment {assessment!r} - it must be accepted and not passed. "
        f"Rebuild it: test_landing_fixtures.py with LANDING_FIXTURE=learning")

    # --- F3 Ended: its cases wait until the end date has passed ---
    f3_id, f3_name = fixture("ended")
    ended = date.today() > date.fromisoformat(landing[f"ended_opportunity_end_date{suffix}"])
    if not ended:
        print(f"STEP [LANDING] F3 {f3_name!r} has not ended yet - its cases are skipped this run")

    summary = run_flows(
        flows=FLOWS,
        env={
            "OPPORTUNITY": f1_name,
            "OPP_DELIVERING": f1_name, "OPP_NEW": f5_name, "OPP_LEARNING": f6_name, "OPP_ENDED": f3_name,
            "ENDED_CHECK": "true" if ended else "false",
            "APPROVED": str(approved), "PENDING": str(pending),
            "EARNED": str(earned), "TRANSFERRED": str(transferred),
            "VISITS_AMOUNT": str(approved * int(ldvp["amount"])),
            "MAX_TOTAL": ldvp["max_total"], "MAX_DAILY": ldvp["max_daily"],
        },
        reports=False, app_env=config.env,
    )
    print(f"STEP [LANDING] {FLOWS} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Landing flows did not pass: {summary['passed']} passed / {summary['failed']} failed - "
        f"see {summary['build_url']}")


def _count(text):
    # Counts and amounts render as "2", "200", "200.00" or "-" for none.
    digits = "".join(ch for ch in text.split(".")[0] if ch.isdigit())
    return int(digits) if digits else 0
