import allure
import pytest
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("Worker List View")
@allure.story("Verify count breakdown of Total row in Deliver tab of Connect Workers page")
@allure.tag("Worker_List_View_5")
@allure.description("""
    Covered manual test cases:
        - Worker_List_View_5 : Confirm user can see the breakdown of visits when they click
          on the total no of visits for the Total row at the bottom of the page
  """)

@pytest.mark.web
# @pytest.mark.bugasura("TES90")
def test_worker_list_view_05_verify_count_breakdown_for_total_of_opportunity(web_driver, test_data, config, settings):
    worker_list_view_5_data = test_data.get("WORKER_LIST_VIEW_5")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        if 'staging' in config.get("cchq_url"):
            connect_home_page.select_organization_from_list("PM_Automation_01")
        else:
            connect_home_page.select_organization_from_list("dg_connect")


    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(worker_list_view_5_data["opportunity_name"])
        connect_workers_page.verify_deliver_table_headers_present()

    # Worker List View_5
    with allure.step("Verify Total row Delivered column count breakdown in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(["Total", "Delivered"])

    with allure.step("Verify Total row Pending column count breakdown in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(["Total", "Pending"])

    with allure.step("Verify Total row Approved column count breakdown in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(["Total", "Approved"])

    with allure.step("Verify Total row Rejected column count breakdown in Deliver table"):
        connect_workers_page.click_and_verify_status_count_breakdown_for_item(["Total", "Rejected"])