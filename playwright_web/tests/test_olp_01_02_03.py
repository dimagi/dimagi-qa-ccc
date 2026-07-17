from pages.cchq_application_page import CCHQApplicationPage
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_programs_page import ConnectProgramsPage


def test_olp_01_02_03_setup_budget_in_connect(page, test_data, config, settings):
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")

    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_application_page = CCHQApplicationPage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()

    cchq_home_page.select_app_under_applications_tab("[08/12] Learn App")
    learn_app_name = cchq_application_page.create_copy_of_learn_app()
    cchq_home_page.verify_app_present_under_applications_tab(learn_app_name)

    cchq_home_page.select_app_under_applications_tab("[08/12] Delivey App")
    delivery_app_name = cchq_application_page.create_copy_of_delivery_app()
    cchq_home_page.verify_app_present_under_applications_tab(delivery_app_name)

    connect_page = cchq_login_page.navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_programs_page = ConnectProgramsPage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)

    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list("PM_Automation_01")

    # Opportunities can no longer be created directly - a Program must exist with an
    # accepted Network Manager. Create a fresh program and run the full handshake:
    # PM creates program and invites the NM org, NM applies, PM accepts.
    connect_home_page.click_programs_in_sidebar()
    program_name = connect_programs_page.create_program(olp1_data)
    connect_programs_page.invite_network_manager(program_name, olp1_data["network_manager"])

    connect_home_page.select_organization_from_list(olp1_data["network_manager"])
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.apply_to_program(program_name)

    connect_home_page.select_organization_from_list("PM_Automation_01")
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.accept_application(program_name, olp1_data["network_manager"])

    connect_programs_page.open_create_opportunity_form(program_name, olp1_data["network_manager"])

    env = "staging" if "staging" in config.get("cchq_url") else "prod"
    connect_opp_page.create_opportunity_in_connect_page(
        olp1_data, learn_app_name, delivery_app_name, env, network_manager=olp1_data["network_manager_slug"]
    )
    connect_opp_page.create_payment_unit_in_connect_page(olp2_data)
    connect_opp_page.setup_budget_in_connect_page(olp3_data)
