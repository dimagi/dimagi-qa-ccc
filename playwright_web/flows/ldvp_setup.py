"""Opportunity setup for the LDVP end-to-end test (CCCT-2670).

Builds a fresh opportunity per run - apps copied, program handshake, opportunity,
payment unit, budget - with the steps flows.olp_setup already uses, except that
the payment unit comes from the LDVP block (max 2 a day, 4 in total) instead of
OLP_2, so the daily limit is reachable in one device session.
"""

from dataclasses import dataclass

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from flows.olp_setup import (
    PM_ORG,
    create_program_with_nm_handshake,
    login_cchq_and_copy_master_apps,
    open_connect_as_org,
)
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage
from pages.connect_programs_page import ConnectProgramsPage
from pages.connect_workers_page import ConnectWorkersPage
from utils.helpers import parse_org_and_opp


CREATE_ATTEMPTS = 3


@dataclass
class LdvpOpp:
    connect_page: object
    org_slug: str
    opp_id: str
    opportunity_name: str
    base_url: str


def create_ldvp_opportunity(page, config, settings, test_data):
    ldvp = test_data.get("LDVP")
    olp1_data = test_data.get("OLP_1")
    payment_unit = {**test_data.get("OLP_2"), **{k: ldvp[k] for k in (
        "payment_unit_name", "amount", "description", "max_total", "max_daily")}}
    days = int(ldvp["days"])

    env = "staging" if "staging" in config.get("cchq_url") else "prod"

    learn_app_name, delivery_app_name = login_cchq_and_copy_master_apps(page, config, settings)
    connect_page = open_connect_as_org(page, config)

    # Reuse one long-lived program whose NM handshake is already done. The
    # handshake (create, invite NM, NM applies, PM accepts) is the slowest and
    # flakiest part of this setup on staging, and the program does not need to
    # be fresh - only the opportunity does. With none recorded for this
    # environment, make one and say so, so its name can be added to LDVP.
    program_name = ldvp.get("program_name_staging" if env == "staging" else "program_name")
    if program_name:
        ConnectHomePage(connect_page).click_programs_in_sidebar()
    else:
        # Starts today and outlasts the opportunity: an opportunity has to lie
        # within its program, and the LDVP opportunity starts today.
        program_name = create_program_with_nm_handshake(connect_page, olp1_data, start_offset_days=0,
                                                        days=max(365, days + 5))
        print(f"STEP [LDVP] Created program {program_name!r} - record it as LDVP.program_name"
              f"{'_staging' if env == 'staging' else ''} in web_test_data.yaml to reuse it")

    opportunities = ConnectOpportunitiesPage(connect_page)
    # Named "LDVP Opportunity_<time>" so LDVP runs stand out on prod.
    opp_data = {**olp1_data, "opportunity_name": ldvp["opportunity_name"]}
    org_url = f"{config.get('connect_url')}/a/{PM_ORG.lower()}"
    opportunity_name = None
    for attempt in range(1, CREATE_ATTEMPTS + 1):
        opportunities.opp_full_name = None
        try:
            ConnectProgramsPage(connect_page).open_create_opportunity_form(program_name, olp1_data["network_manager"])
            # fill_opportunity_form directly, not create_opportunity_in_connect_page:
            # that one re-submits once on its own, with no duplicate check.
            connect_page.wait_for_timeout(5000)
            opportunity_name = opportunities.fill_opportunity_form(
                opp_data, learn_app_name, delivery_app_name, env, network_manager=olp1_data["network_manager_slug"]
            )
            connect_page.wait_for_timeout(3000)
            break
        except PlaywrightTimeoutError:
            # Staging HQ is sometimes slow to fill the app dropdowns. The form
            # submits inside the call, so retry only if nothing was created - after
            # giving an in-flight submit time to land.
            if opportunities.opp_full_name:
                connect_page.wait_for_timeout(15000)
            if opportunities.opp_full_name and _opportunity_exists(connect_page, org_url, opportunities.opp_full_name):
                raise AssertionError(
                    f"Opportunity {opportunities.opp_full_name!r} was created but its setup timed out - finish "
                    f"or delete it on web; not retrying, which would create a second one") from None
            if attempt == CREATE_ATTEMPTS:
                raise
            print(f"STEP [LDVP] Opportunity form attempt {attempt} timed out; retrying")
            connect_page.goto(f"{org_url}/program/", wait_until="domcontentloaded", timeout=120000)
            connect_page.wait_for_load_state("networkidle", timeout=120000)
    # Starts today: the OLP default (two days out) leaves the job "not started
    # yet" on the device, and a visit made then earns nothing.
    opportunities.create_payment_unit_in_connect_page(payment_unit, days=days, start_offset_days=0)
    budget = {**test_data.get("OLP_3"), "total_budget_value": ldvp["total_budget_value"]}
    opportunities.setup_budget_in_connect_page(budget, days=days, start_offset_days=0)

    # The payment unit and budget pages leave no opportunity URL behind, so open
    # the opportunity from the list to read its ids, as tasking_config does.
    ConnectHomePage(connect_page).click_organizations_in_sidebar()
    opportunities.click_opportunity_in_opportunity(opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")
    org_slug, opp_id = parse_org_and_opp(connect_page.url)
    return LdvpOpp(connect_page, org_slug, opp_id, opportunity_name, config.get("connect_url"))


def _opportunity_exists(connect_page, org_url, name):
    connect_page.goto(f"{org_url}/opportunity/", wait_until="load", timeout=120000)
    return ConnectOpportunityListPage(connect_page).has_opportunity(name)


def invite_and_wait(opp, full_number, phone_number):
    """TC-INV-001: invite by full number, then wait for the async invite to list it."""
    workers = ConnectWorkersPage(opp.connect_page)
    workers.invite_workers(opp.base_url, opp.org_slug, opp.opp_id, [full_number])
    workers.wait_for_worker_in_list(opp.base_url, opp.org_slug, opp.opp_id, phone_number)
    return workers


def resume_ldvp_opportunity(page, config, settings, opp_id, opportunity_name):
    """An existing LDVP opportunity, for resuming a run at delivery: log in and
    point at it without creating anything."""
    from flows.tasking_static import login_to_connect

    connect_page = login_to_connect(page, config, settings, PM_ORG)
    return LdvpOpp(connect_page, PM_ORG.lower(), opp_id, opportunity_name, config.get("connect_url"))
