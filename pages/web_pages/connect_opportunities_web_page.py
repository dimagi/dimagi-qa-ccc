import time
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from pages.web_pages.connect_opportunity_dashboard_web_page import OpportunityDashboardPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectOpportunitiesPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    ADD_OPPORTUNITY_BUTTON = locators.get("connect_opportunities_page", "add_opportunity_btn")
    OPP_NAME_INPUT = locators.get("connect_opportunities_page", "name_input")
    OPP_CURRENCY_INPUT = locators.get("connect_opportunities_page", "currency_input")
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
    CONNECT_WORKERS_TABLE = locators.get("connect_opportunities_page", "connect_workers_table")
    OPPORTUNITIES_TABLE = locators.get("connect_opportunities_page", "opportunities_table")

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


    def click_add_opportunity_btn(self):
        self.click_element(self.ADD_OPPORTUNITY_BUTTON)

    def enter_name_in_opportunity(self , value):
        self.wait_for_element(self.OPP_NAME_INPUT)
        self.type(self.OPP_NAME_INPUT, value)

    def enter_currency_in_opportunity(self , value):
        self.wait_for_element(self.OPP_CURRENCY_INPUT)
        self.type(self.OPP_CURRENCY_INPUT, value)

    def enter_short_description_in_opportunity(self , value):
        self.wait_for_element(self.OPP_SHORT_DESCRIPTION_INPUT)
        self.type(self.OPP_SHORT_DESCRIPTION_INPUT, value)

    def enter_description_in_opportunity(self , value):
        self.wait_for_element(self.OPP_DESCRIPTION_INPUT)
        self.type(self.OPP_DESCRIPTION_INPUT, value)

    def select_hq_server_in_opportunity(self , value):
        self.wait_for_element(self.OPP_SHORT_DESCRIPTION_INPUT)
        self.select_by_visible_text(self.OPP_HQ_SERVER_DROPDOWN, value)

    def select_api_key_in_opportunity(self , value):
        time.sleep(2)
        self.wait_for_element(self.OPP_API_KEY_DROPDOWN)
        self.select_by_visible_text(self.OPP_API_KEY_DROPDOWN, value)

    def select_learn_app_domain_in_opportunity(self , value):
        time.sleep(2)
        self.scroll_into_view(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.wait_for_element(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DOMAIN_DROPDOWN, value)

    def select_deliver_app_domain_in_opportunity(self , value):
        time.sleep(2)
        self.scroll_into_view(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.wait_for_element(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN, value)

    def select_learn_app_in_opportunity(self , value):
        time.sleep(5)
        self.scroll_into_view(self.OPP_LEARN_APP_DROPDOWN)
        self.wait_for_clickable(self.OPP_LEARN_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DROPDOWN, value)

    def select_deliver_app_in_opportunity(self , value):
        time.sleep(5)
        self.scroll_into_view(self.OPP_DELIVER_APP_DROPDOWN)
        self.wait_for_clickable(self.OPP_DELIVER_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DROPDOWN, value)

    def enter_learn_app_description_in_opportunity(self , value):
        self.scroll_into_view(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.wait_for_element(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.type(self.OPP_LEARN_APP_DESCRIPTION_INPUT, value)

    def enter_passing_score_in_opportunity(self , value):
        self.scroll_into_view(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.wait_for_element(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.type(self.OPP_LEARN_APP_PASSING_SCORE_INPUT, value)

    def click_opportunity_in_opportunity(self , value):
        self.click_link_by_text(value)

    def click_submit_btn(self):
        self.scroll_into_view(self.SUBMIT_BUTTON)
        self.click_element(self.SUBMIT_BUTTON)

    def verify_numbers_in_connect_workers_table(self, num_list):
        table = self.wait_for_element(self.CONNECT_WORKERS_TABLE)
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        table_numbers = [row.find_element(By.XPATH, "./td[5]").text.strip() for row in rows]
        for number in num_list:
            assert number in table_numbers, f"Number '{number}' not found in the table!"

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
        self.scroll_into_view(self.START_DATE_INPUT)
        self.enter_date(self.START_DATE_INPUT, value)

    def enter_end_date_in_payment_unit_of_opportunity(self , value):
        self.scroll_into_view(self.END_DATE_INPUT)
        self.enter_date(self.END_DATE_INPUT, value)

    def select_required_deliver_units_checkbox(self, required_text):
        parent = self.wait_for_element(self.REQUIRED_DELIVER_UNITS_SECTION)
        label = parent.find_element(By.XPATH, f".//label[normalize-space()[contains(., '{required_text}')]]")
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
        elements = table.find_elements("xpath", f".//td//a[text()='{opp_name}']")
        assert len(elements) > 0, f"Opportunity '{opp_name}' not found in the table."

    def create_opportunity_in_connect_page(self, data):
        self.click_add_opportunity_btn()
        time.sleep(1)
        self.enter_name_in_opportunity(data["opportunity_name"])
        self.enter_currency_in_opportunity(data["currency"])
        self.enter_short_description_in_opportunity(data["short_description"])
        self.select_hq_server_in_opportunity(data["hq_server"])
        self.enter_description_in_opportunity(data["description"])
        self.select_api_key_in_opportunity(data["api_key"])
        self.select_learn_app_domain_in_opportunity(data["learn_app_domain"])
        self.select_deliver_app_domain_in_opportunity(data["deliver_app_domain"])
        self.select_learn_app_in_opportunity(data["learn_app"])
        self.select_deliver_app_in_opportunity(data["deliver_app"])
        self.enter_learn_app_description_in_opportunity(data["learn_app_description"])
        self.enter_passing_score_in_opportunity(data["passing_score"])
        self.click_submit_btn()
        time.sleep(3)

    def create_payment_unit_in_connect_page(self, data):
        self.click_add_payment_unit_button()
        self.enter_name_in_opportunity(data["payment_unit_name"])
        self.enter_amount_in_payment_unit_of_opportunity(data["amount"])
        self.enter_description_in_opportunity(data["description"])
        self.enter_max_total_in_payment_unit_of_opportunity(data["max_total"])
        self.enter_max_daily_in_payment_unit_of_opportunity(data["max_daily"])
        self.enter_start_date_in_payment_unit_of_opportunity(data["start_date"])
        self.enter_end_date_in_payment_unit_of_opportunity(data["end_date"])
        #self.select_required_deliver_units_checkbox(data["required_deliver_units"])
        self.click_submit_btn()
        time.sleep(3)
        self.verify_payment_unit_present(data["payment_unit_name"])

    def setup_budget_in_connect_page(self, data):
        self.click_setup_budget_button()
        self.enter_start_date_in_payment_unit_of_opportunity(data["start_date"])
        self.enter_end_date_in_payment_unit_of_opportunity(data["end_date"])
        self.enter_max_connect_workers_in_budget(data["no_of_connect_workers"])
        self.verify_total_budget_value(data["total_budget_value"])
        self.click_submit_btn()
        time.sleep(3)
        self.verify_opportunity_name_in_table(data["opportunity_name"])
