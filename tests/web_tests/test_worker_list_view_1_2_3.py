import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("Worker List View")
@allure.story("Verify tabs in Connect Workers page of opportunity dashboard")
@allure.tag("Worker_List_View_1", "Worker_List_View_2", "Worker_List_View_3")
@allure.description("""
    This automated test consolidates multiple manual test cases
    
    Covered manual test cases:
        - Worker_List_View_1 : Confirm user is redirected to the Worker's List page on clicking click on ‘Connect  Workers’
        - Worker_List_View_2 : Verify user can click on the Learn Tab, on the workers list page and see all the workers learn progress
        - Worker_List_View_3 : Verify user can access the Deliver tab, with all the delivery information for an opportunity 
  """)

@pytest.mark.web
def test_worker_list_view_1_2_3_verify_connect_workers_details_of_opportunity_in_connect(web_driver, test_data, config):
    worker_list_view_1_2_3_data = test_data.get("WORKER_LIST_VIEW_1_2_3")

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

    # Worker List View_1
    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        connect_opp_page.click_link_by_text(worker_list_view_1_2_3_data["opportunity_name"])
        opp_dashboard_page.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        opp_dashboard_page.verify_text_in_url("workers")
        connect_workers_page.verify_connect_workers_table_headers_present()

    # Worker List View_2
    with allure.step("Navigate and verify Connect Workers Learn tab details in Opportunity"):
        connect_workers_page.click_tab_by_name("Learn")
        connect_workers_page.verify_learn_table_headers_present()

    # Worker List View_3
    with allure.step("Navigate and verify Connect Workers Deliver tab details in Opportunity"):
        connect_workers_page.click_tab_by_name("Deliver")
        connect_workers_page.verify_deliver_table_headers_present()