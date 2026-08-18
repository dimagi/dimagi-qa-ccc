import time

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_hybrid_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_workers_page import ConnectWorkersPage


# Drives a real device via a BrowserStack Maestro build - kept out of the per-PR
# gate (run on-demand / nightly), per the migration notes in PR #23.
@pytest.mark.on_demand
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
    # Resolve per environment rather than reading TASKING_HYBRID raw: the unsuffixed
    # keys are prod, so a staging run reading them straight would drive the prod
    # opportunity id against connect-staging and find no worker there.
    hybrid = require_hybrid_opp(test_data, config)

    base_url = config.get("connect_url")
    org, opp = hybrid["org"], hybrid["opp_id"]
    task_type = hybrid["task_type"]

    # The worker comes from mobile_workers.yaml, the single source the Maestro suite
    # also resolves from, so the number is this environment's. It has to be: a
    # PersonalID number cannot hold a session on two environments at once, and with
    # both environments running on every push a shared number means the two device
    # sessions evict each other mid-flow.
    from flows.mobile_runner import env_by_flow

    worker = env_by_flow([hybrid["flow"]], config.env)[hybrid["flow"]]
    worker_name = worker["USERNAME"]
    full_number = f"{worker['COUNTRY_CODE']}{worker['PHONE_NUMBER']}"

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

    # The worker must be enrolled before a task can be assigned to them.
    workers.wait_for_worker_in_list(base_url, org, opp, worker["PHONE_NUMBER"])

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

    # --- MOBILE + WEB, in two device sessions ------------------------------------
    # Submissions reach Connect through CommCare HQ, and on staging that hop lags.
    # With the blocked visit and the re-learn form submitted in one session, the
    # completion could be processed first, and the blocked visit was then evaluated
    # with nothing pending and came back Approved (2026-08-13).
    #
    # Submitting them in the right order is not enough: Connect has to be *seen* to
    # have evaluated the blocked visit before the completion is submitted at all, and
    # only the web side can see that. run_flows blocks until the build finishes, so
    # that gate can only sit between two sessions - hence the split.
    from flows.mobile_runner import run_flows

    device_env = {
        # The runner resolves the worker for this environment itself; passing it back
        # keeps the values the web half asserted on and the values the device signs in
        # with provably the same.
        **worker,
        "OPPORTUNITY": hybrid.get("opportunity_name") or "",
        # Connect builds this body from the task type's name
        # (send_task_completion_notification), so derive it from the same value the
        # task was assigned with rather than restating it.
        "COMPLETION_NOTIFICATION_BODY": f"You have completed the task '{task_type}'.",
        # Unique per run so each visit is findable by entity name on web, and so a
        # re-run cannot match a previous run's rows.
        "VISIT_NAME_BLOCKED": blocked_visit_name,
        "VISIT_ID_BLOCKED": blocked_visit_id,
        "VISIT_NAME_ALLOWED": allowed_visit_name,
        "VISIT_ID_ALLOWED": allowed_visit_id,
    }

    def run_device_flow(flow):
        # Each build targets one Connect server, so the APK follows the env.
        summary = run_flows(flows=[flow], env=device_env, reports=False, app_env=config.env)
        print(f"STEP [Hybrid] {flow} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"Mobile flow {flow} did not pass: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )
        return summary

    # Session 1: submit the blocked visit and stop, with the task still pending.
    run_device_flow(hybrid["flow_blocked_visit"])

    # TC-E2E-002: submitted while the task was pending. The form receiver sets
    # status=rejected outright and adds the "pending_task" flag - it is not merely
    # left flagged for review. wait_for_visit only returns once the row exists, and
    # the status is written in the same transaction that creates it, so a row here is
    # proof Connect has evaluated this visit - which is exactly the gate the
    # completion below must not jump.
    user_id = workers.worker_user_id(base_url, org, opp, worker_name)
    workers.goto_worker_visits_page(base_url, org, opp, user_id)
    blocked_row = workers.wait_for_visit(blocked_visit_name)
    assert "reject" in blocked_row.lower(), (
        f"Visit '{blocked_visit_name}' was submitted with a task pending, so it should be "
        f"rejected. Row reads: {blocked_row!r}"
    )

    # Session 2: only now complete the task, then submit the allowed visit. That
    # second visit needs no gate of its own - the flow waits for Connect's
    # task-completion push, which is fired after the completion is committed.
    run_device_flow(hybrid["flow"])

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

    # --- WEB: the second delivery visit (TC-E2E-003) ---
    # The pair still has to hold together: TC-E2E-002 above would pass on its own
    # even if delivery were blocked permanently, which is the bug this guards against.
    workers.goto_worker_visits_page(base_url, org, opp, user_id)

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
