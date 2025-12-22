import allure
import pytest
from web_pages.cchq_home_web_page import HomePage
from web_pages.connect_home_web_page import ConnectHomePage
from web_pages.cchq_login_web_page import LoginPage
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.web
def test_olp_8_verification_flags_of_opportunity_in_connect(web_driver, test_data, config):
    olp8_data = test_data.get("OLP_8")

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

    with allure.step("Navigate to Opportunity and verify Hamburger menu items"):
        connect_opp_page.click_link_by_text(olp8_data["opportunity_name"])
        opp_dashboard_page.click_hamburger_icon()
        opp_dashboard_page.select_hamburger_menu_item(olp8_data["hamburger_menu_item"])
