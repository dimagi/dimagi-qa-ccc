import allure
import pytest
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
def test_invite_worker_to_opportunity_connect(web_driver, test_data, config):
    data = test_data.get("Invite_Workers")

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

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        opp_dashboard_page.nav_to_add_worker(data["opportunity_name"])
        opp_dashboard_page.enter_users_and_submit_in_opportunity(data["numbers_list"])

    with allure.step("Verify Invited Workers in the Opportunity Page"):
        opp_dashboard_page.click_dashboard_card_in_opportunity(data["card_title"], data["card_subtitle"])
        connect_opp_page.verify_numbers_in_connect_workers_table(data["numbers_list"])
        opp_dashboard_page.nav_to_add_worker("Demo Opportunity")
        connect_opp_page.add_worker_in_opportunity(["+919999999999", "+918888888888", "+917777777777"])

    with allure.step("Verify Invited Workers in the Opportunity Page"):
        opp_dashboard_page.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        connect_opp_page.verify_numbers_in_connect_workers_table(["+919999999999", "+918888888888", "+917777777777"])
