import time
import allure
import pytest
from web_pages.cchq_login_web_page import LoginPage
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.web
def test_invite_worker_to_opportunity_connect(web_driver, test_data, config):
    cchq_login_page = LoginPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq_and_signin_connect(web_driver, config)

    with allure.step("Invite Workers to Opportunity in Connect Dashboard Page"):
        invite_workers_to_opportunity(web_driver, "Demo Opportunity", ["+919999999999", "+918888888888", "+917777777777"])

def invite_workers_to_opportunity(web_driver, opp, num_list):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_link_by_text(opp)
    odp = OpportunityDashboardPage(web_driver)
    odp.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
    odp.is_breadcrumb_item_present("Connect Workers")
    odp.click_add_worker_icon()
    cop.enter_invite_users_in_opportunity(num_list)
    time.sleep(2)
    cop.click_submit_btn()
    odp.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
    cop.verify_numbers_in_connect_workers_table(num_list)

