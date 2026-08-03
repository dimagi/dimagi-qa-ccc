import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_workers_page import ConnectWorkersPage


def test_assign_and_delete_task_from_worker_page(page, test_data, config, settings):
    """TC-TAS-008 - assign a task from the worker's own Tasks page, then delete it there.

    Uses **J1's sandbox task type**, not the live one: the live type is what J2, J3,
    J4 and the mobile chain assign, and a stray pending assignment on it would break
    them on the duplicate constraint. The sandbox type is otherwise only renamed and
    archived by J1, so borrowing it for one assignment is safe as long as this test
    deletes what it created - which is also the point of the test.

    Two things about this page are not like the opportunity-wide task list:
      - the Create Task modal has no worker picker. CreateTaskForm gets the worker's
        access, so it sets access.initial and swaps the field for a HiddenInput.
      - rows print the task type as "Name (slug)"
        (WorkerCompletedTaskTable.render_task_type), so they can be matched on the
        slug and survive J1 renaming the sandbox between Sandbox A and Sandbox B.
    """
    tasking = require_static_opp(test_data)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    workers = ConnectWorkersPage(connect_page)

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

    # ...and delete it from the same page, which is the other half of what this
    # case is for. Leaving it assigned would also block J1's next archive.
    workers.delete_worker_task_by_slug(sandbox_slug)
    assert not workers.worker_task_row_exists(sandbox_slug), (
        f"Task row for '({sandbox_slug})' still present after deleting it from the worker page"
    )
