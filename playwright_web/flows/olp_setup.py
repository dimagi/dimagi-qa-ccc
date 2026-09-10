"""Reusable OLP setup flows shared by the OLP regression test and the tasking
journey tests. Extracted from test_olp_01_02_03 - behavior must stay identical."""

from dataclasses import dataclass

from pages.cchq_application_page import CCHQApplicationPage
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_programs_page import ConnectProgramsPage

PM_ORG = "PM_Automation_01"
# Masters are picked by partial name match on the Applications tab. Renamed from
# "[08/12] ..." on 2026-08-03; the brackets are part of the real names, so a
# search string must not span them.
LEARN_APP_MASTER = "[Master] Learn App"
DELIVER_APP_MASTER = "[Master] Delivery App"


@dataclass
class OlpSetup:
    connect_page: object
    program_name: str
    opportunity_name: str
    learn_app_name: str
    delivery_app_name: str


def login_cchq_and_copy_master_apps(page, config, settings):
    """CCHQ login + copy Learn/Deliver masters, returns (learn_copy, deliver_copy)."""
    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_application_page = CCHQApplicationPage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()

    cchq_home_page.select_app_under_applications_tab(LEARN_APP_MASTER)
    learn_app_name = cchq_application_page.create_copy_of_learn_app()
    cchq_home_page.verify_app_present_under_applications_tab(learn_app_name)

    cchq_home_page.select_app_under_applications_tab(DELIVER_APP_MASTER)
    delivery_app_name = cchq_application_page.create_copy_of_delivery_app()
    cchq_home_page.verify_app_present_under_applications_tab(delivery_app_name)
    return learn_app_name, delivery_app_name


def open_connect_as_org(page, config, organization=PM_ORG):
    """Open Connect in a new tab, OAuth in via CCHQ, select the organization."""
    connect_page = LoginPage(page).navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list(organization)
    return connect_page


def create_program_with_nm_handshake(connect_page, olp1_data):
    """PM creates program and invites the NM org, NM applies, PM accepts."""
    connect_home_page = ConnectHomePage(connect_page)
    connect_programs_page = ConnectProgramsPage(connect_page)

    connect_home_page.click_programs_in_sidebar()
    program_name = connect_programs_page.create_program(olp1_data)
    connect_programs_page.invite_network_manager(program_name, olp1_data["network_manager"])

    connect_home_page.select_organization_from_list(olp1_data["network_manager"])
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.apply_to_program(program_name)

    connect_home_page.select_organization_from_list(PM_ORG)
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.accept_application(program_name, olp1_data["network_manager"])
    return program_name


def create_opportunity_with_budget(
    connect_page, config, test_data, program_name, learn_app_name, delivery_app_name, days=7
):
    """Create opportunity under the program, add payment unit, set budget.

    days sets the delivery window length; the default 7 gives the short-lived
    opportunity the regression tests expect. Pass something long (e.g. 365) for
    an opportunity that has to stay usable, since Connect refuses new invites
    and blocks delivery once an opportunity has ended.
    """
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")
    connect_programs_page = ConnectProgramsPage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)

    connect_programs_page.open_create_opportunity_form(program_name, olp1_data["network_manager"])
    env = "staging" if "staging" in config.get("cchq_url") else "prod"
    opportunity_name = connect_opp_page.create_opportunity_in_connect_page(
        olp1_data, learn_app_name, delivery_app_name, env, network_manager=olp1_data["network_manager_slug"]
    )
    connect_opp_page.create_payment_unit_in_connect_page(olp2_data, days=days)
    connect_opp_page.setup_budget_in_connect_page(olp3_data, days=days)
    return opportunity_name


def full_olp_setup(page, config, settings, test_data, days=7):
    """Complete OLP flow: apps copied, program handshake done, opportunity ready."""
    learn_app_name, delivery_app_name = login_cchq_and_copy_master_apps(page, config, settings)
    connect_page = open_connect_as_org(page, config)
    olp1_data = test_data.get("OLP_1")
    program_name = create_program_with_nm_handshake(connect_page, olp1_data)
    opportunity_name = create_opportunity_with_budget(
        connect_page, config, test_data, program_name, learn_app_name, delivery_app_name, days=days
    )
    return OlpSetup(connect_page, program_name, opportunity_name, learn_app_name, delivery_app_name)
