import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage
from pages.web_pages.connect_worker_visits_web_page import WorkerVisitsPage

@allure.feature("Worker Visit Verification Page")
@allure.story("Verify tabs in Connect Workers page of opportunity dashboard")
@allure.tag("Worker_Visit_Verification_Page_3")
@allure.description("""
    Covered manual test cases:
        - Worker_Visit_Verification_Page_3 : Confirm user is able to suspend users from an opportunity 
  """)

@pytest.mark.web
def test_worker_visit_verification_page_3_verify_suspend_users_from_an_opportunity(web_driver, test_data, config):
    worker_visit_3_data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_3")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        opp_dashboard_page.navigate_to_connect_workers(worker_visit_3_data["opportunity_name"])

    with allure.step("Navigate and verify Connect Workers Visits and header details in Opportunity"):
        connect_workers_page.navigate_to_worker_visits(worker_visit_3_data["worker_name"])
        worker_visits_page.verify_worker_visits_table_headers_present()

    # Worker Visit Verification Page_3
    with allure.step("Verify Suspend user in Worker Visits page of Opportunity"):
        worker_visits_page.suspend_user_in_worker_visits(worker_visit_3_data["reason"])
        worker_visits_page.revoke_suspension_for_worker()