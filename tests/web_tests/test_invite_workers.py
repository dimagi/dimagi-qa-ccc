import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@pytest.mark.web
def test_invite_worker_to_opportunity_connect(web_driver, test_data, config):
    data = test_data.get("Invite_Workers")

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

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        connect_home_page.select_organization_from_list(data["org_name"])
        opp_dashboard_page.navigate_to_connect_workers(data["opportunity_name"])
        connect_workers_page.verify_and_delete_if_numbers_present_in_invites(data["numbers_list"])
        connect_workers_page.invite_workers_to_opportunity(data["numbers_list"])

    with allure.step("Verify Invited Workers in the Opportunity Page"):
        opp_dashboard_page.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        connect_workers_page.verify_numbers_in_connect_workers_table(data["numbers_list"])

    ################### Step to verify learn table pass status 100% and green - for reference not included in the test case
    # with allure.step("Verify Assessment status in learn table for worker"):
    #     opp_dashboard_page.navigate_to_connect_workers("Test Opp 151201")
    #     connect_workers_page.click_tab_by_name("Learn")
    #     connect_workers_page.verify_worker_passed_with_100_in_learn_table("Automation User 10")
    ###################