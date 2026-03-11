import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.cchq_application_web_page import CCHQApplicationPage

@allure.feature("OLP")
@allure.story("Add opportunity in Connect Page")
@allure.tag("OLP_1", "OLP_2", "OLP_3")
@allure.description("""
    This automated test consolidates multiple manual test cases

    Covered manual test cases:
        - OLP_1 : Verify user is able to create on opportunity
        - OLP_2 : Verify user is able to land on the payment unit page
        - OLP_3 : Verify user is able to land on the Budget page
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES76", "TES77", "TES78")
def test_olp_01_02_03_setup_budget_in_connect(web_driver, test_data, config, settings):
    add_opportunity(web_driver, test_data, config, settings)

def add_opportunity(web_driver, test_data, config, settings):
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_application_page = CCHQApplicationPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)

    with allure.step("Login to CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")

    with allure.step("Create a copy of Learn App in CommCare HQ"):
        cchq_home_page.select_app_under_applications_tab("[08/12] Learn App")
        learn_app_name = cchq_application_page.create_copy_of_learn_app()
        cchq_home_page.verify_app_present_under_applications_tab(learn_app_name)

    with allure.step("Create a copy of Delivery App in CommCare HQ"):
        cchq_home_page.select_app_under_applications_tab("[08/12] Delivey App")
        delivery_app_name = cchq_application_page.create_copy_of_delivery_app()
        cchq_home_page.verify_app_present_under_applications_tab(delivery_app_name)

    with allure.step("Navigate and SignIn to Connect with CommCare HQ"):
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        connect_home_page.select_organization_from_list("PM_Automation_01")

    with allure.step("Add Opportunity in Connect Page with required fields"):
        if 'staging' in config.get("cchq_url"):
            opp_name = connect_opp_page.create_opportunity_in_connect_page(olp1_data, learn_app_name, delivery_app_name,
                                                                           "staging"
                                                                           )
        else:
            opp_name = connect_opp_page.create_opportunity_in_connect_page(olp1_data, learn_app_name, delivery_app_name,
                                                                           "prod"
                                                                           )

    with allure.step("Add Payment Unit in Connect Page"):
        connect_opp_page.create_payment_unit_in_connect_page(olp2_data)

    with allure.step("Setup Budget for opportunity in Connect Page"):
        connect_opp_page.setup_budget_in_connect_page(olp3_data)

    return opp_name