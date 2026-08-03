from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_task_types_page import ConnectTaskTypesPage


def test_task_type_config_journey(page, test_data, config, settings):
    """J1 - TC-TTC-001/004/005/006 and TC-TAS-005 on the long-lived opportunity.

    Consumes nothing. A task-type slug is permanently taken per deliver app, so
    this test owns a single sandbox type, created once from the second task unit
    and thereafter only renamed, archived and unarchived. It must never touch the
    live "Relearn Task Unit" type - J2, J3, J4 and the hybrid test all assign it,
    and archiving it would break every one of them.

    Deliberately not here:
      TC-TTC-002 (create) runs in test_olp_01_02_03, on the app copy that test
        discards, which is the only place a slug can be spent for free.
      TC-TTC-003 (slug integrity) is dropped - the hybrid test proves the same
        contract more strongly, since a slug that stopped matching the HQ task
        unit id would make task completion impossible, which it asserts.

    Run this first in the tasking sequence: it ends by proving the sandbox type is
    assignable again, so a broken unarchive fails here instead of silently
    poisoning J2-J4.
    """
    tasking = require_static_opp(test_data)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    task_types = ConnectTaskTypesPage(connect_page)
    task_list = ConnectAssignedTasksPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    name_a, name_b = tasking["sandbox_name_a"], tasking["sandbox_name_b"]
    sandbox_slug = tasking["sandbox_unit_slug"]

    # TC-TTC-001: the config page opens from the opportunity dashboard's menu.
    connect_page.goto(f"{base_url}/a/{org}/opportunity/{opp}/")
    connect_page.wait_for_load_state("load")
    task_types.open_from_dashboard_menu()
    task_types.verify_page_loaded()

    # --- J1's own sandbox type: created once, then reused forever ---
    sandbox = task_types.find_existing_row([name_a, name_b])
    if sandbox is None:
        offered = task_types.available_task_unit_values()
        assert sandbox_slug in offered, (
            f"No sandbox task type named {name_a!r} or {name_b!r} exists, and task unit "
            f"{sandbox_slug!r} is no longer available (offered: {offered or 'nothing'}). Its "
            "slug has been spent on a type under some other name - rename that type back to "
            f"{name_a!r}, or register a fresh task unit in the deliver app for this test to own."
        )
        created = task_types.add_task_type_by_unit_value(sandbox_slug, tasking["case_property"])
        task_types.verify_row_present(created)
        task_types.verify_row_shows_unit(created, tasking["sandbox_unit_name"])
        task_types.edit_task_type_name(created, name_a, "J1 sandbox - safe to rename and archive")
        task_types.verify_row_present(name_a)
        sandbox = name_a

    # TC-TTC-004: both units are in use, so neither is offered. Archiving never
    # releases a slug, so this holds however the previous run left things.
    offered = task_types.available_task_unit_values()
    assert tasking["task_unit_slug"] not in offered, f"Live task unit still offered: {offered}"
    assert sandbox_slug not in offered, f"Sandbox task unit still offered: {offered}"

    # TC-TTC-005: rename. The two names are toggled rather than a fresh name being
    # invented, so the row is still findable next run without carrying any state
    # between runs - the slug, which would be the natural key, is never rendered.
    renamed = name_b if sandbox == name_a else name_a
    task_types.edit_task_type_name(sandbox, renamed, f"Edited by automation -> {renamed}")
    task_types.verify_row_present(renamed)
    assert not task_types.row_exists(sandbox), f"Old name {sandbox!r} still listed after the rename"

    # TC-TAS-005 (positive): an active type is offered in the Create Task modal.
    task_list.goto_task_list(base_url, org, opp)
    task_list.verify_page_loaded()
    assert renamed in task_list.create_modal_task_type_labels()

    # TC-TTC-006: archive - the row stays listed, with today's date filled in.
    task_types.goto_task_types(base_url, org, opp)
    task_types.archive_task_type(renamed)
    task_types.verify_row_archived(renamed)

    # TC-TAS-005 (negative): an archived type is no longer assignable.
    task_list.goto_task_list(base_url, org, opp)
    assert renamed not in task_list.create_modal_task_type_labels(), "Archived type still assignable"

    # Put it back, and prove it, before finishing.
    task_types.goto_task_types(base_url, org, opp)
    task_types.unarchive_task_type(renamed)
    task_types.verify_row_not_archived(renamed)
    task_list.goto_task_list(base_url, org, opp)
    assert renamed in task_list.create_modal_task_type_labels(), (
        f"Sandbox type {renamed!r} is not assignable again after unarchive - later tasking "
        "tests would run against an archived type"
    )
