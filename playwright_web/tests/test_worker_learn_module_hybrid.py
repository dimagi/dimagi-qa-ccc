"""Learn_tab_02 (hybrid): "modules completed" progress updates as the worker
submits a Learn form on mobile. Modeled on test_e2e_relearn_lifecycle.py: web
drives setup/assertions, a Maestro flow (worker_learn_module.yaml) drives the
device.

Gated on two data files, and skips with a clean message until both are filled in:
  - web_test_data.yaml LEARN_TAB_02_HYBRID: the opportunity and worker (needs a
    worker whose learning is started but not complete)
  - mobile_workers.yaml MAESTRO_LEARN_TAB_02: the worker's sign-in and the Learn
    app's module/form/question names, copied from that opportunity's Learn app CCZ
The mobile flow is built from commcare-android source (see its own header
comment) but is NOT yet device-validated - expect to refine it against the first
real BrowserStack run, as every flow in this suite was.
"""

import re

import pytest

from flows.mobile_runner import env_by_flow, run_flows
from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_connect_workers
from pages.connect_workers_page import ConnectWorkersPage

FLOW = "worker_learn_module.yaml"
# Mobile env values that must be real before the device flow can run.
REQUIRED_MOBILE_KEYS = (
    "PHONE_NUMBER",
    "USERNAME",
    "BACKUP_CODE",
    "LEARN_MODULE",
    "LEARN_FORM",
    "LEARN_QUESTION",
)


def _is_tbd(value):
    return not value or str(value).startswith("TBD")


def _require_learn_data(test_data, config):
    """Web + mobile data for the test, or skip naming exactly what is still TBD."""
    data = test_data.get("LEARN_TAB_02_HYBRID") or {}
    worker = env_by_flow([FLOW], config.env)[FLOW]
    missing = [f"LEARN_TAB_02_HYBRID.{k}" for k in ("opportunity_name", "worker_name") if _is_tbd(data.get(k))]
    missing += [f"MAESTRO_LEARN_TAB_02.{k.lower()}" for k in REQUIRED_MOBILE_KEYS if _is_tbd(worker.get(k))]
    if missing:
        pytest.skip(
            "Learn_tab_02 hybrid data not seeded - needs a worker with learning started but not "
            f"complete. Still TBD: {', '.join(missing)}"
        )
    return data, worker


def _completed_count(cell_text):
    """The modules-completed number in a Learn tab cell (e.g. '2' or '2/5' -> 2)."""
    match = re.search(r"\d+", cell_text or "")
    assert match, f"No number in the Modules completed cell: {cell_text!r}"
    return int(match.group())


def test_learn_tab_02_modules_completed_updates_after_mobile_submission(page, config, settings, test_data):
    data, worker = _require_learn_data(test_data, config)
    opportunity_name = data["opportunity_name"]
    worker_name = data["worker_name"]
    column = data["modules_completed_column"]

    connect_page = login_to_connect(page, config, settings, PM_ORG)
    dashboard = open_connect_workers(connect_page, opportunity_name)
    workers = ConnectWorkersPage(connect_page)
    workers.click_tab_by_name("Learn")
    workers.verify_learn_table_headers_present()
    before = _completed_count(workers.learn_column_value(worker_name, column))

    device_env = {**worker, "OPPORTUNITY": opportunity_name, "LESSONS_COMPLETED_AFTER": str(before + 1)}
    summary = run_flows(flows=[FLOW], env=device_env, reports=False, app_env=config.env)
    assert summary["status"] == "SUCCESS", (
        f"Mobile flow {FLOW} did not pass: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )

    # The submission reaches Connect through CommCare HQ, which lags on staging
    # (same shape as the relearn-task flow), so poll rather than read once.
    after = before
    for _ in range(15):  # ~90s
        dashboard.goto_worker_tab("workers")  # re-enter to force a fresh load
        workers.click_tab_by_name("Learn")
        after = _completed_count(workers.learn_column_value(worker_name, column))
        if after > before:
            break
        connect_page.wait_for_timeout(6000)
    assert after > before, (
        f"'{column}' for '{worker_name}' did not increase after the mobile submission "
        f"(was {before}, now {after})"
    )
    print(f"STEP [Hybrid] {column} for {worker_name}: {before} -> {after}")
