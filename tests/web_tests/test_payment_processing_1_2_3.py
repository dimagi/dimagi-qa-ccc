import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage

@allure.feature("Payment Processing")
@allure.story("Verify Payments Tab in workers list and rollback a payment")
@allure.tag("Payment Processing_1", "Payment Processing_2", "Payment Processing_3")
@allure.description("""
    This automated test consolidates multiple manual test cases

    Covered manual test cases:
        - Payment Processing_1 : Confirm user can see all the payment info under Payments tab on the Workers List page
        - Payment Processing_2 : User should be able to see the payment history by clicking the last paid date
        - Payment Processing_3 : Confirm user can rollback a payment made to the worker
  """)

@pytest.mark.web
def test_payment_processing_1_2_3_verify_payments_tab_rollback_payment_of_opportunity(web_driver, test_data, config):
    payment_processing_1_2_3_data = test_data.get("PAYMENT_PROCESSING_1_2_3")

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

    # Payment Processing_1
    with allure.step("Navigate and verify Payments Tab details in Opportunity"):
        opp_dashboard_page.navigate_to_payments_earned(payment_processing_1_2_3_data["opportunity_name"])
        connect_workers_page.verify_tab_is_active("Payments")
        connect_workers_page.verify_payments_table_headers_present()

    # Payment Processing_2
    with allure.step("Verify Last Paid column history breakdown of Payments table"):
        connect_workers_page.click_last_paid_date_n_verify_history(payment_processing_1_2_3_data["worker_name"])

    # Payment Processing_3
    with allure.step("Verify payment rollback in Last Paid column history breakdown of Payments table"):
        connect_workers_page.rollback_last_payment()
