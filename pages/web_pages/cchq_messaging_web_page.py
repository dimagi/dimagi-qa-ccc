import time

from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from datetime import datetime
from selenium.webdriver.support import expected_conditions as EC

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class MessagingPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    NEW_CONDITIONAL_ALERT = locators.get("cchq_messaging_page", "new_conditional_alert")
    CONDITIONAL_ALERT_NAME_INPUT = locators.get("cchq_messaging_page", "conditional_alert_name_input")
    CONTINUE_BTN = locators.get("cchq_messaging_page", "continue_btn")
    CASE_TYPE_INPUT = locators.get("cchq_messaging_page", "case_type_input")
    SELECT_A_FILTER_BUTTON = locators.get("cchq_messaging_page", "select_a_filter_btn")
    CASE_PROPERTY_FILTER_OPTION = locators.get("cchq_messaging_page", "case_property_filter_option")
    CASE_PROPERTY_ENTITY_DROPDOWN = locators.get("cchq_messaging_page", "case_property_entity_dropdown")
    CASE_PROPERTY_EQUALS_DROPDOWN = locators.get("cchq_messaging_page", "case_property_equals_dropdown")
    CASE_PROPERTY_NAME_INPUT = locators.get("cchq_messaging_page", "case_property_name_input")
    RECIPIENT_INPUT = locators.get("cchq_messaging_page", "recipient_input")
    WHAT_TO_SEND_INPUT = locators.get("cchq_messaging_page", "what_to_send_input")
    SAVE_BUTTON = locators.get("cchq_messaging_page", "save_btn")
    ALERTS_LIST = locators.get("cchq_messaging_page", "alerts_list_table")
    PAGINATION_CONTAINER = locators.get("cchq_messaging_page", "pagination_container")
    ADD_BROADCAST_BTN = locators.get("cchq_messaging_page", "add_broadcast_btn")
    BROADCAST_NAME_INPUT = locators.get("cchq_messaging_page", "broadcast_name_input")
    SEND_BROADCAST_BTN = locators.get("cchq_messaging_page", "send_broadcast_btn")
    USER_RECIPIENT_INPUT = locators.get("cchq_messaging_page", "user_recipients_input")
    MESSAGE_INPUT = locators.get("cchq_messaging_page", "message_input")
    BROADCASTS_TABLE = locators.get("cchq_messaging_page", "broadcasts_table")
    SURVEY_FORM_INPUT = locators.get("cchq_messaging_page", "survey_form_input")
    EXPIRE_AFTER_INPUT = locators.get("cchq_messaging_page", "expire_after_input")
    PAGE_DROPDOWN = locators.get("cchq_messaging_page", "page_dropdown")
    PAGE_DROPDOWN_COND_ALERT = locators.get("cchq_messaging_page", "page_dropdown_cond_alert")

    def click_new_conditional_alert_btn(self):
        self.click_element(self.NEW_CONDITIONAL_ALERT)
        time.sleep(1)
        self.verify_text_in_url("/conditional/add")

    def click_continue_btn(self):
        btns = self.driver.find_elements(*self.CONTINUE_BTN)
        for each in btns:
            if each.is_enabled() and each.is_displayed():
                self.click_element(each)
                break

    def enter_name_in_conditional_alert(self, name):
        ts = int(time.time() * 1000)
        self.cond_alert_full_name = f"{name} {ts}"
        print(self.cond_alert_full_name)
        self.type(self.CONDITIONAL_ALERT_NAME_INPUT, self.cond_alert_full_name)

    def select_case_type(self, value):
        self.select_by_visible_text(self.CASE_TYPE_INPUT, value)

    def select_case_property_filter(self):
        self.wait_for_element(self.SELECT_A_FILTER_BUTTON)
        self.click_element(self.SELECT_A_FILTER_BUTTON)
        time.sleep(1)
        self.wait_for_element(self.CASE_PROPERTY_FILTER_OPTION)
        self.click_element(self.CASE_PROPERTY_FILTER_OPTION)

    def select_case_property_entity_dropdown(self, value):
        self.wait_for_element(self.CASE_PROPERTY_ENTITY_DROPDOWN)
        self.select_by_visible_text(self.CASE_PROPERTY_ENTITY_DROPDOWN, value)

    def select_case_property_equals_dropdown(self, value):
        self.wait_for_element(self.CASE_PROPERTY_EQUALS_DROPDOWN)
        self.select_by_visible_text(self.CASE_PROPERTY_EQUALS_DROPDOWN, value)

    def enter_name_in_case_property_input(self, value):
        self.wait_for_element(self.CASE_PROPERTY_NAME_INPUT)
        self.type(self.CASE_PROPERTY_NAME_INPUT, value)

    def select_n_apply_case_property_filter_with_entity_id(self, name):
        self.select_case_property_filter()
        self.select_case_property_entity_dropdown("entity_id")
        self.select_case_property_equals_dropdown("equals")
        self.enter_name_in_case_property_input(name)

    def select_recipients(self, params):
        recipient_ele = self.wait_for_element(self.RECIPIENT_INPUT)
        for each in params:
            recipient_ele.send_keys(each)
            time.sleep(1)
            recipient_ele.send_keys(Keys.ENTER)
        time.sleep(2)

    def select_what_to_send_input(self, value):
        self.select_by_visible_text(self.WHAT_TO_SEND_INPUT, value)
        time.sleep(2)

    def create_new_connect_message_conditional_alert(self, entity_id_value, user_recipients):
        self.click_new_conditional_alert_btn()
        time.sleep(2)
        self.enter_name_in_conditional_alert("Automation Message Alert")
        time.sleep(1)
        self.click_continue_btn()
        if "staging" in self.get_current_url():
            self.select_case_type("case")
        else:
            self.select_case_type("automation")
        self.select_n_apply_case_property_filter_with_entity_id(entity_id_value)
        self.click_continue_btn()
        time.sleep(3)
        self.wait_for_element(self.WHAT_TO_SEND_INPUT)
        self.select_what_to_send_input("Connect Message")
        time.sleep(1)
        self.enter_message_in_broadcast("Automation Test Message")
        time.sleep(1)
        self.select_recipients(["Users"])
        time.sleep(1)
        self.select_user_recipients(user_recipients)
        self.click_save_btn()
        self.is_created_alert_name_present_in_list(self.cond_alert_full_name)

    def select_survey_form_for_alert(self, value):
        self.scroll_into_view(self.SURVEY_FORM_INPUT)
        self.select_by_visible_text(self.SURVEY_FORM_INPUT, value)

    def enter_expire_after_for_alert(self, value):
        self.scroll_into_view(self.EXPIRE_AFTER_INPUT)
        self.type(self.EXPIRE_AFTER_INPUT, value)

    def create_new_connect_survey_conditional_alert(self, entity_id_value, user_recipients):
        self.click_new_conditional_alert_btn()
        time.sleep(2)
        self.enter_name_in_conditional_alert("Automation Survey Alert")
        self.click_continue_btn()
        self.select_case_type("automation")
        self.select_n_apply_case_property_filter_with_entity_id(entity_id_value)
        self.click_continue_btn()
        self.select_what_to_send_input("Connect Survey")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.select_survey_form_for_alert("Delivery App - ETE > Surveys > Survey")
        self.enter_expire_after_for_alert("1")
        self.click_save_btn()
        self.is_created_alert_name_present_in_list(self.cond_alert_full_name)

    def verify_options_present_in_what_to_send(self, values):
        what_to_send_ele = self.wait_for_element(self.WHAT_TO_SEND_INPUT)
        options = what_to_send_ele.find_elements(By.TAG_NAME, "option")
        actual_values = [opt.text.strip() for opt in options]
        for each in values:
            assert each in actual_values, f"{each} not in What to Send options"

    def navigate_to_conditional_alerts_n_verify_what_to_send_options(self, values):
        self.click_new_conditional_alert_btn()
        time.sleep(2)
        self.enter_name_in_conditional_alert("Sample Test")
        self.click_continue_btn()
        self.select_case_type("visit")
        self.click_continue_btn()
        self.verify_options_present_in_what_to_send(values)

    def click_save_btn(self):
        time.sleep(2)
        self.scroll_to_element(self.SAVE_BUTTON)
        time.sleep(2)
        self.js_click(self.SAVE_BUTTON)
        time.sleep(50)

    def click_last_page_in_pagination(self):
        pagination = self.wait_for_element(self.PAGINATION_CONTAINER)
        page_numbers = pagination.find_elements(By.XPATH, ".//li/a/span[normalize-space() and number(normalize-space())=number(normalize-space())]")
        assert page_numbers, "No pagination pages found"
        last_page = page_numbers[-1]
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", last_page)
        self.driver.execute_script("arguments[0].click();", last_page)

    def is_created_alert_name_present_in_list(self, name):
        time.sleep(2)
        self.wait_for_page_to_load()
        self.select_by_value(self.PAGE_DROPDOWN_COND_ALERT, "100")
        time.sleep(5)
        self.wait_for_element(self.NEW_CONDITIONAL_ALERT)
        self.scroll_into_view(self.NEW_CONDITIONAL_ALERT)
        table_ele = self.wait_for_element(self.ALERTS_LIST)
        name_elements = table_ele.find_elements(By.XPATH, "//tr//td[2]//a")
        assert any(name in n.text for n in name_elements)
        print(f"Created '{name}' conditional alert successfully")

    def click_add_broadcast_button(self):
        self.click_element(self.ADD_BROADCAST_BTN)
        time.sleep(1)
        self.verify_text_in_url("/broadcasts/add")

    def enter_broadcast_name(self, name):
        ts = int(time.time() * 1000)
        self.broadcast_full_name = f"{name} {ts}"
        self.type(self.BROADCAST_NAME_INPUT, self.broadcast_full_name)

    def select_user_recipients(self, params):
        time.sleep(3)
        recipient_ele = self.wait_for_element(self.USER_RECIPIENT_INPUT)
        self.click_element(self.USER_RECIPIENT_INPUT)
        for each in params:
            recipient_ele.send_keys(each)
            time.sleep(2)
            recipient_ele.send_keys(Keys.ENTER)

    def enter_message_in_broadcast(self, message):
        self.scroll_into_view(self.MESSAGE_INPUT)
        self.type(self.MESSAGE_INPUT, message)

    def click_send_broadcast_btn(self):
        self.click_element(self.SEND_BROADCAST_BTN)

    def is_broadcast_name_present_in_list(self, name):
        time.sleep(2)
        self.wait_for_page_to_load()
        self.select_by_value(self.PAGE_DROPDOWN, "100")
        time.sleep(5)
        broadcasts_table = self.wait_for_element(self.BROADCASTS_TABLE)
        name_elements = broadcasts_table.find_elements(By.XPATH, "//tr//td//a")
        name_texts = [el.text.strip() for el in name_elements]
        assert name in name_texts, (
            f"Expected '{name}' not found in Name column. "
            f"Actual values: {name_texts}"
        )
        print(f"Created '{name}' broadcast successfully")

    def create_new_broadcast_with_connect_message_option(self, user_recipients):
        self.click_add_broadcast_button()
        time.sleep(1)
        self.enter_broadcast_name("Connect Message Broadcast")
        self.select_what_to_send_input("Connect Message")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        time.sleep(1)
        self.enter_message_in_broadcast("Test Connect Message Broadcast")
        time.sleep(2)
        self.click_send_broadcast_btn()
        time.sleep(2)
        self.verify_text_in_url("/broadcasts/")
        self.is_broadcast_name_present_in_list(self.broadcast_full_name)

    def create_new_broadcast_with_connect_survey_option(self, user_recipients):
        self.click_add_broadcast_button()
        time.sleep(1)
        self.enter_broadcast_name("Connect Survey Broadcast")
        self.select_what_to_send_input("Connect Survey")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.select_survey_form_for_alert("Delivery App - ETE > Surveys > Survey")
        self.enter_expire_after_for_alert("1")
        self.click_send_broadcast_btn()
        time.sleep(2)
        self.verify_text_in_url("/broadcasts/")
        self.is_broadcast_name_present_in_list(self.broadcast_full_name)

    def delete_existing_alerts(self, name_prefix):
        while True:
            self.wait_for_page_load()
            rows = self.driver.find_elements(By.XPATH, "//table[contains(@class,'table')]/tbody/tr")
            deleted_any = False
            for row in rows:
                try:
                    name = row.find_element(By.XPATH, "./td[2]").text.strip()
                    status = row.find_element(By.XPATH, "./td[4]").text.strip().lower()
                    if name_prefix in name and status == "active":
                        delete_btn = row.find_element(By.XPATH, "./td[1]//button")
                        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", delete_btn)
                        delete_btn.click()
                        time.sleep(2)
                        alert = self.wait_for_js_alert_present()
                        alert.accept()
                        time.sleep(2)
                        deleted_any = True
                        break
                except Exception:
                    continue
            if not deleted_any:
                break
