import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("OLP")
@allure.story("Verify Payments Earned section in opportunity dashboard page")
@allure.tag("OLP_6")
@allure.description("""
  Covered manual test cases:
  - OLP_6 : Verify user see the all the information related to the deliveries under Payments Earned section  
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES81")
def test_olp_06_payments_earned_of_opportunity_in_connect(web_driver, test_data, config, settings):
    olp6_data = test_data.get("OLP_6")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate to Payments Earned section and verify table in Opportunity"):
        opp_dashboard_page.navigate_to_payments_earned(olp6_data["opportunity_name"])
        connect_workers_page.verify_tab_is_active("Payments")
        connect_workers_page.verify_payments_table_headers_present()
