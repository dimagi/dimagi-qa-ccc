import allure
import pytest
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_connect_1_all_connect_options_side_menu(mobile_driver, test_data):
    data = test_data.get("CONNECT_1")
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)


    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["mobile_username"],
                                 data["mobile_backup_code"])   # test number


    with allure.step("Verify all connect options in the side menu"):
        home.verify_side_panel_options()


