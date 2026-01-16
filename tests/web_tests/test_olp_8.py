import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage

@allure.feature("OLP")
@allure.story("Verify hamburger menu item Verification Flags in opportunity dashboard page")
@allure.tag("OLP_8")
@allure.description("""
  Covered manual test cases:
  - OLP_8 : Confirm user is taken to the verification flag on selecting Verification Flags option
  """)

@pytest.mark.web
def test_olp_8_verification_flags_of_opportunity_in_connect(web_driver, test_data, config):
    olp8_data = test_data.get("OLP_8")

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

    with allure.step("Navigate to Opportunity and open Verification Flags in Hamburger Menu"):
        connect_opp_page.click_opportunity_in_opportunity(olp8_data["opportunity_name"])
        opp_dashboard_page.select_hamburger_menu_item("Verification Flags")
        opp_dashboard_page.verify_text_in_url("verification_flags_config")
