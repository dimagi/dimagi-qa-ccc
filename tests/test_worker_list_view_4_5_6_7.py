import time

import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@pytest.mark.web
def test_worker_list_view_1_2_3_verify_count_breakdown_of_opportunity_in_connect(web_driver, test_data, config):
    worker_list_view_4_5_6_7_data = test_data.get("WORKER_LIST_VIEW_4_5_6_7")

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
        connect_opp_page.click_link_by_text(worker_list_view_4_5_6_7_data["opportunity_name"])
        opp_dashboard_page.click_dashboard_card_in_opportunity(worker_list_view_4_5_6_7_data["card_title"], worker_list_view_4_5_6_7_data["card_subtitle"])
        opp_dashboard_page.verify_text_in_url(worker_list_view_4_5_6_7_data["url_text"])

    with allure.step("Navigate and verify Connect Workers Deliver tab details in Opportunity"):
        connect_workers_page.click_tab_by_name(worker_list_view_4_5_6_7_data["tab_name"])
        connect_workers_page.verify_table_headers_present(worker_list_view_4_5_6_7_data["headers_list"])

    # Worker List View_4
    with allure.step("Verify Delivered column count breakdown in table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(worker_list_view_4_5_6_7_data["item_delivered_params"])

    # Worker List View_5
    with allure.step("Verify Pending column count breakdown in table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(worker_list_view_4_5_6_7_data["item_pending_params"])

    # Worker List View_6
    with allure.step("Verify Approved column count breakdown in table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(worker_list_view_4_5_6_7_data["item_approved_params"])

    # Worker List View_7
    with allure.step("Verify Rejected column count breakdown in table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(worker_list_view_4_5_6_7_data["item_rejected_params"])