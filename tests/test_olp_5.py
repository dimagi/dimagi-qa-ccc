import time

import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.web
def test_olp_5_services_delivered_of_opportunity_in_connect(web_driver, test_data, config):
    olp5_data = test_data.get("OLP_5")

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

    with allure.step("Navigate to Services Delivered section in Opportunity"):
        connect_opp_page.click_link_by_text(olp5_data["opportunity_name"])
        opp_dashboard_page.click_dashboard_card_in_opportunity(olp5_data["card_title"], olp5_data["card_subtitle"])
        opp_dashboard_page.verify_tab_is_active(olp5_data["tab_name"])
        opp_dashboard_page.verify_table_element_present()
