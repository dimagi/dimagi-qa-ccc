import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("Worker List View")
@allure.story("Verify selected filters are applied on the delivery tab")
@allure.tag("Worker_List_View_8")
@allure.description("""
    Covered manual test cases:
        - Worker_List_View_8 : Verify selected filters are applied on the delivery tab
  """)

@pytest.mark.web
def test_worker_list_view_8_verify_last_active_filter_as_1_day_ago(web_driver, test_data, config):
    worker_list_view_8_data = test_data.get("WORKER_LIST_VIEW_8")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Navigate and verify Connect Workers Deliver details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(worker_list_view_8_data["opportunity_name"])
        connect_workers_page.verify_deliver_table_headers_present()

    # Worker List View_8
    with allure.step("Verify Last Active filter as 1 day ago in Deliver table"):
        connect_workers_page.clear_all_filters_deliver_table()
        connect_workers_page.apply_n_verify_last_active_filter_1_day_ago_deliver_table()
