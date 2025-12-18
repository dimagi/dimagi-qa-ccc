import time
import pytest
from web_pages.cchq_login_web_page import *
from web_pages.cchq_home_web_page import *
from web_pages.connect_home_web_page import *
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage


@pytest.mark.web
def test_create_opportunity_in_connect(web_driver, config):
    valid_login_cchq_and_signin_connect(web_driver, config)
    create_opportunity_in_connect_page(web_driver, config)
    time.sleep(10)

@pytest.mark.web
def test_payment_unit_in_opportunity_connect(web_driver, config):
    valid_login_cchq_and_signin_connect(web_driver, config)
    create_opportunity_in_connect_page(web_driver, config)
    time.sleep(3)
    create_payment_unit_in_connect_page(web_driver, config)
    time.sleep(10)

def valid_login_cchq_and_signin_connect(web_driver, config):
    lp = LoginPage(web_driver)
    cchq_url = config.get("cchq_url")
    web_driver.get(cchq_url)
    lp.verify_login_page_title("Welcome")
    lp.enter_username_and_password(
        config.get("hq_username"),
        config.get("hq_password")
    )
    time.sleep(3)
    hp = HomePage(web_driver)
    hp.verify_home_page_title("Welcome")
    navigate_to_connect_page(web_driver, config)
    signin_to_connect_page_using_cchq(web_driver, config)
    time.sleep(3)

def navigate_to_connect_page(web_driver, config):
    connect_url = config.get("connect_url")
    bp = BaseWebPage(web_driver)
    bp.open_url_in_new_tab(connect_url)
    assert connect_url in web_driver.current_url

def signin_to_connect_page_using_cchq(web_driver, config):
    chp = ConnectHomePage(web_driver)
    chp.click_signin_link()
    time.sleep(3)
    chp.click_login_with_cchq()

def create_opportunity_in_connect_page(web_driver, config):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_add_opportunity_btn()
    time.sleep(1)
    cop.enter_name_in_opportunity("Demo Opportunity")
    cop.enter_currency_in_opportunity("INR")
    cop.enter_short_description_in_opportunity("This is a Demo Opportunity")
    cop.select_hq_server_in_opportunity("CommCareHQ (https://www.commcarehq.org)")
    cop.enter_description_in_opportunity("Demo Opportunity")
    cop.select_api_key_in_opportunity("fccc...0784")
    cop.select_learn_app_domain_in_opportunity("connetqa-prod")
    cop.select_deliver_app_domain_in_opportunity("connetqa-prod")
    cop.select_learn_app_in_opportunity("Learn App")
    cop.select_deliver_app_in_opportunity("Delivey App [Job 1]")
    cop.enter_learn_app_description_in_opportunity("This is Learn App")
    cop.enter_passing_score_in_opportunity("40")
    cop.click_submit_btn()

def create_payment_unit_in_connect_page(web_driver, config):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_add_payment_unit_button()
    cop.enter_name_in_opportunity("Payment Unit 1")
    cop.enter_amount_in_payment_unit_of_opportunity("100")
    cop.enter_description_in_opportunity("Payment Unit 1")
    cop.enter_max_total_in_payment_unit_of_opportunity("1000")
    cop.enter_max_daily_in_payment_unit_of_opportunity("10")
    time.sleep(3)
    cop.enter_start_date_in_payment_unit_of_opportunity("01/01/2026")
    time.sleep(3)
    cop.enter_end_date_in_payment_unit_of_opportunity("01/01/2027")
    time.sleep(3)
    cop.select_required_deliver_units_checkbox("Optional Delivery")
    time.sleep(3)
    cop.click_submit_btn()

@pytest.mark.web
def test_invite_worker_to_opportunity_connect(web_driver, config):
    valid_login_cchq_and_signin_connect(web_driver, config)
    invite_workers_to_opportunity(web_driver, "Demo Opportunity", ["+919999999999", "+918888888888", "+917777777777"])

def invite_workers_to_opportunity(web_driver, opp, num_list):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_link_by_text(opp)
    odp = OpportunityDashboardPage(web_driver)
    odp.click_connect_workers_link()
    odp.is_breadcrumb_item_present("Connect Workers")
    odp.click_add_worker_icon()
    cop.enter_invite_users_in_opportunity(num_list)
    time.sleep(2)
    cop.click_submit_btn()
    odp.click_connect_workers_link()
    cop.verify_numbers_in_connect_workers_table(num_list)