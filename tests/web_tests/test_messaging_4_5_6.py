import allure
import pytest
from pygments.lexers import data
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_messaging_web_page import MessagingPage

@allure.feature("Messaging")
@allure.story("Confirm user can see and create Broadcasts with the two new message options on HQ")
@allure.tag("Messaging_4", "Messaging_5", "Messaging_6")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - Messaging_4 : Confirm user sees the two new message options on HQ when configuring Broadcasts 
  - Messaging_5 : Confirm user is able to configure a broadcast message with new Connect Message option
  - Messaging_6 : Confirm user is able to configure a broadcast message with new Connect Survey option
  """)

@pytest.mark.web
def test_messaging_4_create_n_verify_broadcasts_with_new_message_options(web_driver, test_data, config):
    messaging_4_5_6_data = test_data.get("MESSAGING_4_5_6")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_messaging_page = MessagingPage(web_driver)

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

    # Messaging_5
    with allure.step("Create new Broadcast with Connect Message Option"):
        cchq_messaging_page.create_new_broadcast_with_connect_message_option(messaging_4_5_6_data["connect_message_broadcast"])

    # Messaging_6
    with allure.step("Create new Broadcast with Connect Survey Option"):
        cchq_messaging_page.create_new_broadcast_with_connect_survey_option(messaging_4_5_6_data["connect_survey_broadcast"])