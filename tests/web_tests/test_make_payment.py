import allure
import pytest
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@pytest.mark.web
def test_make_payment_for_worker_to_opportunity_connect(web_driver, test_data, config):
    data = test_data.get("Make_Payment")

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

    with allure.step("Make payment for worker in Opportunity of Connect Dashboard Page"):
        connect_home_page.select_organization_from_list(data["org_name"])
        opp_dashboard_page.navigate_to_payments_earned(data["opportunity_name"])
        ##### order of params - worker_name, country_code, phone_number, amount #####
        connect_workers_page.make_payment_with_date_for_worker(data["worker_name"],
                                                         data["country_code"],
                                                         data["phone_number"],
                                                        "100")
