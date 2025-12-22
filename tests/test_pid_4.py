import allure
import pytest
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_pid_4_sign_out(mobile_driver, test_data):
    data = test_data.get("PID_4")
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number


    with allure.step("Click Forget user and sign out from the app"):
        home.sign_out()


