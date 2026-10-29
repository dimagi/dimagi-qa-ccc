"""Opportunity setup for the LDVP end-to-end test (CCCT-2670).

Builds a fresh opportunity per run - apps copied, program handshake, opportunity,
payment unit, budget - with the steps flows.olp_setup already uses, except that
the payment unit comes from the LDVP block (max 2 a day, 4 in total) instead of
OLP_2, so the daily limit is reachable in one device session.
"""

from dataclasses import dataclass

from flows.olp_setup import (
    create_program_with_nm_handshake,
    login_cchq_and_copy_master_apps,
    open_connect_as_org,
)
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_programs_page import ConnectProgramsPage
from pages.connect_workers_page import ConnectWorkersPage
from utils.helpers import parse_org_and_opp


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

    learn_app_name, delivery_app_name = login_cchq_and_copy_master_apps(page, config, settings)
    connect_page = open_connect_as_org(page, config)
    program_name = create_program_with_nm_handshake(connect_page, olp1_data)

    opportunities = ConnectOpportunitiesPage(connect_page)
    ConnectProgramsPage(connect_page).open_create_opportunity_form(program_name, olp1_data["network_manager"])
    env = "staging" if "staging" in config.get("cchq_url") else "prod"
    opportunity_name = opportunities.create_opportunity_in_connect_page(
        olp1_data, learn_app_name, delivery_app_name, env, network_manager=olp1_data["network_manager_slug"]
    )
    opportunities.create_payment_unit_in_connect_page(payment_unit, days=days)
    opportunities.setup_budget_in_connect_page(test_data.get("OLP_3"), days=days)

    # The payment unit and budget pages leave no opportunity URL behind, so open
    # the opportunity from the list to read its ids, as tasking_config does.
    ConnectHomePage(connect_page).click_organizations_in_sidebar()
    opportunities.click_opportunity_in_opportunity(opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")
    org_slug, opp_id = parse_org_and_opp(connect_page.url)
    return LdvpOpp(connect_page, org_slug, opp_id, opportunity_name, config.get("connect_url"))


def invite_and_wait(opp, full_number, phone_number):
    """TC-INV-001: invite by full number, then wait for the async invite to list it."""
    workers = ConnectWorkersPage(opp.connect_page)
    workers.invite_workers(opp.base_url, opp.org_slug, opp.opp_id, [full_number])
    workers.wait_for_worker_in_list(opp.base_url, opp.org_slug, opp.opp_id, phone_number)
    return workers
