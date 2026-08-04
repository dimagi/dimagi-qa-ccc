import time

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

    Also covers **TC-E2E-002 and TC-E2E-003**: a Registration Form visit is
    submitted before the re-learn form (task pending -> rejected with the
    "pending_task" flag) and another after it completes (-> not rejected). They are
    asserted as a pair, since 002 alone would still pass if delivery were blocked
    permanently. Both ride this one device session; the plan puts 002 in a separate
    "P2-B e2e_visit_blocking" test, but a second flow means a second cold start for
    no extra coverage.

    TC-E2E-004 (an archived task type must not block visits) is deliberately NOT
    here. It cannot share a visit with TC-E2E-006: an archived-type task left
    outstanding keeps the in-app pending-task warning up, so "the warning clears"
    and "an archived type does not block" cannot both be observed in one session.
    Covering it needs its own device session, since archiving happens on web and a
    Maestro build cannot be paused midway. Deferred pending a team decision.
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

    # Unique numeric ids and entity names per run. The Registration Form needs a
    # unique numeric id, and unique names are what let the two visits be told apart
    # on web - and stop a re-run matching last run's rows. The names carry their case
    # id so the Visits tab reads as its own explanation of why each was submitted.
    stamp = str(int(time.time()))[-6:]
    blocked_visit_id, allowed_visit_id = f"{stamp}1", f"{stamp}2"
    blocked_visit_name = f"E2E002-Blocked-{stamp}"
    allowed_visit_name = f"E2E003-Unblocked-{stamp}"

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
            # Unique per run so each visit is findable by entity name on web, and
            # so a re-run cannot match a previous run's rows.
            "VISIT_NAME_BLOCKED": blocked_visit_name,
            "VISIT_ID_BLOCKED": blocked_visit_id,
            "VISIT_NAME_ALLOWED": allowed_visit_name,
            "VISIT_ID_ALLOWED": allowed_visit_id,
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

    # --- WEB: the two delivery visits (TC-E2E-002 / TC-E2E-003) ---
    # Checked on the Visits tab of the same worker page. They have to be asserted as
    # a pair: the rejected one alone would still pass if delivery were blocked
    # permanently, which is the bug this guards against.
    user_id = workers.worker_user_id(base_url, org, opp, worker_name)
    workers.goto_worker_visits_page(base_url, org, opp, user_id)

    # TC-E2E-002: submitted while the task was pending. The form receiver sets
    # status=rejected outright and adds the "pending_task" flag - it is not merely
    # left flagged for review.
    blocked_row = workers.wait_for_visit(blocked_visit_name)
    assert "reject" in blocked_row.lower(), (
        f"Visit '{blocked_visit_name}' was submitted with a task pending, so it should be "
        f"rejected. Row reads: {blocked_row!r}"
    )

    # TC-E2E-003: submitted after the task completed, so the flag is never added and
    # the visit is processed normally. On this opportunity that means **Approved**
    # (auto_approve_visits is on); Pending is also accepted here so that turning
    # auto-approve off does not fail a test about task blocking. Rejected is the
    # regression this guards against.
    allowed_row = workers.wait_for_visit(allowed_visit_name)
    assert "Rejected" not in allowed_row, (
        f"Visit '{allowed_visit_name}' was submitted with no blocking task outstanding, so it "
        f"should not be rejected. Row reads: {allowed_row!r}"
    )
    assert "Approved" in allowed_row or "Pending" in allowed_row, (
        f"Visit '{allowed_visit_name}' should have been processed normally; expected Approved "
        f"(or Pending if auto-approve is off). Row reads: {allowed_row!r}"
    )
    print(f"STEP [Hybrid] Blocked visit: {blocked_row!r}")
    print(f"STEP [Hybrid] Allowed visit: {allowed_row!r}")
