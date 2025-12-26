import allure
import pytest

from pages.mobile_pages.learn_app_page import LearnAppPage
from pages.mobile_pages.notifications import Notifications
from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage


@allure.feature("CONNECT")
@allure.story("Delivery App related validations")
@allure.tag("CONNECT_9")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_9 : Verify user can view the opportunity details and claim the job after completing the learning
  """)
@pytest.mark.mobile
def test_opportunity_details(mobile_driver, test_data):
    data = test_data.get("TC_5")

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    learn = LearnAppPage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number

    with allure.step("Open the learn app page"):
        home.open_learn_app(data["opportunity_name"])

    with allure.step("Verify Completed Opportunity details"):
        learn.verify_opportunity_details_screen()

    with allure.step("Download the Delivery App"):
        learn.download_delivery_app()