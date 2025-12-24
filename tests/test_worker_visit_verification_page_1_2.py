import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage
from pages.web_pages.connect_worker_visits_web_page import WorkerVisitsPage


@pytest.mark.web
def test_worker_visit_verification_page_1_2_for_deliver_of_opportunity_in_connect(web_driver, test_data, config):
    worker_visit_1_2_data = test_data.get("WORKER_VISIT_VERIFICATION_PAGE_1_2")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        connect_opp_page.click_link_by_text(worker_visit_1_2_data["opportunity_name"])
        opp_dashboard_page.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        opp_dashboard_page.verify_text_in_url("workers")

    with allure.step("Navigate and verify Connect Workers Deliver tab, header details in Opportunity"):
        connect_workers_page.click_tab_by_name("Deliver")
        connect_workers_page.click_name_in_table(worker_visit_1_2_data["worker_name"])
        connect_workers_page.is_breadcrumb_item_present("Visits")
        worker_visits_page.verify_worker_visits_table_headers_present()

    # Worker Visit Verification Page_1
    with allure.step("Verify tabs, apply filter for individual and Approve in Worker Visits page"):
        worker_visits_page.verify_worker_visits_tabs_present()
        worker_visits_page.set_row_checkbox_from_list(["09 Dec, 2025 08:41", "test name", True])
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