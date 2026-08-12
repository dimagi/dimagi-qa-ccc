import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_task_types_page import ConnectTaskTypesPage
from pages.connect_workers_page import ConnectWorkersPage


def test_assign_and_delete_task_from_worker_page(page, test_data, config, settings):
    """TC-TAS-008 - assign a task from the worker's own Tasks page, then delete it there.

    Also checks the task shows up on the opportunity-wide Task List, reached the way
    a PM reaches it: by clicking the "Tasks Assigned to Connect Workers" card on the
    opportunity dashboard. Every other test navigates there by URL, so the card is
    otherwise never exercised.

    Uses **J1's sandbox task type**, not the live one: the live type is what J2, J3,
    J4 and the mobile chain assign, and a stray pending assignment on it would break
    them on the duplicate constraint. The sandbox type is otherwise only renamed and
    archived by J1, so borrowing it for one assignment is safe as long as this test
    deletes what it created - which is also the point of the test.

    Two things about the worker page are not like the opportunity-wide task list:
      - the Create Task modal has no worker picker. CreateTaskForm gets the worker's
        access, so it sets access.initial and swaps the field for a HiddenInput.
      - rows print the task type as "Name (slug)"
        (WorkerCompletedTaskTable.render_task_type), so they can be matched on the
        slug and survive J1 renaming the sandbox between Sandbox A and Sandbox B.
    """
    tasking = require_static_opp(test_data, config)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    workers = ConnectWorkersPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)
    task_list = ConnectAssignedTasksPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    sandbox_slug = tasking["sandbox_unit_slug"]
    sandbox_names = {tasking["sandbox_name_a"], tasking["sandbox_name_b"], tasking["sandbox_unit_name"]}

    user_id = workers.worker_user_id(base_url, org, opp, worker)
    workers.goto_worker_tasks_page(base_url, org, opp, user_id)

    # Clear a leftover from an interrupted run: the sandbox type can only be
    # assigned once at a time, so a stale row would make the create below fail.
    if workers.worker_task_row_exists(sandbox_slug):
        workers.delete_worker_task_by_slug(sandbox_slug)

    offered = workers.worker_page_task_type_labels()
    sandbox_label = next((label for label in offered if label in sandbox_names), None)
    if sandbox_label is None:
        pytest.skip(
            f"J1's sandbox task type is not assignable (offered: {offered or 'nothing'}). It is "
            "created on first J1 run and left unarchived - run test_task_type_config.py first."
        )

    workers.create_task_from_worker_page(sandbox_label, due_in_days=7)
    workers.verify_worker_task_row(sandbox_slug, status="To Do")

    # The other half of the plan's expected outcome: a type already assigned to this
    # worker drops out of their dropdown, because the view hands the worker's access
    # to CreateTaskForm, which excludes it.
    workers.goto_worker_tasks_page(base_url, org, opp, user_id)
    offered_after = workers.worker_page_task_type_labels()
    assert sandbox_label not in offered_after, (
        f"'{sandbox_label}' is assigned to {worker} but is still offered: {offered_after}"
    )

    # The same task must appear on the opportunity-wide Task List, reached via the
    # dashboard card rather than by URL.
    connect_page.goto(f"{base_url}/a/{org}/opportunity/{opp}/")
    connect_page.wait_for_load_state("load")
    connect_page.wait_for_timeout(3000)  # stats tiles arrive via htmx
    task_types.open_task_list_from_dashboard_tile()
    task_list.verify_page_loaded()
    rows = task_list.worker_row_texts(worker)
    assert any(sandbox_label in row for row in rows), (
        f"Task '{sandbox_label}' assigned from the worker page is missing from the Task List "
        f"reached via the dashboard card. Rows for '{worker}': {rows or 'none'}"
    )

    # ...and delete it from the worker page, which is the other half of what this
    # case is for. Leaving it assigned would also block J1's next archive.
    workers.goto_worker_tasks_page(base_url, org, opp, user_id)
    workers.delete_worker_task_by_slug(sandbox_slug)
    assert not workers.worker_task_row_exists(sandbox_slug), (
        f"Task row for '({sandbox_slug})' still present after deleting it from the worker page"
    )
