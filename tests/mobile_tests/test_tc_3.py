import allure
import pytest

from pages.mobile_pages.learn_app_page import LearnAppPage
from pages.mobile_pages.notifications import Notifications
from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@allure.feature("CONNECT")
@allure.story("New Opportunity related validations")
@allure.tag("CONNECT_3", "CONNECT_5", "CONNECT_6")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_3 : Verify User receive opportunity invite push notification
  - CONNECT_5 : Verify opportunity list on the opportunity page
  - CONNECT_6 : Verify Learn Modules and download the Learn App
  """)
@pytest.mark.mobile
@pytest.mark.web
def test_opportunity_invite_and_details(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_3")

    # web driver and page initiation
    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    notifications = Notifications(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    learn = LearnAppPage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number

    with allure.step("Verify Opportunity List in Opportunity Dashboard"):
        home.nav_to_opportunities()
        pid.handle_fingerprint_auth()
        opportunity.verify_opportunity_list()

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        connect_home_page.select_organization_from_list(data["org_name"])
        opp_dashboard_page.navigate_to_connect_workers(data["opportunity_name"])
        connect_workers_page.invite_workers_to_opportunity(data["phone_number"])

    with allure.step("Verify push notification shown for the invite"):
        notifications.open_notifications()
        notifications.verify_opportunity_invite()
        notifications.click_opportunity_invite()

    with allure.step("Handle Fingerprint Authentication"):
        pid.handle_fingerprint_auth()

    with allure.step("Verify Opportunity Details"):
        opportunity.verify_job_card()
        opportunity.verify_delivery_details()
        opportunity.verify_learn_details()

    with allure.step("Download the Learn App"):
        opportunity.download_learn_app()


