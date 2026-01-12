import allure
import pytest

from pages.mobile_pages.otp_verification_page import OTPVerificationPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage

@allure.feature("PID")
@allure.story("Login related validations")
@allure.tag("PID_3")
@allure.description("""
 This automated test consolidates multiple manual test cases

  Covered manual test cases:
  - PID_3 : Confirm user can change the phone number by clicking the 'change' option
  """)
@pytest.mark.mobile
def test_login_and_home_page(mobile_driver, test_data):
    data = test_data.get("TC_9")

    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    otp_page = OTPVerificationPage(mobile_driver)

    username = data["username"]

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Enter Mobile Number and Continue"):
        pid.start_signup(data["country_code_1"], data["real_phone_number"])   # test number

    with allure.step("Handle Fingerprint Authentication"):
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()

    with allure.step("Chane Mobile Number and Continue"):
        otp_page.change_phone_number()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code_2"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])

