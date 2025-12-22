import allure
import pytest

from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_connect_5_verify_opportunity_list(mobile_driver, test_data):
    data = test_data.get("CONNECT_5")

    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)



    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["username"],
                                 data["backup_code"])   # test number


    with allure.step("Navigate to Opportunity page"):
        home.nav_to_opportunities()

    with allure.step("Handle Fingerprint Authentication"):
        pid.handle_fingerprint_auth()

    with allure.step("Verify Opportunity List"):
        opportunity.verify_opportunity_list()




