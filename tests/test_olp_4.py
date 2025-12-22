import allure
import pytest
from pygments.lexers import data
from web_pages.base_web_page import BaseWebPage
from web_pages.cchq_home_web_page import HomePage
from web_pages.connect_home_web_page import ConnectHomePage
from web_pages.cchq_login_web_page import LoginPage
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.web
def test_olp_4_verify_opportunity_details_in_dashboard(web_driver, test_data, config):
    olp4_data = test_data.get("OLP_4")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate to Opportunity Dashboard and verify all fields present"):
        connect_opp_page.click_link_by_text(olp4_data["opportunity_name"])
        opp_dashboard_page.navigate_to_opportunity_and_verify_all_fields_present_in_connect(olp4_data)
