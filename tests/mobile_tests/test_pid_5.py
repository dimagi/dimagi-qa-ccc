import allure
import pytest
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_pid_5_recover_existing_user(mobile_driver, test_data):
    data = test_data.get("PID_5")
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)

    username = data["username"]

    # Step 1: enter existing test number
    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Enter Mobile Number and Continue"):
        pid.start_signup(data["country_code"], data["phone_number"])   # test number

    # Step 2: device auth (handled via emulator / adb)
    with allure.step("Handle Fingerprint Authentication"):
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()

    # Step 3: Skip OTP for demo user
    with allure.step("Confirm Demo User popup"):
        pid.demo_user_confirm()

    # Step 4: Enter Name
    with allure.step("Enter Username"):
        pid.enter_name(username)

    # Step 5: Verify Backup code welcome text
    with allure.step("Verify Backup Code screen with existing Username"):
        pid.verify_backup_code_screen(username)

    # Step 6: Enter Backup Code
    with allure.step("Enter Backup Code and Continue"):
        pid.enter_backup_code(data["backup_code"])

    # Step 7: Verify user logged in
    with allure.step("Verify user logged in to Connect App"):
        assert home.is_username_displayed(username)
