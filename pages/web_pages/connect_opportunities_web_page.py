import re
import time

from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.select import Select

from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from datetime import datetime

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectOpportunitiesPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    ADD_OPPORTUNITY_BUTTON = locators.get("connect_opportunities_page", "add_opportunity_btn")
    OPP_NAME_INPUT = locators.get("connect_opportunities_page", "name_input")
    OPP_CURRENCY_INPUT = locators.get("connect_opportunities_page", "currency_input")
    OPP_COUNTRY_INPUT = locators.get("connect_opportunities_page", "country_input")
    OPP_SHORT_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "short_description_input")
    OPP_HQ_SERVER_DROPDOWN = locators.get("connect_opportunities_page", "hq_server_dropdown")
    OPP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "description_input")
    OPP_API_KEY_DROPDOWN = locators.get("connect_opportunities_page", "api_key_dropdown")
    OPP_LEARN_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_domain_dropdown")
    OPP_DELIVER_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_domain_dropdown")
    OPP_LEARN_APP_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_dropdown")
    OPP_DELIVER_APP_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_dropdown")
    OPP_LEARN_APP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "learn_app_description")
    OPP_LEARN_APP_PASSING_SCORE_INPUT = locators.get("connect_opportunities_page", "learn_app_passing_score_input")
    SUBMIT_BUTTON = locators.get("connect_opportunities_page", "submit_button")
    OPPORTUNITIES_TABLE = locators.get("connect_opportunities_page", "opportunities_table")
    FILTER_BUTTON = locators.get("connect_opportunities_page", "filter_btn")
    IS_TEST_FILTER_DROPDOWN = locators.get("connect_opportunities_page", "is_test_filter_dropdown")
    STATUS_FILTER_INPUT = locators.get("connect_opportunities_page", "status_filter_dropdown")
    APPLY_BUTTON = locators.get("connect_opportunities_page", "apply_btn")

    ADD_PAYMENT_UNIT_BUTTON = locators.get("connect_opportunities_page", "add_payment_btn")
    AMOUNT_INPUT = locators.get("connect_opportunities_page", "amount_input")
    MAX_TOTAL_INPUT = locators.get("connect_opportunities_page", "max_total_input")
    MAX_DAILY_INPUT = locators.get("connect_opportunities_page", "max_daily_input")
    START_DATE_INPUT = locators.get("connect_opportunities_page", "start_date_input")
    END_DATE_INPUT = locators.get("connect_opportunities_page", "end_date_input")
    REQUIRED_DELIVER_UNITS_SECTION = locators.get("connect_opportunities_page", "required_delivery_section")
    PAYMENT_UNITS_TABLE = locators.get("connect_opportunities_page", "payment_units_table")
    MAX_CONNECT_WORKERS_INPUT = locators.get("connect_opportunities_page", "max_connect_workers")
    SETUP_BUDGET_BUTTON = locators.get("connect_opportunities_page", "setup_budget_btn")
    TOTAL_BUDGET_INPUT = locators.get("connect_opportunities_page", "total_budget_input")
    PAGE_SIZE = locators.get("connect_opportunities_page", "page_size")


    def click_add_opportunity_btn(self):
        self.click_element(self.ADD_OPPORTUNITY_BUTTON)

    def enter_name_in_opportunity(self , value):
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        self.opp_full_name =  value+ "_" +timestamp
        self.wait_for_element(self.OPP_NAME_INPUT)
        self.type(self.OPP_NAME_INPUT, self.opp_full_name)
        return self.opp_full_name

    def select_currency_in_opportunity(self , value):
        self.wait_for_element(self.OPP_CURRENCY_INPUT)
        self.select_by_visible_text(self.OPP_CURRENCY_INPUT, value)

    def select_country_in_opportunity(self , value):
        self.wait_for_element(self.OPP_COUNTRY_INPUT)
        self.select_by_visible_text(self.OPP_COUNTRY_INPUT, value)

    def enter_short_description_in_opportunity(self , value):
        self.wait_for_element(self.OPP_SHORT_DESCRIPTION_INPUT)
        self.type(self.OPP_SHORT_DESCRIPTION_INPUT, value)

    def enter_description_in_opportunity(self , value):
        self.wait_for_element(self.OPP_DESCRIPTION_INPUT)
        self.type(self.OPP_DESCRIPTION_INPUT, value)

    def select_hq_server_in_opportunity(self , value):
        self.wait_for_element(self.OPP_HQ_SERVER_DROPDOWN)
        time.sleep(1)
        self.select_by_visible_text(self.OPP_HQ_SERVER_DROPDOWN, value)
        time.sleep(3)

    def select_api_key_in_opportunity(self , value):
        time.sleep(8)
        self.wait_for_element(self.OPP_API_KEY_DROPDOWN)
        print(f"Selecting {value}")
        self.select_by_visible_text(self.OPP_API_KEY_DROPDOWN, value)

    def select_learn_app_domain_in_opportunity(self , value):
        time.sleep(2)
        self.scroll_to_element(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.wait_for_element(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DOMAIN_DROPDOWN, value)

    def select_deliver_app_domain_in_opportunity(self , value):
        time.sleep(2)
        self.scroll_to_element(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.wait_for_element(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN, value)

    def select_learn_app_in_opportunity(self , value):
        time.sleep(5)
        self.scroll_to_element(self.OPP_LEARN_APP_DROPDOWN)
        self.wait_for_clickable(self.OPP_LEARN_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DROPDOWN, value)

    def select_deliver_app_in_opportunity(self , value):
        time.sleep(5)
        self.scroll_to_element(self.OPP_DELIVER_APP_DROPDOWN)
        self.wait_for_clickable(self.OPP_DELIVER_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DROPDOWN, value)

    def enter_learn_app_description_in_opportunity(self , value):
        self.scroll_to_element(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.wait_for_element(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.type(self.OPP_LEARN_APP_DESCRIPTION_INPUT, value)

    def enter_passing_score_in_opportunity(self , value):
        self.scroll_to_element(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.wait_for_element(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.type(self.OPP_LEARN_APP_PASSING_SCORE_INPUT, value)

    def click_opportunity_in_opportunity(self , value):
        time.sleep(5)
        try:
            self.select_by_visible_text(self.PAGE_SIZE, "100")
            time.sleep(10)
        except:
            print("Dropdown not present")
        self.click_link_by_text(value)
        time.sleep(3)

    def click_submit_btn(self):
        self.scroll_to_element(self.SUBMIT_BUTTON)
        self.click_element(self.SUBMIT_BUTTON)

    def click_add_payment_unit_button(self):
        self.click_element(self.ADD_PAYMENT_UNIT_BUTTON)
        self.verify_text_in_url("/payment_units/create")

    def enter_amount_in_payment_unit_of_opportunity(self , value):
        self.wait_for_element(self.AMOUNT_INPUT)
        self.type(self.AMOUNT_INPUT, value)

    def enter_max_daily_in_payment_unit_of_opportunity(self , value):
        self.wait_for_element(self.MAX_DAILY_INPUT)
        self.type(self.MAX_DAILY_INPUT, value)

    def enter_max_total_in_payment_unit_of_opportunity(self , value):
        self.wait_for_element(self.MAX_TOTAL_INPUT)
        self.type(self.MAX_TOTAL_INPUT, value)

    def enter_start_date_in_payment_unit_of_opportunity(self , value):
        self.scroll_to_element(self.START_DATE_INPUT)
        self.enter_date(self.START_DATE_INPUT, value)

    def enter_end_date_in_payment_unit_of_opportunity(self , value):
        self.scroll_to_element(self.END_DATE_INPUT)
        self.enter_date(self.END_DATE_INPUT, value)

    def select_required_deliver_units_checkbox(self, required_text):
        parent = self.wait_for_element(self.REQUIRED_DELIVER_UNITS_SECTION)
        label = parent.find_element(By.XPATH, f".//label[contains(normalize-space(.), '{required_text}')]")
        checkbox = label.find_element(By.TAG_NAME, "input")
        if not checkbox.is_selected():
            label.click()

    def verify_payment_unit_present(self, payment_unit_name):
        table = self.wait_for_element(self.PAYMENT_UNITS_TABLE)
        rows = table.find_elements(By.XPATH, ".//tbody/tr[not(contains(@class,'detail-row'))]")
        for row in rows:
            unit_name_cell = row.find_element(By.XPATH, "./td[2]")
            if unit_name_cell.text.strip() == payment_unit_name:
                return
        raise AssertionError(f"Payment Unit '{payment_unit_name}' not found in UI table")

    def click_setup_budget_button(self):
        self.click_element(self.SETUP_BUDGET_BUTTON)
        self.verify_text_in_url("/finalize/")

    def enter_max_connect_workers_in_budget(self, value):
        self.wait_for_element(self.MAX_CONNECT_WORKERS_INPUT)
        self.type(self.MAX_CONNECT_WORKERS_INPUT, value)

    def verify_total_budget_value(self, value):
        time.sleep(1)
        element = self.wait_for_element(self.TOTAL_BUDGET_INPUT)
        actual_value = element.get_attribute("value")
        assert actual_value == value, f"Expected total budget value to be '{value}', but got '{actual_value}'"

    def verify_opportunity_name_in_table(self, opp_name):
        table = self.wait_for_element(self.OPPORTUNITIES_TABLE)
        element = table.find_element("xpath", f".//td//a[text()='{opp_name}']")
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        assert element.is_displayed(), f"Opportunity '{opp_name}' not found in the table."
        print(f"Opportunity '{opp_name}' present in table.")

    def fill_opportunity_form(self, data, learn_app, delivery_app, env):
        env = f"_{env}" if env == "staging" else ""
        opp_name=self.enter_name_in_opportunity(data["opportunity_name"])
        self.select_currency_in_opportunity(data["currency"])
        self.select_country_in_opportunity(data["country"])
        self.enter_short_description_in_opportunity(data["short_description"])
        self.enter_description_in_opportunity(data["description"])
        self.select_hq_server_in_opportunity(data[f"hq_server{env}"])
        time.sleep(3)
        self.select_api_key_in_opportunity(data[f"api_key{env}"])
        time.sleep(3)
        self.select_learn_app_domain_in_opportunity(data[f"learn_app_domain{env}"])
        time.sleep(2)
        self.select_deliver_app_domain_in_opportunity(data[f"deliver_app_domain{env}"])
        time.sleep(5)
        self.select_learn_app_in_opportunity(learn_app)
        self.select_deliver_app_in_opportunity(delivery_app)
        self.enter_learn_app_description_in_opportunity(data["learn_app_description"])
        self.enter_passing_score_in_opportunity(data["passing_score"])
        self.click_submit_btn()
        return opp_name

    def create_opportunity_in_connect_page(self, data, learn_app, delivery_app, env):
        self.click_add_opportunity_btn()
        time.sleep(5)
        try:
            opp_name=self.fill_opportunity_form(data, learn_app, delivery_app, env)
        except:
            self.refresh_current_page()
            time.sleep(3)
            opp_name=self.fill_opportunity_form(data, learn_app, delivery_app, env)
        time.sleep(3)
        return opp_name

    def create_payment_unit_in_connect_page(self, data):
        self.click_add_payment_unit_button()
        self.enter_name_in_opportunity(data["payment_unit_name"])
        self.enter_amount_in_payment_unit_of_opportunity(data["amount"])
        self.enter_description_in_opportunity(data["description"])

        self.enter_max_total_in_payment_unit_of_opportunity(data["max_total"])
        self.enter_max_daily_in_payment_unit_of_opportunity(data["max_daily"])
        try:
            start, end = self.generate_date_range(7, opt=1)
            print(start, end)
            self.enter_start_date_in_payment_unit_of_opportunity(start)
            self.enter_end_date_in_payment_unit_of_opportunity(end)
        except:
            start, end = self.generate_date_range(7, opt=2)
            print(start, end)
            self.enter_start_date_in_payment_unit_of_opportunity(start)
            self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.select_required_deliver_units_checkbox(data["required_deliver_units"])
        self.click_submit_btn()
        time.sleep(3)
        self.verify_payment_unit_present(self.opp_full_name)

    def setup_budget_in_connect_page(self, data):
        self.click_setup_budget_button()
        try:
            start, end = self.generate_date_range(7, opt=1)
            print(start, end)
            self.enter_start_date_in_payment_unit_of_opportunity(start)
            self.enter_end_date_in_payment_unit_of_opportunity(end)
        except:
            start, end = self.generate_date_range(7, opt=2)
            print(start, end)
            self.enter_start_date_in_payment_unit_of_opportunity(start)
            self.enter_end_date_in_payment_unit_of_opportunity(end)
        # start, end = self.generate_date_range(2)
        # print(start, end)
        # self.enter_start_date_in_payment_unit_of_opportunity(start)
        # self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.enter_max_connect_workers_in_budget(data["no_of_connect_workers"])
        self.verify_total_budget_value(data["total_budget_value"])
        self.click_submit_btn()
        time.sleep(3)
        self.is_breadcrumb_item_present(self.opp_full_name)

    def click_filter_btn(self):
        self.click_element(self.FILTER_BUTTON)

    def select_is_test_in_filters(self, value):
        self.select_by_visible_text(self.IS_TEST_FILTER_DROPDOWN, value)

    def select_status_in_filters(self, params):
        for each in params:
            self.select_by_visible_text(self.STATUS_FILTER_INPUT, each)
            time.sleep(1)

    def click_apply_btn(self):
        self.click_element(self.APPLY_BUTTON)

    def clear_filters_in_opportunities(self):
        self.click_filter_btn()
        self.select_is_test_in_filters("---------")
        Select(self.wait_for_element(self.STATUS_FILTER_INPUT)).deselect_all()
        self.click_apply_btn()
        time.sleep(1)

    def verify_status_for_all_opportunities(self, expected_status):
        table = self.wait_for_element(self.OPPORTUNITIES_TABLE)
        headers = table.find_elements(By.XPATH, ".//thead//th")
        status_col_index = None
        for index, header in enumerate(headers, start=1):
            if header.text.strip() == "Status":
                status_col_index = index
                break
        assert status_col_index is not None, "Status column not found in opportunities table"
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        assert rows, "No rows found in opportunities table"
        for row_num, row in enumerate(rows, start=1):
            status_element = row.find_element(By.XPATH, f"./td[{status_col_index}]//span[contains(@class,'badge')]")
            actual_status = status_element.text.strip()
            assert actual_status == expected_status, (
                f"Row {row_num}: Expected status '{expected_status}', "
                f"but found '{actual_status}'"
            )

    def apply_n_verify_filter_as_active_in_opportunities(self):
        self.clear_filters_in_opportunities()
        self.click_filter_btn()
        self.select_is_test_in_filters("Yes")
        self.select_status_in_filters(["Active"])
        self.click_apply_btn()
        self.wait_for_page_to_load()
        time.sleep(2)
        self.verify_status_for_all_opportunities("Active")
        time.sleep(2)

    def apply_n_verify_filter_as_ended_in_opportunities(self):
        self.clear_filters_in_opportunities()
        self.click_filter_btn()
        self.select_is_test_in_filters("Yes")
        self.select_status_in_filters(["Ended"])
        self.click_apply_btn()
        self.wait_for_page_to_load()
        time.sleep(2)
        self.verify_status_for_all_opportunities("Ended")
        time.sleep(2)

    def apply_n_verify_filter_as_inactive_in_opportunities(self):
        self.clear_filters_in_opportunities()
        self.click_filter_btn()
        self.select_is_test_in_filters("Yes")
        self.select_status_in_filters(["Inactive"])
        self.click_apply_btn()
        self.wait_for_page_to_load()
        time.sleep(2)
        self.verify_status_for_all_opportunities("Inactive")

