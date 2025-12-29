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
@allure.story("Learn App related validations")
@allure.tag("CONNECT_7", "CONNECT_8")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_7 : Verify user can start learning after downloading the learn app
  - CONNECT_8 : Verify user isn't allowed to download the app if they fail the assessment 
  """)
@pytest.mark.mobile
@pytest.mark.web
def test_opportunity_invite_and_details(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_4")

    # web driver and page initiation
    cchq_login_page = LoginPage(web_driver)
    connect_opp = ConnectOpportunitiesPage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

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


    with allure.step("Complete Learning module"):
        learn.complete_learn_survey("Learn 1")

    with allure.step("Verify In Progress Job Status"):
        learn.verify_job_status("IN_PROGRESS")

    with allure.step("Complete Learning module"):
        learn.complete_learn_survey("Learn 2")

    with allure.step("Verify Learn Completed Job Status"):
        learn.verify_job_status("COMPLETED")

    with allure.step("Fail the Assessment with less than min score"):
        learn.complete_assessment("10")

    # with allure.step("Verify Assessment Status on Connect portal"):

    with allure.step("Verify Job Status for Failed Assessment"):
        learn.verify_job_status("FAILED_ASSESSMENT")

    with allure.step("Pass the Assessment with more than min score"):
        learn.complete_assessment("90")

    with allure.step("Verify Job Status for Passed Assessment"):
        learn.verify_certificate_screen()

    # with allure.step("Verify Assessment Status on Connect portal"):
