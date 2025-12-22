import allure
import pytest
from web_pages.base_web_page import BaseWebPage
from web_pages.cchq_home_web_page import HomePage
from web_pages.connect_home_web_page import ConnectHomePage
from web_pages.cchq_login_web_page import LoginPage
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage


@pytest.mark.web
def test_olp_1_2_3_setup_budget_in_connect(web_driver, test_data, config):
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Add Opportunity in Connect Page with required fields"):
        connect_opp_page.create_opportunity_in_connect_page(olp1_data)

    with allure.step("Add Payment Unit in Connect Page"):
        connect_opp_page.create_payment_unit_in_connect_page(olp2_data)

    with allure.step("Setup Budget for opportunity in Connect Page"):
        connect_opp_page.setup_budget_in_connect_page(olp3_data)
