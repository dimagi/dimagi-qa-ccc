from pyexpat.errors import messages

import allure
import pytest

from pages.mobile_pages.app_notifications import AppNotifications
from pages.mobile_pages.delivery_app_page import DeliveryAppPage
from pages.mobile_pages.messaging_page import Message
from pages.mobile_pages.mobile_notifications import MobileNotifications
from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_worker_visits_web_page import WorkerVisitsPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@allure.feature("CONNECT")
@allure.story("Delivery App related validations")
@allure.tag("CONNECT_13", "CONNECT_19", "CONNECT_17")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_13 : Confirm user can see all the notifications received on the notification history screen 
  - CONNECT_19 : Verify on clicking the messaging option, user is taken channels list page
  - CONNECT_17 : Verify when a mobile user is suspended from an opportunity
  
  """)

@pytest.mark.mobile
@pytest.mark.web
def test_opportunity_details(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_7")

    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    app_notification = AppNotifications(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)
    message = Message(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number

    with allure.step("Open the app notifications screen"):
        home.nav_to_notifications()
        app_notification.verify_all_notifications()

    with allure.step("Navigate to Messaging option"):
        home.nav_to_messaging()
        message.verify_channel_list() #need to design

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        connect_home_page.select_organization_from_list(data["organization_name"])

    with allure.step("Navigate and verify Connect Workers details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(data["opportunity_name"])
        connect_workers_page.click_name_in_table(data["username"])

    with allure.step("Verify Suspend user in Worker Visits page of Opportunity"):
        worker_visits_page.suspend_user_in_worker_visits("Test Reason")

    with allure.step("Verify Suspend message on app home screen"):
        home.nav_to_opportunities()
        opportunity.open_opportunity_from_list(data["opportunity_name"], "delivery")
        delivery.verify_suspend_message()

    # with allure.step("Revoke Suspension of the user"):

