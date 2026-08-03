import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_workers_page import ConnectWorkersPage


def test_e2e_relearn_lifecycle(page, test_data, config, settings):
    """P2-A - assign on web, complete on a real device, verify on web.

    Web assigns the re-learn task, a Maestro flow on a BrowserStack device has
    the worker sync and submit the task form, then web polls the task list until
    the status flips from To Do to Complete.

    Covers TC-E2E-001; TC-E2E-005 (Connect's task-completion push reaching the
    device, which the flow waits on rather than guessing at a delay); TC-E2E-006
    (the in-app "Complete assigned tasks to continue delivering services."
    warning showing and then being replaced by the completion message, checked on
    both the delivery-progress card and the app home tile - asserted inside
    worker_relearn_task.yaml, which needs APK 2.63.4 or newer); TC-TAS-001; and -
    because a completed task only exists at the end of this chain - TC-TAS-009 and
    TC-TDL-003.

    Still to add: TC-E2E-002 (delivery visit auto-rejected with the "Pending Task"
    flag while a task is pending) and TC-E2E-003 (visit accepted once it is
    complete). Both need a delivery visit submitted from the device, and they have
    to land as a pair - 002 alone would still pass if delivery were blocked
    permanently. Best done as extra stages of this one device session rather than
    a second cold start.
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

    if not hybrid.get("mobile_backup_code"):
        pytest.skip("TASKING_HYBRID.mobile_backup_code is not set - the device cannot sign in without it")

    # The worker must be enrolled before a task can be assigned to them.
    workers.wait_for_worker_in_list(base_url, org, opp, hybrid["mobile_phone_number"])

    # --- WEB: assign the task ---
    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()

    # Being invited is not enough: the Create Task dropdown only offers workers
    # who accepted the invite on their device, so check before driving TomSelect
    # and fail with the reason instead of a timeout inside the widget.
    assignable = tasks.create_modal_worker_labels()
    if not any(worker_name in label for label in assignable):
        pytest.skip(
            f"Worker '{worker_name}' is not assignable yet - the opportunity invite has to be "
            f"accepted on the device first. Currently offered: {assignable or 'nobody'}"
        )
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
            # Connect builds this body from the task type's name
            # (send_task_completion_notification), so derive it from the same
            # value the task was assigned with rather than restating it.
            "COMPLETION_NOTIFICATION_BODY": f"You have completed the task '{task_type}'.",
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

    # --- WEB: what a completed task allows and forbids ---
    # These belong here rather than in J2: they need a genuinely completed task,
    # and in J2 they would depend on leftovers from a previous run and fail on a
    # clean environment. The rows are ordered newest first, so the completed task
    # just verified above is the one being read.

    # TC-TAS-009: no Edit control - assigned_task_edit_button.html renders it only
    # while status is "assigned".
    assert tasks.row_edit_button_count(worker_name) == 0, "Completed task row still offers Edit"

    # TC-TDL-003: the select checkbox is still rendered but disabled, so a
    # completed task cannot be picked for deletion.
    checkbox_states = tasks.row_checkbox_states(worker_name)
    assert checkbox_states, "Completed task row has no select checkbox at all"
    assert not any(checkbox_states), (
        f"Completed task row is still selectable for deletion: {checkbox_states}"
    )

    # Re-assignment is allowed once the previous task completed - the duplicate
    # constraint only applies while one is still assigned. This is the property
    # that makes the whole tasking suite re-runnable against a single worker, so
    # it is worth asserting rather than assuming.
    tasks.create_task(task_type, worker_name, due_in_days=7)
    tasks.verify_success_message("Task created successfully")
    tasks.verify_task_row(worker_name, task_type, status="To Do")
    print("STEP [Hybrid] Same task type re-assigned after completion")

    # Leave nothing pending: J2, J3 and J4 assign this same type to this same
    # worker and would hit the duplicate constraint on the next run. The completed
    # rows stay - they are not deletable, which is the point of TC-TDL-003.
    tasks.delete_tasks_for_workers([worker_name])
    assert tasks.status_badge(worker_name) != "To Do", (
        "A pending task was left behind - the next J2 run would fail on the duplicate constraint"
    )
