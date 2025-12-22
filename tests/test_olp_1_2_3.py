import allure
import pytest
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage

@pytest.mark.web
def test_olp_1_2_3_setup_budget_in_connect(web_driver, test_data, config):
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")
    cchq_login_page = LoginPage(web_driver)

    with allure.step("Login to CommCare HQ and SignIn Connect with CommCare HQ"):
        cchq_login_page.valid_login_cchq_and_signin_connect(web_driver, config)

    with allure.step("Add Opportunity in Connect Page with required fields"):
        create_opportunity_in_connect_page(web_driver, olp1_data)

    with allure.step("Add Payment Unit in Connect Page"):
        create_payment_unit_in_connect_page(web_driver, olp2_data)

    with allure.step("Setup Budget for opportunity in Connect Page"):
        setup_budget_in_connect_page(web_driver, olp3_data)

    time.sleep(10)

def create_opportunity_in_connect_page(web_driver, data):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_add_opportunity_btn()
    time.sleep(1)
    cop.enter_name_in_opportunity(data["opportunity_name"])
    cop.enter_currency_in_opportunity(data["currency"])
    cop.enter_short_description_in_opportunity(data["short_description"])
    cop.select_hq_server_in_opportunity(data["hq_server"])
    cop.enter_description_in_opportunity(data["description"])
    cop.select_api_key_in_opportunity(data["api_key"])
    cop.select_learn_app_domain_in_opportunity(data["learn_app_domain"])
    cop.select_deliver_app_domain_in_opportunity(data["deliver_app_domain"])
    cop.select_learn_app_in_opportunity(data["learn_app"])
    cop.select_deliver_app_in_opportunity(data["deliver_app"])
    cop.enter_learn_app_description_in_opportunity(data["learn_app_description"])
    cop.enter_passing_score_in_opportunity(data["passing_score"])
    cop.click_submit_btn()
    time.sleep(3)

def create_payment_unit_in_connect_page(web_driver, data):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_add_payment_unit_button()
    cop.enter_name_in_opportunity(data["payment_unit_name"])
    cop.enter_amount_in_payment_unit_of_opportunity(data["amount"])
    cop.enter_description_in_opportunity(data["description"])
    cop.enter_max_total_in_payment_unit_of_opportunity(data["max_total"])
    cop.enter_max_daily_in_payment_unit_of_opportunity(data["max_daily"])
    cop.enter_start_date_in_payment_unit_of_opportunity(data["start_date"])
    cop.enter_end_date_in_payment_unit_of_opportunity(data["end_date"])
    #cop.select_required_deliver_units_checkbox(data["required_deliver_units"])
    cop.click_submit_btn()
    time.sleep(3)
    cop.verify_payment_unit_present(data["payment_unit_name"])

def setup_budget_in_connect_page(web_driver, data):
    cop = ConnectOpportunitiesPage(web_driver)
    cop.click_setup_budget_button()
    cop.enter_start_date_in_payment_unit_of_opportunity(data["start_date"])
    cop.enter_end_date_in_payment_unit_of_opportunity(data["end_date"])
    cop.enter_max_connect_workers_in_budget(data["no_of_connect_workers"])
    cop.verify_total_budget_value(data["total_budget_value"])
    cop.click_submit_btn()
    time.sleep(3)
    cop.verify_opportunity_name_in_table(data["opportunity_name"])

