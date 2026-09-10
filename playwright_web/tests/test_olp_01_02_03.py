from flows.olp_setup import full_olp_setup
from flows.tasking_config import verify_task_type_creation


def test_olp_01_02_03_setup_budget_in_connect(page, test_data, config, settings):
    """OLP 01/02/03 - program handshake, opportunity, payment unit and budget.

    Also covers TC-TTC-002 (creating a task type from a task unit). A task-type
    slug is permanently consumed per deliver app, so the throwaway app copy this
    test already makes is the only place the create case can run every run without
    accumulating dead types on the long-lived tasking opportunity.
    """
    setup = full_olp_setup(page, config, settings, test_data)
    verify_task_type_creation(setup.connect_page, config, test_data, setup)
