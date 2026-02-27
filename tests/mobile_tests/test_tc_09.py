import time

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
@allure.tag("Messaging_1", "Messaging_2", "Messaging_3")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - Messaging_1 : Confirm user sees the two new message options on HQ
  - Messaging_2 : Confirm user is able to configure a conditional alert with new Connect Message 
  - Messaging_3 : Confirm user is able to configure a conditional alert with new Connect Survey 
  """)

@pytest.mark.web
@pytest.mark.mobile
# @pytest.mark.bugasura("TES33", "TES34", "TES35")
def test_messaging_create_n_verify_alerts_with_new_message_options(web_driver, mobile_driver, test_data, config, settings):
    data = test_data.get("TC_9")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_messaging_page = MessagingPage(web_driver)

    # mobile driver and page initiation
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    delivery = DeliveryAppPage(mobile_driver)
    message = Message(mobile_driver)

    temp_id = int(time.time() * 1000) % 1000000

    with allure.step("Login to CommCare HQ and verify Welcome title"):
        cchq_login_page.valid_login_cchq(config, settings)
        cchq_home_page.verify_home_page_title("Welcome")

    with allure.step("Navigate to Conditional Alerts under Messaging"):
        cchq_home_page.click_option_under_messaging_tab("Conditional Alerts")
        cchq_home_page.verify_breadcrumb_text_present_cchq("Conditional Alerts")

    # Messaging_1
    with allure.step("Verify new message options available in What to Send dropdown in Conditional Alerts"):
        cchq_messaging_page.navigate_to_conditional_alerts_n_verify_what_to_send_options(["Connect Message", "Connect Survey"])
        cchq_home_page.click_option_under_messaging_tab("Conditional Alerts")

    # Messaging_2
    with allure.step("Create new conditional alert with Connect Message option"):
        cchq_messaging_page.delete_existing_alerts("Automation Message Alert")
        cchq_messaging_page.create_new_connect_message_conditional_alert(user_recipients=[data["user_id"]],
                                                                         entity_id_value=temp_id)


    # Messaging_3
    with allure.step("Create new conditional alert with Connect Survey option"):
        cchq_messaging_page.delete_existing_alerts("Automation Survey Alert")
        cchq_messaging_page.create_new_connect_survey_conditional_alert(user_recipients=[data["user_id"]],
                                                                         entity_id_value=temp_id)

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

    with allure.step("Submit the form on the Delivery App"):
        delivery.submit_form("Registration Form", user_id_input=temp_id)

    with allure.step("Navigate to Messaging option"):
        if 'staging' in config.get("cchq_url"):
            message.open_channel_on_message("connectqa")
        else:
            message.open_channel_on_message("connetqa-prod")

    with allure.step("Verify Connect Message shown"):
        message.verify_connect_message()

    with allure.step("Complete Connect Survey"):
        message.fill_survey_form()