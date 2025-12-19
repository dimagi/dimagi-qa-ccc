import allure
import pytest

from pages.mobile_pages.notifications import Notifications
from pages.mobile_pages.opportunity_page import OpportunityPage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.home_page import HomePage


@pytest.mark.mobile
def test_connect_3_user_receive_opportunity_invite(mobile_driver, test_data):
    data = test_data.get("CONNECT_3")

    # web driver and page initiation

    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    notifications = Notifications(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)



    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Sign in with existing demo user"):
        pid.signin_existing_user(data["country_code"],
                                 data["phone_number"],
                                 data["mobile_username"],
                                 data["mobile_backup_code"])   # test number

    # launch connect portal and initiate the opp invite

    with allure.step("Verify push notification shown for the invite"):
        notifications.open_notifications()
        notifications.verify_opportunity_invite()
        notifications.click_opportunity_invite()

    with allure.step("Handle Fingerprint Authentication"):
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()

    with allure.step("Verify Opportunity Details"):
        opportunity.verify_job_card()
        opportunity.verify_delivery_details()
        opportunity.verify_learn_details()




