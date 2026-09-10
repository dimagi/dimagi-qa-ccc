"""TC-TTC-002 - creating a task type from a registered task unit.

This lives in a flow rather than in the tasking journey test because a task-type
slug is permanently consumed per deliver app: unique on (app, slug), no delete in
the UI, and archiving does not release it. So the create case can only run
repeatably on an app copy that is going to be thrown away. test_olp_01_02_03
already builds exactly that every run, so the assertion rides along on its
opportunity instead of burning a slug on the long-lived tasking opportunity - or
creating a second opportunity just to have somewhere to spend one.
"""

from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_task_types_page import ConnectTaskTypesPage


def verify_task_type_creation(connect_page, config, test_data, setup):
    """Create a task type on the just-built opportunity and verify it landed.

    Covers TC-TTC-002, the before/after half of TC-TTC-004, and TC-IMP-003 (which
    needs an opportunity that starts with no task types at all).
    """
    tasking = test_data.get("TASKING")
    connect_home = ConnectHomePage(connect_page)
    opp_list = ConnectOpportunitiesPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)
    task_list = ConnectAssignedTasksPage(connect_page)

    connect_home.click_organizations_in_sidebar()
    opp_list.click_opportunity_in_opportunity(setup.opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")

    # TC-IMP-003 (part A): no task types yet -> dashboard tile absent
    if tasking.get("switch_enabled"):
        assert not task_types.is_tasks_tile_visible(), "Tasks tile visible before any task type exists"

    org_slug, opp_id = task_types.opportunity_ids_from_current_url()
    base_url = config.get("connect_url")

    # Reach the config page. The connected-app assertion only means something
    # here, where the test knows which copy it linked to the opportunity.
    task_types.open_from_dashboard_menu()
    task_types.verify_page_loaded(expected_app_name=setup.delivery_app_name)
    task_types.verify_no_task_types_yet()

    # TC-TTC-002: create from the live task unit, selected by option value since
    # that value is the slug the TaskType is saved with.
    created_name = task_types.add_task_type_by_unit_value(
        tasking["task_unit_slug"], tasking["case_property"]
    )
    assert created_name == tasking["task_unit_name"], (
        f"Name auto-filled as {created_name!r}, expected the task unit's name "
        f"{tasking['task_unit_name']!r}"
    )
    task_types.verify_row_present(created_name)
    task_types.verify_row_shows_unit(created_name, tasking["task_unit_name"])

    # TC-TTC-004, in its strongest form: the unit was offered a moment ago and is
    # not offered now that a type uses its slug.
    offered = task_types.available_task_unit_values()
    assert tasking["task_unit_slug"] not in offered, f"Used task unit still offered: {offered}"

    # TC-IMP-003 (part B): an active type exists -> dashboard tile present
    if tasking.get("switch_enabled"):
        connect_page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/")
        connect_page.wait_for_load_state("load")
        connect_page.wait_for_timeout(3000)  # stats tile arrives via htmx
        assert task_types.is_tasks_tile_visible(), "Tasks tile missing with an active task type"

    task_list.goto_task_list(base_url, org_slug, opp_id)
    task_list.verify_page_loaded()
    return created_name
