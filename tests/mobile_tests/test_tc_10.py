import allure
import pytest
from pygments.lexers import data

from pages.mobile_pages.app_notifications import AppNotifications
from pages.mobile_pages.delivery_app_page import DeliveryAppPage
from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.messaging_page import Message
from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_messaging_web_page import MessagingPage

@allure.feature("Messaging")
@allure.story("Verify Conditional Alert with Connect Message & Connect Survey options")
@allure.tag("Messaging_4", "Messaging_5", "Messaging_6")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - Messaging_4 : Confirm user sees the two new message options on HQ when configuring Broadcasts 
  - Messaging_5 : Confirm user is able to configure a broadcast message with new Connect Message option
  - Messaging_6 : Confirm user is able to configure a broadcast message with new Connect Survey option
  """)

@pytest.mark.web
@pytest.mark.mobile
def test_messaging_create_n_verify_broadcasts_with_new_message_options(mobile_driver, web_driver, test_data, config):
    data = test_data.get("TC_10")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_messaging_page = MessagingPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    app_notification = AppNotifications(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)
    message = Message(mobile_driver)

    with allure.step("Login to CommCare HQ and verify Welcome title"):
        cchq_login_page.valid_login_cchq(config)
        cchq_home_page.verify_home_page_title("Welcome")

    with allure.step("Navigate to Broadcasts under Messaging"):
        cchq_home_page.click_option_under_messaging_tab("Broadcasts")
        cchq_home_page.verify_breadcrumb_text_present_cchq("Broadcasts")

    # Messaging_4
    with allure.step("Verify new message options available in What to Send dropdown in Broadcasts"):
        cchq_messaging_page.click_add_broadcast_button()
        cchq_messaging_page.verify_options_present_in_what_to_send(["Connect Message", "Connect Survey"])
        cchq_home_page.click_option_under_messaging_tab("Broadcasts")

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])

    with allure.step("Open the Delivery App"):
        home.open_app_from_goto_connect()
        opportunity.open_opportunity_from_list(data["opportunity_name"], "delivery")

    with allure.step("Get User Id from the Connect App"):
        user_id = delivery.get_user_id()

    with allure.step("Navigate to Messaging option"):
        message.open_channel_on_message("connetqa-prod")

    # Messaging_5
    with allure.step("Create new Broadcast with Connect Message Option"):
        cchq_messaging_page.create_new_broadcast_with_connect_message_option([user_id])

    with allure.step("Verify Broadcast Connect Message shown"):
        message.verify_connect_message()

    # Messaging_6
    with allure.step("Create new Broadcast with Connect Survey Option"):
        cchq_messaging_page.create_new_broadcast_with_connect_survey_option([user_id])

    with allure.step("Verify Broadcast Connect Survey shown"):
        message.fill_survey_form()