import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("Worker List View")
@allure.story("Verify count breakdown of worker in Deliver tab of Connect Workers page")
@allure.tag("Worker_List_View_4")
@allure.description("""
    Covered manual test cases:
        - Worker_List_View_4 : Confirm user can see the breakdown of delivered/flagged visits when they click 
          on the no of visits under Delivered, Pending, Rejected and Approved columns
  """)

@pytest.mark.web
def test_worker_list_view_4_verify_count_breakdown_of_opportunity_in_connect(web_driver, test_data, config):
    worker_list_view_4_data = test_data.get("WORKER_LIST_VIEW_4")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    connect_opp_page = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        connect_opp_page.click_opportunity_in_opportunity(worker_list_view_4_data["opportunity_name"])
        opp_dashboard_page.click_dashboard_card_in_opportunity("Services Delivered", "Total")
        opp_dashboard_page.verify_text_in_url("workers/deliver")
        connect_workers_page.verify_deliver_table_headers_present()

    # Worker List View_4
    with allure.step("Verify Delivered column count breakdown for worker in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item([worker_list_view_4_data["worker_name"], "Delivered"])

    with allure.step("Verify Pending column count breakdown for worker in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item([worker_list_view_4_data["worker_name"], "Pending"])

    with allure.step("Verify Approved column count breakdown for worker in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item([worker_list_view_4_data["worker_name"], "Approved"])

    with allure.step("Verify Rejected column count breakdown for worker in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item([worker_list_view_4_data["worker_name"], "Rejected"])