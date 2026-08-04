from datetime import date

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage


def test_task_assignment_lifecycle_journey(page, test_data, config, settings):
    """J2 - assign -> verify -> duplicate blocked -> edit due date -> delete.

    Covers TC-TAS-001/002/004(positive)/006/007, TC-TLV-001, TC-TDL-001/002
    from the tasking test plan. Needs the designated static opportunity.
    """
    tasking = require_static_opp(test_data)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()

    # TC-TLV-001: structure + Task ID column removed (PR #1375)
    tasks.verify_columns()

    # A pending task left behind by an earlier failed run would block assignment
    # on the duplicate constraint, so clear one before taking the baseline. This
    # no-ops when only completed rows are present - their checkboxes are disabled.
    if tasks.row_exists(worker):
        tasks.delete_tasks_for_workers([worker])
    total_before = tasks.metric("Total Tasks")
    open_before = tasks.metric("Open Tasks")

    try:
        # TC-TAS-004 (positive): the enrolled worker is offered; TC-TAS-001: assign
        due = tasks.create_task(task_type, worker, due_in_days=7)
        tasks.verify_success_message("Task created successfully")
        tasks.verify_task_row(worker, task_type, due_date_iso=due, status="To Do")

        # TC-TAS-007: metric cards moved
        assert tasks.metric("Total Tasks") == total_before + 1
        assert tasks.metric("Open Tasks") == open_before + 1

        # TC-TAS-002: duplicate assignment blocked while the first is pending.
        # Rejected via a flashed error message on the reloaded list, not inline -
        # so also check the counts, which is what actually proves nothing was
        # created.
        error = tasks.attempt_duplicate_task(task_type, worker)
        assert "already assigned" in error.lower(), f"Unexpected duplicate error: {error!r}"
        assert tasks.metric("Total Tasks") == total_before + 1, "A duplicate task was created"
        assert tasks.metric("Open Tasks") == open_before + 1

        # TC-TAS-003: a past due date cannot be selected. The date picker greys out
        # earlier days because the input's min is today, and typing round the picker
        # does not help either - the field then fails the browser's own range check,
        # which blocks submission. So a past due date never reaches the server, and
        # asserting the widget is the right level for this case.
        min_attr, validity = tasks.check_past_due_date_cannot_be_selected(days_ago=3)
        assert min_attr == date.today().isoformat(), (
            f"Due date input min is {min_attr!r}, expected today ({date.today().isoformat()}) - "
            "without it the picker would allow past dates"
        )
        assert validity["rangeUnderflow"] is True, f"A past date was accepted by the field: {validity}"
        assert validity["valid"] is False, f"A past date left the field valid: {validity}"

        # TC-TAS-006: edit due date with a reason
        tasks.edit_due_date(worker, due_in_days=14, reason="Automation reschedule")
        tasks.verify_success_message("Task updated successfully")

        # TC-TDL-001: single delete. Bulk delete (TC-TDL-002) is deliberately not
        # covered - it needs two assignable types or two enrolled workers purely to
        # tick the "2 task(s)" path, which is more standing test data than this
        # workflow warrants.
        tasks.delete_tasks_for_workers([worker])
        assert tasks.metric("Total Tasks") == total_before, (
            "Totals did not return to baseline after delete"
        )
        assert tasks.metric("Open Tasks") == open_before
        assert tasks.status_badge(worker) != "To Do", (
            f"Pending task for '{worker}' still present after delete"
        )
    finally:
        # Leave nothing pending even on a mid-test failure: J3, J4 and the mobile
        # chain assign this same type to this same worker.
        tasks.goto_task_list(base_url, org, opp)
        if tasks.status_badge(worker) == "To Do":
            tasks.delete_tasks_for_workers([worker])
