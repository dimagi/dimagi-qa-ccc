import time
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from web_pages.base_web_page import BaseWebPage
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
    INVITE_USERS_INPUT = locators.get("connect_opportunities_page", "invite_users_input")
    ADD_PAYMENT_UNIT_BUTTON = locators.get("connect_opportunities_page", "add_payment_btn")
    AMOUNT_INPUT = locators.get("connect_opportunities_page", "amount_input")
    MAX_TOTAL_INPUT = locators.get("connect_opportunities_page", "max_total_input")
    MAX_DAILY_INPUT = locators.get("connect_opportunities_page", "max_daily_input")
    START_DATE_INPUT = locators.get("connect_opportunities_page", "start_date_input")
    END_DATE_INPUT = locators.get("connect_opportunities_page", "end_date_input")
    REQUIRED_DELIVER_UNITS_SECTION = locators.get("connect_opportunities_page", "required_delivery_section")
    CONNECT_WORKERS_TABLE = locators.get("connect_opportunities_page", "connect_workers_table")

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

    def enter_invite_users_in_opportunity(self, num_list):
        input_element = self.wait_for_element(self.INVITE_USERS_INPUT)
        for each in num_list:
            input_element.send_keys(each)
            input_element.send_keys(Keys.ENTER)

    def verify_numbers_in_connect_workers_table(self, num_list):
        table = self.wait_for_element(self.CONNECT_WORKERS_TABLE)
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        table_numbers = [row.find_element(By.XPATH, "./td[5]").text.strip() for row in rows]
        for number in num_list:
            assert number in table_numbers, f"Number '{number}' not found in the table!"

    def click_add_payment_unit_button(self):
        self.click_element(self.ADD_PAYMENT_UNIT_BUTTON)

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

    def select_required_deliver_units_checkbox(self, required_text: str):
        parent = self.wait_for_element(self.REQUIRED_DELIVER_UNITS_SECTION)
        label = parent.find_element(By.XPATH, f".//label[normalize-space()[contains(., '{required_text}')]]")
        checkbox = label.find_element(By.TAG_NAME, "input")
        if not checkbox.is_selected():
            label.click()