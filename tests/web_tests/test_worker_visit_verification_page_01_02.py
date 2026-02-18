import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage
from pages.web_pages.connect_worker_visits_web_page import WorkerVisitsPage

@allure.feature("Worker Visit Verification Page")
@allure.story("Verify tabs in Connect Workers page of opportunity dashboard")
@allure.tag("Worker_Visit_Verification_Page_1", "Worker_Visit_Verification_Page_2")
@allure.description("""
    This automated test consolidates multiple manual test cases

    Covered manual test cases:
        - Worker_Visit_Verification_Page_1 : Confirm user lands on the Worker Visit Verification Page when they select a worker from the workers list page 
        - Worker_Visit_Verification_Page_2 : User should be able to Approve or Reject visits from the Workers Visit Verification Page 
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES92", "TES93", "TES101")
def test_worker_visit_verification_page_01_02_for_deliver_of_opportunity_in_connect(web_driver, test_data, config, settings):
    worker_visit_1_2_data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_1_2")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        connect_home_page.select_organization_from_list("PM_Automation_01")


    with allure.step("Navigate and verify Connect Workers Deliver tab details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(worker_visit_1_2_data["opportunity_name"])
        connect_workers_page.verify_deliver_table_headers_present()

    with allure.step("Verify Worker Visits and tabs, header details in Opportunity"):
        connect_workers_page.navigate_to_worker_visits(worker_visit_1_2_data["worker_name"])
        worker_visits_page.verify_worker_visits_table_headers_present()

    # Worker Visit Verification Page_1
    with allure.step("Verify tabs, apply filter for individual and Approve in Worker Visits page"):
        worker_visits_page.verify_worker_visits_tabs_present()
        worker_visits_page.set_row_checkbox_from_list("True")
        # worker_visits_page.set_row_checkbox_from_list(["09 Dec, 2025 08:41", "test name", True])
        worker_visits_page.click_approve_all_btn()

    # Worker Visit Verification Page_2
    with allure.step("Verify tabs, apply filter for bulk and Approve All in Worker Visits page"):
        worker_visits_page.verify_worker_visits_tabs_present()
        worker_visits_page.set_select_all_checkbox_worker_visits(True)
        worker_visits_page.click_approve_all_btn()

    ################### Step to change organization - for reference not included in the test case
    # with allure.step("Change organization"):
    #     connect_home_page.select_organization_from_list("Automation_Test_01")
    ##################

    ################### Step to approve visit using entity name & id - for reference not included in the test case
    # with allure.step("Approve individual Worker Visit using entity name and ID"):
    #     worker_visits_page.approve_entity_from_visits_using_name_and_id("test name", "123")
    ##################

    ################## Step to verify overlimit flag present - for reference not included in the test case
    # with allure.step("Verify Over limit flag present for the entity in worker visits"):
    #     connect_home_page.select_organization_from_list("Automation_Test_01")
    #     opp_dashboard_page.navigate_to_services_delivered("opp_max_daily_visits_test_01")
    #     connect_workers_page.click_name_in_table("Automation User 12")
    #     worker_visits_page.verify_overlimit_flag_present_for_the_entity_in_visits("test user 6")
    #################