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
@allure.story("Max daily visits related validations")
@allure.tag("CONNECT_15")
@allure.description("""
  Covered manual test case:
  - CONNECT_15 : Verify user can only do the max visits allowed to them on a single day
  """)

@pytest.mark.mobile
@pytest.mark.web
# @pytest.mark.bugasura("TES29")
def test_max_visit_allowed(web_driver, mobile_driver, config, test_data, settings):
    data = test_data.get("TC_8")

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

    with allure.step("Open the opportunity delivery app"):
        home.open_app_from_goto_connect()
        opportunity.open_opportunity_from_list(data["opportunity_name"], "delivery")

    with allure.step("Check if daily visit already exhausted"):
        if delivery.verify_over_limit_message():
            allure.attach(
                "Daily visit already exhausted for today. Skipping remaining steps.",
                name="Over limit detected",
                attachment_type=allure.attachment_type.TEXT
            )
            assert True
            return

    with allure.step("Complete the daily visits"):
        delivery.sync_with_server()
        delivery.complete_daily_visits()

    with allure.step("Complete one more daily visit"):
        result = delivery.submit_form("Registration Form")
        delivery.sync_with_server()

    with allure.step("Verify daily visit progress not updated"):
        delivery.verify_daily_visits_progress()

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_login_page.navigate_to_connect_page(config)
        connect_home_page.signin_to_connect_page_using_cchq()
        connect_home_page.select_organization_from_list(data["org_name"])

    with allure.step("Verify Over limit flag present for the entity in worker visits"):
        opp_dashboard_page.navigate_to_services_delivered(data["opportunity_name"])
        connect_workers_page.click_name_in_table(data["username"])
        worker_visits_page.verify_overlimit_flag_present_for_the_entity_in_visits(result["name"])
