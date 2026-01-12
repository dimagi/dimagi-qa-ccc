import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage

@allure.feature("OLP")
@allure.story("Verify hamburger menu options in opportunity dashboard page")
@allure.tag("OLP_7")
@allure.description("""
  Covered manual test cases:
  - OLP_7 : Confirm user can click on the hamburger option on the opportunity dashboard page and see different options
  """)

@pytest.mark.web
def test_olp_7_verify_hamburger_menu_items_of_opportunity_in_connect(web_driver, test_data, config):
    olp7_data = test_data.get("OLP_7")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate to Opportunity and verify Hamburger menu items"):
        connect_opp_page.click_opportunity_in_opportunity(olp7_data["opportunity_name"])
        opp_dashboard_page.verify_hamburger_menu_items_present_in_opportunity()
