from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_task_types_page import ConnectTaskTypesPage
from pages.connect_workers_page import ConnectWorkersPage


def test_task_views_and_filters_journey(page, test_data, config, settings):
    """J3 - creates its own task, checks every view that renders it, deletes it.

    Covers TC-TLV-002(two filters)/003/004/005(basic)/006 from the tasking test
    plan. TC-TLV-005 Name/Description assertions are deferred pending the
    TC-IMP-002 template bug verification. Needs the static opportunity.
    """
    tasking = require_static_opp(test_data, config)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)
    workers = ConnectWorkersPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()
    tasks.create_task(task_type, worker, due_in_days=7)
    tasks.verify_success_message("Task created successfully")

    try:
        # TC-TLV-002: two representative filters (all share one filterset code path)
        tasks.apply_status_filter("To Do")
        badges = tasks.visible_status_badges()
        assert badges and all(b == "To Do" for b in badges), f"Non-To-Do rows after filter: {badges}"
        tasks.clear_filters()

        # TC-TLV-003: Workers page Tasks tab shows the grouped row
        workers.goto_workers_tasks_tab(base_url, org, opp)
        workers.verify_worker_has_task(worker, task_type)

        # TC-TLV-004/005 (basic): drill-down task list + details panel loads.
        # The page is per-worker and 404s without ?user=<ConnectUser.user_id>,
        # which the Tasks tab does not expose - hence the hop via the Delivery tab.
        user_id = workers.worker_user_id(base_url, org, opp, worker)
        workers.goto_worker_tasks_page(base_url, org, opp, user_id)
        details_text = workers.open_first_task_details()
        assert "Due" in details_text or "Status" in details_text

        # TC-TLV-006: dashboard tile (only when the waffle switch is confirmed on)
        if tasking.get("switch_enabled"):
            connect_page.goto(f"{base_url}/a/{org}/opportunity/{opp}/")
            connect_page.wait_for_load_state("load")
            connect_page.wait_for_timeout(3000)  # stats tile arrives via htmx
            assert task_types.is_tasks_tile_visible()
    finally:
        # cleanup so reruns start clean even on mid-test failure
        tasks.goto_task_list(base_url, org, opp)
        if tasks.row_exists(worker):
            tasks.delete_tasks_for_workers([worker])
