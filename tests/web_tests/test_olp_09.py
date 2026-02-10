import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("OLP")
@allure.story("Verify hamburger menu item Add Workers in opportunity dashboard page")
@allure.tag("OLP_9")
@allure.description("""
  Covered manual test cases:
  - OLP_9 : Confirm user is redirected to Add Workers page when they click on the Add Workers option 
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES84")
def test_olp_09_ways_to_add_workers_opportunity_in_connect(web_driver, test_data, config, settings):
    olp9_data = test_data.get("OLP_9")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate to Invite Workers using Hamburger Menu of Opportunity"):
        connect_opp_page.click_opportunity_in_opportunity(olp9_data["opportunity_name"])
        opp_dashboard_page.select_hamburger_menu_item("Add Connect Workers")
        opp_dashboard_page.verify_text_in_url("user_invite")
        connect_workers_page.verify_invite_users_input_present()

    with allure.step("Navigate to Invite Workers to Opportunity in Connect Dashboard Page"):
        opp_dashboard_page.navigate_backward()
        opp_dashboard_page.navigate_to_connect_workers(olp9_data["opportunity_name"])
        connect_workers_page.nav_to_add_worker()
        opp_dashboard_page.verify_text_in_url("user_invite")
