import os

import pytest

from flows.landing_setup import create_new_fixture, fixture_days
from utils.helpers import poll_until

POLL_SECONDS = 30


# Builds one landing-suite fixture opportunity - run by hand when one is missing,
# never in CI. LANDING_FIXTURE picks which: "new" (F5, web only) or "learning"
# (F6, one device session). The delivering (F1) and ended (F3) fixtures are full
# LDVP runs: test_e2e_ldvp.py with LDVP_DAYS=300 or LDVP_DAYS=2.
@pytest.mark.on_demand
@pytest.mark.landing
def test_create_landing_fixture(page, test_data, config, settings):
    """Create a landing fixture and print the ids to record under LANDING."""
    from flows.mobile_runner import env_by_flow, run_flows

    kind = os.environ.get("LANDING_FIXTURE", "")
    assert kind in ("new", "learning"), f"Set LANDING_FIXTURE to new or learning, not {kind!r}"
    ldvp = test_data.get("LDVP")
    sync_timeout = int(ldvp["sync_timeout_seconds_staging" if config.env == "stage" else "sync_timeout_seconds"])

    worker = env_by_flow(["ldvp_learn.yaml"], config.env)["ldvp_learn.yaml"]
    phone, worker_name = worker["PHONE_NUMBER"], worker["USERNAME"]
    opp, workers = create_new_fixture(page, config, settings, test_data, f"{worker['COUNTRY_CODE']}{phone}", phone)
    print(f"STEP [LANDING] {kind} fixture {opp.opportunity_name!r} ({opp.opp_id}), {fixture_days(test_data, config)} days")

    if kind == "learning":
        # ldvp_learn.yaml accepts the invite and submits both learn modules; the
        # assessment is never taken, so the job stays in learning.
        summary = run_flows(flows=["ldvp_learn.yaml"], env={"OPPORTUNITY": opp.opportunity_name},
                            reports=False, app_env=config.env)
        print(f"STEP [LANDING] ['ldvp_learn.yaml'] -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", f"ldvp_learn.yaml did not pass - see {summary['build_url']}"

        def accepted():
            workers.goto_workers_page(opp.base_url, opp.org_slug, opp.opp_id)
            workers.verify_worker_status(phone, "Invite accepted")

        poll_until(accepted, sync_timeout, POLL_SECONDS, lambda: None)

    key = "new" if kind == "new" else "learning"
    suffix = "_staging" if config.env == "stage" else ""
    print(f"STEP [LANDING] Record in web_test_data.yaml LANDING: {key}_opportunity_id{suffix}: "
          f"\"{opp.opp_id}\" / {key}_opportunity_name{suffix}: \"{opp.opportunity_name}\" ({worker_name})")
