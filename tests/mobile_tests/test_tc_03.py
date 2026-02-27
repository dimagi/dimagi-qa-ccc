import allure
import pytest
from selenium import webdriver

from pages.mobile_pages.app_notifications import AppNotifications
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
from pages.web_pages.connect_workers_web_page import ConnectWorkersPage
from tests.web_tests.test_olp_01_02_03 import add_opportunity

opp_name = None
@pytest.fixture(scope="function")
# @pytest.fixture(scope="session")
def created_opportunity(web_driver,test_data, config, settings):
    # driver = webdriver.Chrome()
    # driver.maximize_window()
    # try:
    # opp = add_opportunity(web_driver, test_data, config, settings)
    # finally:
    #     driver.quit()
    # return opp
    try:
        opp = add_opportunity(web_driver, test_data, config, settings)
        return opp
    except Exception as e:
        try:
            web_driver.save_screenshot("created_opportunity_failure.png")
        except Exception:
            pass
        raise
@allure.feature("CONNECT")
@allure.story("New Opportunity related validations")
@allure.tag("CONNECT_3", "CONNECT_5", "CONNECT_14", "Notification_2", "Notification_4")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_3 : Verify User receive opportunity invite push notification
  - CONNECT_5 : Verify opportunity list on the opportunity page
  - CONNECT_14 : Verify on clicking the opportunities option from the side drawer takes you to the opportunity list page
  - Notification_2: Verify notifications icon is present on the opportunities list page
  - Notification_4: Verify user lands on opportunity's learn app upon clicking on the opportunity invite notification
  """)
@pytest.mark.mobile
@pytest.mark.web
@pytest.mark.dependency(name="tc_3")
# @pytest.mark.xfail
# @pytest.mark.bugasura("TES17", "TES19", "TES28", "TES107", "TES108")
def test_opportunity_invite_notifications_and_details(created_opportunity, web_driver, config, test_data, settings, mobile_driver):

    data = test_data.get("TC_3_to_4")
    global opp_name
    opp_name = created_opportunity

    # web driver and page initiation
    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    notifications = MobileNotifications(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    app_notifications = AppNotifications(mobile_driver)


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
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        connect_home_page.select_organization_from_list(data["org_name"])
        opp_dashboard_page.navigate_to_connect_workers(opp_name)
        # opp_dashboard_page.navigate_to_connect_workers(data["opportunity_name"])
        connect_workers_page.invite_workers_to_opportunity([data["country_code"]+data["phone_number"]])

    with allure.step("Verify push notification shown for the invite"):
        notifications.open_notifications()
        notifications.verify_opportunity_invite()
        notifications.click_opportunity_invite()

    with allure.step("Handle Fingerprint Authentication"):
        pid.handle_fingerprint_auth()

    with allure.step("Verify the Opportunity Notifications"):
        opportunity.open_opportunity_from_list(opp_name, "new opportunity")
        opportunity.click_notification()
        app_notifications.verify_all_notifications()

    with allure.step("Verify the Opportunity Details"):
        opportunity.verify_job_card()
        opportunity.verify_delivery_details()
        opportunity.verify_learn_details()



@allure.feature("CONNECT")
@allure.story("Learn App related validations")
@allure.tag("CONNECT_6", "CONNECT_7", "CONNECT_8")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_6 : Verify Learn Modules and download the Learn App
  - CONNECT_7 : Verify user can start learning after downloading the learn app
  - CONNECT_8 : Verify user isn't allowed to download the app if they fail the assessment
  """)
@pytest.mark.mobile
@pytest.mark.web
@pytest.mark.dependency(name="tc_4", depends=["tc_3"])
# @pytest.mark.xfail
# @pytest.mark.bugasura("TES20", "TES21", "TES22")
def test_learn_app_assessments_delivery_app(web_driver, config, test_data, settings, mobile_driver):
    data = test_data.get("TC_3_to_4")


    # web driver and page initiation
    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    learn = LearnAppPage(mobile_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number

    with allure.step("Open the learn app page"):
        home.open_app_from_goto_connect()
        opportunity.open_opportunity_from_list(opp_name, "new opportunity")

    with allure.step("Download the Learn App"):
        opportunity.download_learn_app()


    with allure.step("Complete Learning module"):
        learn.complete_learn_survey("Learn 1")

    with allure.step("Verify In Progress Job Status"):
        learn.sync_with_server()
        learn.verify_job_status("IN_PROGRESS")

    with allure.step("Complete Learning module"):
        learn.complete_learn_survey("Learn 2")

    with allure.step("Verify Learn Completed Job Status"):
        learn.sync_with_server()
        learn.verify_job_status("COMPLETED")

    with allure.step("Fail the Assessment with less than min score"):
        learn.complete_assessment("10")

    with allure.step("Verify Assessment status in learn table for worker"):
        connect_home_page.select_organization_from_list(data["org_name"])
        opp_dashboard_page.navigate_to_connect_workers(opp_name)
        connect_workers_page.click_tab_by_name("Learn")
        connect_workers_page.verify_worker_assessment_status(data["username"], "Failed")

    with allure.step("Verify Job Status for Failed Assessment"):
        learn.sync_with_server()
        learn.verify_job_status("FAILED_ASSESSMENT")

    with allure.step("Pass the Assessment with more than min score"):
        learn.complete_assessment("90")

    with allure.step("Verify Job Status for Passed Assessment"):
        learn.sync_with_server()
        learn.verify_certificate_screen()

    with allure.step("Verify Assessment status in learn table for worker"):
        opp_dashboard_page.navigate_to_connect_workers(opp_name)
        connect_workers_page.click_tab_by_name("Learn")
        connect_workers_page.verify_worker_assessment_status(data["username"], "Passed")

    with allure.step("Verify Completed Opportunity details"):
        learn.verify_opportunity_details_screen()

    with allure.step("Download the Delivery App"):
        learn.download_delivery_app()


@allure.feature("CONNECT")
@allure.story("Payment related validations")
@allure.tag("CONNECT_11", "CONNECT_12", "CONNECT_13", "Notification_3", "Notification_5")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - CONNECT_11 : Confirm when a payment is made to the user, the same is reflected on the mobile
  - CONNECT_12 : Verify that user can confirm the payment status from the mobile
  - CONNECT_13 : Confirm user can see all the notifications received on the notification history screen
  - Notification_3 : Confirm user can see all the notifications received on the notification history screen
  - Notification_5 : Verify user is redirected to payment screen upon clicking on the payment notification
  """)

@pytest.mark.mobile
@pytest.mark.web
@pytest.mark.dependency(name="tc_6", depends=["tc_3"])
@pytest.mark.skip(reason="https://dimagi.atlassian.net/browse/QA-8418")
# @pytest.mark.bugasura("TES25", "TES26", "TES27", "TES109", "TES110")
def test_payment_and_related_notifications(web_driver, config, test_data, settings, mobile_driver):
    data = test_data.get("TC_6")

    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    mobile_notifications = MobileNotifications(mobile_driver)
    app_notification = AppNotifications(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number

    with allure.step("Open the delivery app"):
        home.open_app_from_goto_connect()
        opportunity.open_opportunity_from_list(opp_name, "delivery")
        # opportunity.open_opportunity_from_list(data["opportunity_name"], "delivery")

    with allure.step("Navigate to view job status"):
        delivery.nav_to_view_job()

    with allure.step("Change the organization"):
        connect_home_page.select_organization_from_list(data["org_name"])

    with allure.step("Make payment for the worker in the opportunity of Connect Dashboard Page"):
        opp_dashboard_page.navigate_to_payments_earned(opp_name)
        # opp_dashboard_page.navigate_to_payments_earned(data["opportunity_name"])
        connect_workers_page.make_payment_with_date_for_worker(data["username"],
                                                         data["country_code"],
                                                         data["phone_number"],
                                                        "100")

    with allure.step("Verify push notification shown for the payment"):
        mobile_notifications.open_notifications()
        mobile_notifications.verify_payment_received()
        mobile_notifications.click_payment_received()

    with allure.step("Verify App notification shown for the payment"):
        delivery.nav_to_app_notification()
        app_notification.verify_payment_received()

    with allure.step("Verify Payment confirmation popup on View Job Status header"):
        delivery.verify_payment_popup()

    with allure.step("Deny confirm transferred payment on payment tab"):
        delivery.confirm_pay_on_payment_tab("No")

    with allure.step("Allow confirm transferred payment on payment tab"):
        delivery.confirm_pay_on_payment_tab("Yes")

    with allure.step("Verify transferred amount with payment rows"):
        delivery.verify_transfer_tile_on_payment_tab()
