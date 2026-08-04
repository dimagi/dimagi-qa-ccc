import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage


def test_task_permissions_journey(page, test_data, config, settings):
    """J4 - PM org admin gets manage controls; NM org member gets edit-only; config 404s.

    Covers TC-PRM-001/002/003 from the tasking test plan (permission split from
    commcare-connect PR #1381). Needs the static opportunity + NM org data.
    """
    tasking = require_static_opp(test_data, config)
    if not tasking.get("static_nm_org") or not tasking.get("static_nm_org_name"):
        pytest.skip("TASKING.static_nm_org / static_nm_org_name not configured")
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)
    connect_home = ConnectHomePage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    # TC-PRM-001: PM org admin sees full manage controls (one pending task for Edit column)
    tasks.goto_task_list(base_url, org, opp)
    tasks.create_task(task_type, worker, due_in_days=7)
    tasks.verify_success_message("Task created successfully")
    create_visible, delete_visible, checkboxes_visible = tasks.manage_controls_visible()
    assert create_visible and delete_visible and checkboxes_visible
    assert tasks.edit_buttons_visible()

    try:
        # TC-PRM-002: NM org member gets view + due-date edit only
        connect_home.select_organization_from_list(tasking["static_nm_org_name"])
        tasks.goto_task_list(base_url, tasking["static_nm_org"], opp)
        tasks.verify_page_loaded()
        create_visible, delete_visible, checkboxes_visible = tasks.manage_controls_visible()
        assert not create_visible and not delete_visible and not checkboxes_visible
        assert tasks.edit_buttons_visible(), "NM member should still get due-date Edit (PR #1381)"

        # TC-PRM-003: task type config 404s for the NM org
        connect_page.goto(f"{base_url}/a/{tasking['static_nm_org']}/opportunity/{opp}/task_types/")
        connect_page.wait_for_load_state("load")
        body = connect_page.inner_text("body")
        assert "not available" in body.lower() or "404" in body, f"Expected 404 page, got: {body[:200]}"
    finally:
        # cleanup: back to PM org, delete the created task
        connect_home.select_organization_from_list(PM_ORG)
        tasks.goto_task_list(base_url, org, opp)
        if tasks.row_exists(worker):
            tasks.delete_tasks_for_workers([worker])
