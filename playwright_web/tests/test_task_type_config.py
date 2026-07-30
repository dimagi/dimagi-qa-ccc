from flows.olp_setup import full_olp_setup
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_task_types_page import ConnectTaskTypesPage


def test_task_type_config_journey(page, test_data, config, settings):
    """J1 - TC-TTC-001..006, TC-TAS-005, TC-IMP-003(light) from the tasking test plan.

    Runs against a FRESH opportunity so the relearn task unit slug is always
    available (slugs are unique per app; the per-run app copy resets that).
    """
    tasking = test_data.get("TASKING")
    setup = full_olp_setup(page, config, settings, test_data)
    connect_page = setup.connect_page

    connect_home = ConnectHomePage(connect_page)
    opp_list = ConnectOpportunitiesPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)
    task_list = ConnectAssignedTasksPage(connect_page)

    # Land on the new opportunity's dashboard
    connect_home.click_organizations_in_sidebar()
    opp_list.click_opportunity_in_opportunity(setup.opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")

    # TC-IMP-003 (part A): no task types yet -> dashboard tile absent
    if tasking.get("switch_enabled"):
        assert not task_types.is_tasks_tile_visible(), "Tasks tile visible before any task type exists"

    org_slug, opp_id = task_types.opportunity_ids_from_current_url()
    base_url = config.get("connect_url")

    # TC-TTC-001: reach config page via the dashboard menu
    task_types.open_from_dashboard_menu()
    task_types.verify_page_loaded(expected_app_name=setup.delivery_app_name)
    task_types.verify_no_task_types_yet()

    # TC-TTC-002 + TC-TTC-003: create from the registered task unit, slug intact
    created_name = task_types.add_task_type(
        tasking["task_unit_name"], tasking["case_property"], expected_slug=tasking["task_unit_slug"]
    )
    assert created_name == tasking["task_unit_name"]
    task_types.verify_row_present(created_name)
    task_types.verify_row_shows_unit(created_name, tasking["task_unit_name"])

    # TC-TTC-004: used task unit no longer offered
    labels = task_types.available_task_unit_labels()
    assert tasking["task_unit_name"] not in labels, f"Used task unit still offered: {labels}"

    # TC-TTC-005: edit name/description
    edited_name = tasking["edited_type_name"]
    task_types.edit_task_type_name(created_name, edited_name, "Edited by automation")
    task_types.verify_row_present(edited_name)

    # Positive half of TC-TAS-005: active type IS offered in the Create Task modal
    task_list.goto_task_list(base_url, org_slug, opp_id)
    task_list.verify_page_loaded()
    assert edited_name in task_list.create_modal_task_type_labels()

    # TC-IMP-003 (part B): active type exists -> dashboard tile present
    if tasking.get("switch_enabled"):
        connect_page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/")
        connect_page.wait_for_load_state("load")
        connect_page.wait_for_timeout(3000)  # stats tile arrives via htmx
        assert task_types.is_tasks_tile_visible(), "Tasks tile missing with an active task type"

    # TC-TTC-006: archive - row stays listed with the archive date
    task_types.goto_task_types(base_url, org_slug, opp_id)
    task_types.archive_task_type(edited_name)
    task_types.verify_row_archived(edited_name)

    # Negative half of TC-TAS-005: archived type no longer offered
    task_list.goto_task_list(base_url, org_slug, opp_id)
    labels_after_archive = task_list.create_modal_task_type_labels()
    assert edited_name not in labels_after_archive, "Archived type still assignable"
