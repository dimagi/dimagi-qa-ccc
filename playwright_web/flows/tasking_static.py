"""Shared entry for journey tests that need the designated static tasking
opportunity (enrolled workers). They skip until TASKING.static_* is filled in."""

import pytest

from flows.olp_setup import open_connect_as_org
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage

REQUIRED_KEYS = ["static_opp", "static_opp_id", "static_org", "static_worker", "static_task_type"]


def require_static_opp(test_data):
    tasking = test_data.get("TASKING")
    missing = [key for key in REQUIRED_KEYS if not tasking.get(key)]
    if missing:
        pytest.skip(
            "Static tasking opportunity not configured in test_data (missing: "
            + ", ".join(missing)
            + ") - see Tasking_Workflow_Automation_Test_Plan.xlsx Prerequisites"
        )
    return tasking


def login_to_connect(page, config, settings, organization):
    """CCHQ login + Connect OAuth + org selection (no app copies)."""
    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()
    return open_connect_as_org(page, config, organization=organization)
