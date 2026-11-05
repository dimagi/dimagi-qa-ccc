"""Fixture opportunities for the Connect landing-page suite.

Each fixture is an LDVP opportunity held in one state (plan:
test_plans/Connect_Landing_And_Delivery_Tabs_Test_Plan.xlsx, Prerequisites):

- New (F5): Worker A invited from web and never accepted.
- Learning (F6): Worker A accepted and did the learn modules, never the assessment.

They are made once per environment and recorded in web_test_data.yaml (LANDING).
New is also what the suite rebuilds itself when a run finds it accepted.
"""

from flows.ldvp_setup import create_ldvp_opportunity, invite_and_wait

# Fixtures have to outlast many runs, and an opportunity has to end inside its
# program: the LDVP program on both environments runs to about 2027-10-30.
FIXTURE_DAYS = 300


def create_new_fixture(page, config, settings, test_data, full_number, phone_number):
    """F5: create an opportunity and invite Worker A; nothing on the device."""
    opp = create_ldvp_opportunity(page, config, settings, test_data, days=FIXTURE_DAYS)
    workers = invite_and_wait(opp, full_number, phone_number)
    status = workers.worker_status(phone_number)
    assert status == "Invite pending", f"New fixture invite reads {status!r}, expected 'Invite pending'"
    return opp, workers
