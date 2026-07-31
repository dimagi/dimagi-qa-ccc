"""One-off setup for the long-lived tasking opportunity.

Creates a program + opportunity with a year-long delivery window, configures the
re-learn task type on it and invites the mobile worker, then prints the values to
paste into TASKING_HYBRID. Not part of the suite: it only runs when explicitly
asked for, so CI never creates this data.

    SETUP_TASKING=1 python -m pytest tests/test_setup_tasking_opportunity.py -s

The worker still has to complete learning and the assessment on the device once
before tasking can be verified - progress lives on the worker+opportunity pair,
so it cannot be carried over from another opportunity.
"""

import os

import pytest

from flows.olp_setup import full_olp_setup
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_task_types_page import ConnectTaskTypesPage
from pages.connect_workers_page import ConnectWorkersPage

DELIVERY_WINDOW_DAYS = 365


def test_setup_tasking_opportunity(page, test_data, config, settings):
    if os.getenv("SETUP_TASKING") != "1":
        pytest.skip("One-off setup helper - run with SETUP_TASKING=1 to create the opportunity")

    tasking = test_data.get("TASKING")
    hybrid = test_data.get("TASKING_HYBRID")
    full_number = f"{hybrid['mobile_country_code']}{hybrid['mobile_phone_number']}"

    setup = full_olp_setup(page, config, settings, test_data, days=DELIVERY_WINDOW_DAYS)
    connect_page = setup.connect_page

    connect_home = ConnectHomePage(connect_page)
    opp_list = ConnectOpportunitiesPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)
    tasks = ConnectAssignedTasksPage(connect_page)
    workers = ConnectWorkersPage(connect_page)

    connect_home.click_organizations_in_sidebar()
    opp_list.click_opportunity_in_opportunity(setup.opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")
    org_slug, opp_id = task_types.opportunity_ids_from_current_url()
    base_url = config.get("connect_url")

    # Task type, left active - unlike J1 this must not be archived.
    task_types.open_from_dashboard_menu()
    task_types.verify_page_loaded(expected_app_name=setup.delivery_app_name)
    created_name = task_types.add_task_type(
        tasking["task_unit_name"], tasking["case_property"], expected_slug=tasking["task_unit_slug"]
    )
    task_types.verify_row_present(created_name)

    # The task type must be assignable before the worker is worth inviting.
    tasks.goto_task_list(base_url, org_slug, opp_id)
    tasks.verify_page_loaded()
    assert created_name in tasks.create_modal_task_type_labels(), (
        f"Task type '{created_name}' is not assignable on the new opportunity"
    )

    workers.invite_workers(base_url, org_slug, opp_id, [full_number])
    workers.wait_for_worker_in_list(base_url, org_slug, opp_id, hybrid["mobile_phone_number"])

    print("\n" + "=" * 72)
    print("TASKING OPPORTUNITY READY - paste into test_data TASKING_HYBRID:")
    print(f"  org:       {org_slug}")
    print(f"  opp_id:    {opp_id}")
    print(f"  task_type: {created_name}")
    print(f"  opportunity name: {setup.opportunity_name}")
    print(f"  deliver app:      {setup.delivery_app_name}")
    print(f"  invited worker:   {full_number}")
    print(f"  URL: {base_url}/a/{org_slug}/opportunity/{opp_id}/")
    print(f"  delivery window:  {DELIVERY_WINDOW_DAYS} days")
    print("=" * 72)
