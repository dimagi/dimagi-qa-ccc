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
@allure.story("Messaging related validations")
@allure.tag("MESSAGING_1", "MESSAGING_2", "MESSAGING_3")
@allure.tag("MESSAGING_4", "MESSAGING_5", "MESSAGING_6")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - MESSAGING_1 : Confirm user sees the two new message options on HQ 
  - MESSAGING_2 : Confirm user is able to configure a conditional alert with new Connect Message 
  - MESSAGING_3 : Confirm user is able to configure a conditional alert with new Connect Survey
  - MESSAGING_4 : Confirm user sees the two new message options on HQ when configuring Broadcasts 
  - MESSAGING_5 : Confirm user is able to configure a broadcast message with new Connect Message option
  - MESSAGING_6 : Confirm user is able to configure a broadcast message with new Connect Survey option
  
  """)
@pytest.mark.mobile
@pytest.mark.web
def test_max_visit_allowed(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_9")

    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        connect_home_page.select_organization_from_list(data["org_name"])



