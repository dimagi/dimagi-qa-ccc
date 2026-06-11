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
@pytest.mark.mobile
@pytest.mark.web
# @pytest.mark.skip(reason="https://dimagi.atlassian.net/browse/QA-8418")
# @pytest.mark.bugasura("TES25", "TES26", "TES27", "TES109", "TES110")
def test_06_payment_and_related_notifications(web_driver, config, test_data, settings, mobile_driver):
    # if opp_name is None:
    #     pytest.skip("Opportunity name missing")
    # print(opp_name)
    data = test_data.get("TC_6")

    cchq_login_page = LoginPage(web_driver)
    connect_home_page = ConnectHomePage(web_driver)
    opp_dashboard_page = OpportunityDashboardPage(web_driver)
    connect_workers_page = ConnectWorkersPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    notifications = MobileNotifications(mobile_driver)
    app_notification = AppNotifications(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)

    # with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
    #     cchq_login_page.valid_login_cchq(config, settings)
    #     cchq_login_page.navigate_to_connect_page(config)
    #     connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Change the organization"):
        if 'staging' in config.get("cchq_url"):
            connect_home_page.select_organization_from_list(data["org_name_staging"])
        else:
            connect_home_page.select_organization_from_list(data["org_name"])


    with allure.step("Sign in with existing demo user"):
        if 'staging' in config.get("cchq_url"):
            pid.signin_existing_user(data["country_code"],
                                     data["phone_number_staging"],
                                     data["username_staging"],
                                     data["backup_code_staging"])
        else:
            pid.signin_existing_user(data["country_code"],
                                     data["phone_number"],
                                     data["username"],
                                     data["backup_code"])# test number

    with allure.step("Open the delivery app"):
        home.open_app_from_goto_connect()
        #opportunity.open_opportunity_from_list(opp_name, "delivery")
        opportunity.open_opportunity_from_list(data["opportunity_name"], "Resume")

    with allure.step("Navigate to view job status"):
        delivery.nav_to_view_job()

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()

    with allure.step("Change the organization"):
        if 'staging' in config.get("cchq_url"):
            connect_home_page.select_organization_from_list(data["org_name_staging"])
        else:
            connect_home_page.select_organization_from_list(data["org_name"])

    with allure.step("Make payment for the worker in the opportunity of Connect Dashboard Page"):
        #opp_dashboard_page.navigate_to_payments_earned(opp_name)
        opp_dashboard_page.navigate_to_payments_earned(data["opportunity_name"])
        if 'staging' in config.get("cchq_url"):
            connect_workers_page.make_payment_with_date_for_worker(
                data["username_staging"],
                data["country_code"],
                data["phone_number_staging"]
            )
        else:
            connect_workers_page.make_payment_with_date_for_worker(
                data["username"],
                data["country_code"],
                data["phone_number"]
            )

    with allure.step("Verify push notification shown for the payment"):
        try:
            notifications.check_and_open_notification()
            notifications.close_notifications()
        except:
            print("Push Notification validation failed")

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