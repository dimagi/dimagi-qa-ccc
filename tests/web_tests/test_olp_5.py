import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("OLP")
@allure.story("Verify Services Delivered section in opportunity dashboard page")
@allure.tag("OLP_5")
@allure.description("""
  Covered manual test cases:
  - OLP_5 : Verify user see the all the information related to the deliveries under Service Deliveries section  
  """)

@pytest.mark.web
def test_olp_5_services_delivered_of_opportunity_in_connect(web_driver, test_data, config):
    olp5_data = test_data.get("OLP_5")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate to Services Delivered section and verify table in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(olp5_data["opportunity_name"])
        connect_workers_page.verify_deliver_table_headers_present()
