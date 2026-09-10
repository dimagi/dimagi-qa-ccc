"""Shared entry for journey tests that need the designated static tasking
opportunity (enrolled workers). They skip until TASKING.static_* is filled in."""

import pytest

from flows.olp_setup import open_connect_as_org
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage

REQUIRED_KEYS = ["static_opp", "static_opp_id", "static_org", "static_worker", "static_task_type"]

# Keys whose value can differ per environment. The rest are shared.
ENV_SPECIFIC_KEYS = REQUIRED_KEYS + ["static_nm_org", "static_nm_org_name", "switch_enabled"]


def env_value(data, key, config):
    """Resolve a key that may differ between environments.

    Follows the convention OLP_1 already uses for domains and api keys: the
    unsuffixed key holds the **prod** value and `<key>_staging` the staging one.
    Falling back to the unsuffixed key means anything identical on both
    environments only has to be written once.
    """
    if config.env == "stage":
        staged = data.get(f"{key}_staging")
        if staged not in (None, ""):
            return staged
    return data.get(key)


def require_static_opp(test_data, config):
    """The TASKING block with env-specific keys resolved for the current environment.

    Returns a copy, so callers read `tasking["static_opp_id"]` as before and get the
    value for the environment under test - pointing a prod run at staging's
    opportunity would otherwise fail in a thoroughly confusing way.
    """
    tasking = dict(test_data.get("TASKING"))
    for key in ENV_SPECIFIC_KEYS:
        tasking[key] = env_value(tasking, key, config)
    missing = [key for key in REQUIRED_KEYS if not tasking.get(key)]
    if missing:
        pytest.skip(
            f"Static tasking opportunity not configured for env '{config.env}' (missing: "
            + ", ".join(missing)
            + ") - see Tasking_Workflow_Automation_Test_Plan.xlsx Prerequisites"
        )
    return tasking


HYBRID_REQUIRED_KEYS = ["org", "opp_id"]
# Only the opportunity and its task type differ between environments; anything
# identical on both is written once and env_value falls through to it. The mobile
# worker is deliberately absent - it lives in mobile_workers.yaml, resolved by the
# Maestro runner, so web and device cannot disagree about who signs in.
HYBRID_ENV_SPECIFIC_KEYS = ["org", "opp_id", "opportunity_name", "task_type"]


def require_hybrid_opp(test_data, config):
    """The TASKING_HYBRID block resolved for the current environment."""
    hybrid = dict(test_data.get("TASKING_HYBRID"))
    for key in HYBRID_ENV_SPECIFIC_KEYS:
        hybrid[key] = env_value(hybrid, key, config)
    missing = [key for key in HYBRID_REQUIRED_KEYS if not hybrid.get(key)]
    if missing:
        pytest.skip(
            f"Hybrid tasking opportunity not configured for env '{config.env}' "
            f"(missing: {', '.join(missing)}). It needs an opportunity with the re-learn task "
            "type configured and the mobile worker already delivering."
        )
    return hybrid


def login_to_connect(page, config, settings, organization):
    """CCHQ login + Connect OAuth + org selection (no app copies)."""
    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()
    return open_connect_as_org(page, config, organization=organization)
