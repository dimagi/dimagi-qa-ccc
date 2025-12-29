import allure
import pytest
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.mobile
@pytest.mark.web
def test_connect_2_go_to_connect_and_refresh_opportunity_option(mobile_driver, web_driver, config, test_data):
    data = test_data.get("CONNECT_2")

    cchq_login_page = LoginPage(web_driver)
    connect_opp = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)

    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number


    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq_and_signin_connect(web_driver, config)

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        opp_dashboard_page.nav_to_add_worker(data["opportunity_name"])
        connect_opp.add_worker_in_opportunity(data["phone_number"])

    with allure.step("Verify Refresh Opportunity button shown"):
        home.verify_refresh_opportunity()

    with allure.step("Verify Go To Connect button shown"):
        home.verify_go_to_connect()


