import allure
import pytest
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage

@allure.feature("PID & CONNECT")
@allure.story("Login related validations")
@allure.tag("PID_4", "PID_5", "PID_6_1", "CONNECT_1", "CONNECT_2")
@allure.description("""
 This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - PID_5 : Login with valid credentials
  - PID_4 : Sign out for existing demo user
  - PID_6_1 : Verify wrong backup code entered error popup
  - CONNECT_1 : Verify all side menu options shown
  - CONNECT_2 : Verify Go To Connect button shown
  """)
@pytest.mark.mobile
# @pytest.mark.bugasura("TES11", "TES12", "TES13", "TES15", "TES16")
def test_login_and_home_page(mobile_driver, test_data):
    data = test_data.get("TC_1")

    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)

    username = data["username"]

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Enter Mobile Number and Continue"):
        pid.start_signup(data["country_code"], data["phone_number"])   # test number

    with allure.step("Handle Fingerprint Authentication"):
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()

    with allure.step("Confirm Demo User popup"):
        pid.demo_user_confirm()

    with allure.step("Enter Username"):
        pid.enter_name(username)

    with allure.step("Verify Backup Code screen with existing Username"):
        pid.verify_backup_code_screen(username)

    with allure.step("Verify wrong backup code entered error"):
        pid.verify_wrong_backup_code_err()

    with allure.step("Complete Sign In with correct backup code and Continue"):
        pid.enter_backup_code(data["backup_code"])

    with allure.step("Verify user logged in to Connect App"):
        assert home.is_username_displayed(username)

    with allure.step("Verify all connect options in the side menu"):
        home.verify_side_panel_options()

    with allure.step("Verify Go To Connect button shown"):
        home.verify_go_to_connect()

    with allure.step("Sign out from the App by clicking Forget PersonalID User"):
        home.sign_out()
