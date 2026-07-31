import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_workers_page import ConnectWorkersPage


def test_e2e_relearn_lifecycle(page, test_data, config, settings):
    """P2-A - TC-E2E-001: assign on web, complete on a real device, verify on web.

    Web assigns the re-learn task, a Maestro flow on a BrowserStack device has
    the worker sync and submit the task form, then web polls the task list until
    the status flips from To Do to Complete.

    Scope: TC-E2E-001 only. TC-E2E-002 (delivery visit auto-rejected with the
    "Pending Task" flag while a task is pending) and TC-E2E-003 (visit accepted
    once it is complete) both need a delivery visit submitted from the device,
    which this flow does not do yet; they are the natural next addition, ideally
    as stages of the LDVP journey where a delivery visit already happens.

    TC-E2E-006 (the in-app "Complete assigned tasks to continue delivering
    services." warning appearing and then clearing) is deliberately not asserted
    here: on commcare-android master isRelearnTaskPending() is still a stub that
    returns false, and the staging APK in app/ predates the feature entirely, so
    the warning can never render. Add those assertions to
    maestro_mobile/flows/worker_relearn_task.yaml once a build carrying
    CCCT-2294 is in place.
    """
    hybrid = test_data.get("TASKING_HYBRID")
    required = ["org", "opp_id"]
    missing = [key for key in required if not hybrid.get(key)]
    if missing:
        pytest.skip(
            "Hybrid tasking opportunity not configured in test_data TASKING_HYBRID "
            f"(missing: {', '.join(missing)}). It needs an opportunity with the "
            "re-learn task type configured and the mobile worker already delivering."
        )

    base_url = config.get("connect_url")
    org, opp = hybrid["org"], hybrid["opp_id"]
    task_type = hybrid["task_type"]
    worker_name = hybrid["mobile_username"]
    full_number = f"{hybrid['mobile_country_code']}{hybrid['mobile_phone_number']}"

    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)
    workers = ConnectWorkersPage(connect_page)

    # The worker must be enrolled before a task can be assigned to them.
    workers.wait_for_worker_in_list(base_url, org, opp, hybrid["mobile_phone_number"])

    # --- WEB: assign the task ---
    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()
    if tasks.row_exists(worker_name):
        # A leftover pending task would block re-assignment (unique constraint).
        tasks.delete_tasks_for_workers([worker_name])
    tasks.create_task(task_type, worker_name, due_in_days=7)
    tasks.verify_success_message("Task created successfully")
    tasks.verify_task_row(worker_name, task_type, status="To Do")

    # --- MOBILE: worker syncs and completes the task form on a real device ---
    from flows.mobile_runner import run_flows

    summary = run_flows(
        flows=[hybrid["flow"]],
        env={
            "COUNTRY_CODE": hybrid["mobile_country_code"],
            "PHONE_NUMBER": hybrid["mobile_phone_number"],
            "USERNAME": hybrid["mobile_username"],
            "BACKUP_CODE": hybrid["mobile_backup_code"],
            "OPPORTUNITY": hybrid.get("opportunity_name") or "",
        },
        reports=False,
    )
    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Mobile flow did not pass: {summary['passed']} passed / {summary['failed']} failed - "
        f"see {summary['build_url']}"
    )

    # --- WEB: the form receiver round trip is async, so poll ---
    tasks.goto_task_list(base_url, org, opp)
    tasks.wait_for_task_status(
        worker_name,
        status="Complete",
        timeout_seconds=int(hybrid.get("completion_timeout_seconds", 300)),
    )
    print(f"STEP [Hybrid] Task for {full_number} verified Complete on web")
