import allure
import pytest
from mobile_pages.personal_id_page import PersonalIDPage
from mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_pid_6_1_wrong_backup_code_error(mobile_driver, test_data):
    data = test_data.get("PID_6_1")
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

    with allure.step("Enter Wrong Backup Code 1 time"):
        pid.enter_backup_code("123456")

    with allure.step("Verify wrong backup code entered error"):
        assert pid.verify_wrong_backup_code_err()
