import allure
import pytest

from pages.mobile_pages.delivery_app_page import DeliveryAppPage
from pages.mobile_pages.learn_app_page import LearnAppPage
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
@allure.tag("CONNECT_9", "CONNECT_10")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_9 : Verify user can view the opportunity details and claim the job after completing the learning
  - CONNECT_10 : Verify on updating a visit status from web, the status of the visit gets updated on the mobile
  """)

@pytest.mark.mobile
@pytest.mark.web
@pytest.mark.bugasura("TES23", "TES24")
def test_delivery_app_registrations_and_approval(web_driver, mobile_driver, config, test_data):
    data = test_data.get("TC_5")

    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)
    worker_visits_page = WorkerVisitsPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
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

    with allure.step("Open the opportunity from list"):
        home.open_app_from_goto_connect()
        opportunity.open_opportunity_from_list(data["opportunity_name"], "delivery")

    with allure.step("Submit the form on the Delivery App"):
        delivery.submit_form("Registration Form")

    with allure.step("Verify Payment Unit Info and Visits details"):
        delivery.verify_payment_info()

    with allure.step("Submit the form on the Delivery App without GPS location"):
        result = delivery.submit_form("Registration Form", record_loc=False)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Change the organization"):
        connect_home_page.select_organization_from_list(data["org_name"])

    with allure.step("Navigate to the Connect Workers details in Opportunity"):
        opp_dashboard_page.navigate_to_services_delivered(data["opportunity_name"])
        connect_workers_page.click_name_in_table(data["username"])

    with allure.step("Approve individual Worker Visit using entity name and ID"):
        worker_visits_page.approve_entity_from_visits_using_name_and_id(result["name"], result["id"])
