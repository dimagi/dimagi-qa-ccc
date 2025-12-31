import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage
from pages.web_pages.connect_worker_visits_web_page import WorkerVisitsPage

@allure.feature("Worker Visit Verification Page")
@allure.story("Verify all tabs displaying information in Worker Visits page of opportunity")
@allure.tag("Worker_Visit_Verification_Page_4", "Worker_Visit_Verification_Page_5", "Worker_Visit_Verification_Page_6", "Worker_Visit_Verification_Page_7")
@allure.description("""
    This automated test consolidates multiple manual test cases

    Covered manual test cases:
        - Worker_Visit_Verification_Page_4 : Confirm user sees all the pending reviews that require a PM review under 'Pending NM Review' tab 
        - Worker_Visit_Verification_Page_5 : Confirm user sees all the approved visits by the PM for the worker under 'Approved' tab 
        - Worker_Visit_Verification_Page_6 : Confirm user sees all the rejected visits by the PM for the worker under 'Rejected' tab 
        - Worker_Visit_Verification_Page_7 : Confirm user sees all the visits from the worker under 'All' tab
  """)

@pytest.mark.web
def test_worker_visit_verification_page_4_5_6_7_verify_tabs_in_worker_visits_of_opportunity(web_driver, test_data, config):
    worker_visit_4_5_6_7_data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_4_5_6_7")

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

    with allure.step("Navigate and verify Connect Workers Deliver tab details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(worker_visit_4_5_6_7_data["opportunity_name"])
        connect_workers_page.verify_deliver_table_headers_present()

    with allure.step("Verify Worker Visits page and tab details in Opportunity"):
        connect_workers_page.navigate_to_worker_visits(worker_visit_4_5_6_7_data["worker_name"])
        worker_visits_page.verify_worker_visits_tabs_present()

    # Worker Visit Verification Page_4
    with allure.step("Verify Pending NM Review tab in Worker Visits page"):
        worker_visits_page.click_tab_by_name("Pending NM Review")
        worker_visits_page.verify_worker_visits_table_headers_present(pending=True)

    # Worker Visit Verification Page_5
    with allure.step("Verify Approved tab in Worker Visits page"):
        worker_visits_page.click_tab_by_name("Approved")
        worker_visits_page.verify_worker_visits_table_headers_present()

    # Worker Visit Verification Page_6
    with allure.step("Verify Rejected tab in Worker Visits page"):
        worker_visits_page.click_tab_by_name("Rejected")
        worker_visits_page.verify_worker_visits_table_headers_present()

    # Worker Visit Verification Page_7
    with allure.step("Verify All tab in Worker Visits page"):
        worker_visits_page.click_tab_by_name("All")
        worker_visits_page.verify_worker_visits_table_headers_present()

