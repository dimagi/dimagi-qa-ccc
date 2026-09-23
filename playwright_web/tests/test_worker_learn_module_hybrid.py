"""Learn_tab_02 (hybrid): "modules completed" progress updates as the worker
submits a Learn form on mobile. Per [[feedback_hybrid_mobile_in_scope]] this is
in scope, not a permanent skip - modeled on test_e2e_relearn_lifecycle.py (web
drives setup/assertions, a Maestro flow drives the device).

Gated on LEARN_TAB_02_HYBRID (test_data/web_test_data.yaml) - skips with a clean
message until Anshu seeds a worker whose learning is started but not complete,
and worker_learn_module.yaml's module/form-name placeholders are filled in from
that opportunity's Learn app CCZ. The mobile flow is built from commcare-android
source (see its own header comment) but is NOT yet device-validated - expect to
refine it against the first real BrowserStack run, as every flow in this suite
was.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers
from pages.connect_workers_page import ConnectWorkersPage


def _require_learn_data(test_data):
    data = test_data.get("LEARN_TAB_02_HYBRID")
    if not data or str(data.get("opportunity_name", "")).startswith("TBD") or str(data.get("worker_name", "")).startswith("TBD"):
        pytest.skip(
            "LEARN_TAB_02_HYBRID not seeded - needs a worker with learning started "
            "but not complete (see project_connect_workers_migration memory ask list)."
        )
    return data


def test_learn_tab_02_modules_completed_updates_after_mobile_submission(page, config, settings, test_data):
    data = _require_learn_data(test_data)
    opportunity_name = data["opportunity_name"]
    worker_name = data["worker_name"]

    connect_page = login_to_connect(page, config, settings, PM_ORG)
    dashboard = open_connect_workers(connect_page, opportunity_name)
    workers = ConnectWorkersPage(connect_page)
    workers.click_tab_by_name("Learn")
    workers.verify_learn_table_headers_present()
    before = workers.learn_column_value(worker_name, "Modules completed")

    from flows.mobile_runner import env_by_flow, run_flows

    flow_key = data.get("mobile_flow_key", "LEARN_TAB_02")
    worker = env_by_flow([flow_key], config.env)[flow_key]
    device_env = {**worker, "OPPORTUNITY": opportunity_name}

    summary = run_flows(flows=["worker_learn_module.yaml"], env=device_env, reports=False, app_env=config.env)
    assert summary["status"] == "SUCCESS", (
        f"Mobile flow worker_learn_module.yaml did not pass: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )

    # The submission reaches Connect through CommCare HQ, which lags on staging
    # (same shape as the relearn-task flow), so poll rather than read once.
    for _ in range(15):  # ~90s
        dashboard.goto_worker_tab("workers")  # re-enter to force a fresh load
        workers.click_tab_by_name("Learn")
        after = workers.learn_column_value(worker_name, "Modules completed")
        if after != before:
            break
        connect_page.wait_for_timeout(6000)
    assert after != before, (
        f"'Modules completed' for '{worker_name}' did not change after the mobile submission "
        f"(stayed at {before!r})"
    )
    print(f"STEP [Hybrid] Modules completed for {worker_name}: {before!r} -> {after!r}")
