import allure
import pytest
from web_pages.connect_home_web_page import *
from web_pages.cchq_login_web_page import LoginPage
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage

@pytest.mark.web
def test_olp_4_verify_opportunity_details_in_dashboard(web_driver, test_data, config):
    olp4_data = test_data.get("OLP_4")
    cchq_login_page = LoginPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq_and_signin_connect(web_driver, config)

    with allure.step("Navigate to Opportunity Dashboard and verify all fields present"):
        navigate_to_opportunity_and_verify_all_fields_present_in_connect(web_driver, olp4_data)

    time.sleep(10)

def navigate_to_opportunity_and_verify_all_fields_present_in_connect(web_driver, data):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_link_by_text(data["opportunity_name"])
    odp = OpportunityDashboardPage(web_driver)
    odp.is_breadcrumb_item_present(data["opportunity_name"])
    odp.verify_start_date_card_value_present()
    odp.verify_end_date_card_value_present()
    odp.verify_dashboard_card_details_present("Connect Workers", "Invited")
    odp.verify_dashboard_card_details_present("Connect Workers", "Yet to Accept Invitation")
    odp.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
    odp.verify_dashboard_card_details_present("Services Delivered", "Total")
    odp.verify_dashboard_card_details_present("Services Delivered", "Pending NM Review")
    odp.verify_dashboard_card_details_present("Payments", "Earned")
    odp.verify_dashboard_card_details_present("Payments", "Due")
    odp.verify_progress_funnel_present()