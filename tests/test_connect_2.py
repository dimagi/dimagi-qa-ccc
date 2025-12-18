import allure
import pytest
from mobile_pages.personal_id_page import PersonalIDPage
from mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_connect_2_go_to_connect_and_refresh_opportunity_option(mobile_driver, test_data):
    data = test_data.get("CONNECT_2")

    # web driver and page initiation

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


    with allure.step("Verify Refresh Opportunity button shown"):
        home.verify_refresh_opportunity()

    with allure.step("Verify Go To Connect button shown"):
        home.verify_go_to_connect()


