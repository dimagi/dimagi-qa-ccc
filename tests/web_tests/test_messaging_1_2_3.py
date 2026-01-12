import allure
import pytest
from pygments.lexers import data
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_messaging_web_page import MessagingPage

@allure.feature("Messaging")
@allure.story("Verify user can see and create Conditional Alert with Connect Message & Connect Survey options")
@allure.tag("Messaging_1", "Messaging_2", "Messaging_3")
@allure.description("""
  This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - Messaging_1 : Confirm user sees the two new message options on HQ
  - Messaging_2 : Confirm user is able to configure a conditional alert with new Connect Message 
  - Messaging_3 : Confirm user is able to configure a conditional alert with new Connect Survey 
  """)

@pytest.mark.web
def test_messaging_1_2_3_create_n_verify_alerts_with_new_message_options(web_driver, test_data, config):
    messaging_1_2_3_data = test_data.get("MESSAGING_1_2_3")

    cchq_login_page = LoginPage(web_driver)
    cchq_home_page = CCHQHomePage(web_driver)
    cchq_messaging_page = MessagingPage(web_driver)

    with allure.step("Login to CommCare HQ and verify Welcome title"):
        cchq_login_page.valid_login_cchq(config)
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
        cchq_messaging_page.create_new_connect_message_conditional_alert(messaging_1_2_3_data["connect_message_alert"])

    # Messaging_3
    with allure.step("Create new conditional alert with Connect Survey option"):
        cchq_messaging_page.create_new_connect_survey_conditional_alert(messaging_1_2_3_data["connect_survey_alert"])
