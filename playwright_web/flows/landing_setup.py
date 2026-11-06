"""Fixture opportunities for the Connect landing-page suite.

Each fixture is an LDVP opportunity held in one state (plan:
test_plans/Connect_Landing_And_Delivery_Tabs_Test_Plan.xlsx, Prerequisites):

- New (F5): Worker A invited from web and never accepted.
- Learning (F6): Worker A accepted and did the learn modules, never the assessment.

They are made once per environment and recorded in web_test_data.yaml (LANDING).
"""

from datetime import date, timedelta

from flows.ldvp_setup import create_ldvp_opportunity, invite_and_wait


def fixture_days(test_data, config):
    """How long a fixture runs (LANDING.fixture_days): long enough to outlast many
    runs, and it must end inside the LDVP program (LANDING.program_end_date)."""
    landing = test_data.get("LANDING")
    suffix = "_staging" if config.env == "stage" else ""
    days = int(landing["fixture_days"])
    program_end = date.fromisoformat(landing[f"program_end_date{suffix}"])
    assert date.today() + timedelta(days=days) < program_end, (
        f"A {days}-day fixture would end after the LDVP program ({program_end}); lower "
        f"LANDING.fixture_days or extend the program")
    return days


def create_new_fixture(page, config, settings, test_data, full_number, phone_number):
    """F5: create an opportunity and invite Worker A; nothing on the device."""
    opp = create_ldvp_opportunity(page, config, settings, test_data, days=fixture_days(test_data, config))
    workers = invite_and_wait(opp, full_number, phone_number)
    status = workers.worker_status(phone_number)
    assert status == "Invite pending", f"New fixture invite reads {status!r}, expected 'Invite pending'"
    return opp, workers
