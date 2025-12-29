import allure
import pytest

from pages.mobile_pages.delivery_app_page import DeliveryAppPage
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
@allure.story("Delivery App related validations")
@allure.tag("CONNECT_9", "CONNECT_10")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_9 : Verify user can view the opportunity details and claim the job after completing the learning
  - CONNECT_10 : Verify on updating a visit status from web, the status of the visit gets updated on the mobile
  """)

@pytest.mark.mobile
@pytest.mark.web
def test_opportunity_details(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_5")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = HomePage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    learn = LearnAppPage(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)


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

    with allure.step("Submit the form on the Delivery App"):
        delivery.submit_form("Registration Form")

    with allure.step("Verify Payment Unit Info and Visits details"):
        delivery.verify_payment_info()

    with allure.step("Submit the form on the Delivery App without GPS location"):
        delivery.submit_form("Registration Form", record_loc=False)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()