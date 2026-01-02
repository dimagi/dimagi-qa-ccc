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
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        self.cond_alert_full_name = name + "_" + timestamp
        self.type(self.CONDITIONAL_ALERT_NAME_INPUT, self.cond_alert_full_name)

    def select_case_type(self, value):
        self.select_by_visible_text(self.CASE_TYPE_INPUT, value)

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

    def create_new_connect_message_conditional_alert(self, params):
        name, case_type, user_recipients, message = params
        self.click_new_conditional_alert_btn()
        time.sleep(2)
        self.enter_name_in_conditional_alert(name)
        self.click_continue_btn()
        self.select_case_type(case_type)
        self.click_continue_btn()
        self.select_what_to_send_input("Connect Message")
        self.select_user_recipients(user_recipients)
        self.enter_message_in_broadcast(message)
        self.click_save_btn()
        self.is_created_alert_name_present_in_list(self.cond_alert_full_name)

    def select_survey_form_for_alert(self, value):
        self.scroll_into_view(self.SURVEY_FORM_INPUT)
        self.select_by_visible_text(self.SURVEY_FORM_INPUT, value)

    def enter_expire_after_for_alert(self, value):
        self.scroll_into_view(self.EXPIRE_AFTER_INPUT)
        self.type(self.EXPIRE_AFTER_INPUT, value)

    def create_new_connect_survey_conditional_alert(self, params):
        name, case_type, user_recipients, survey_form, expire_after = params
        self.click_new_conditional_alert_btn()
        time.sleep(2)
        self.enter_name_in_conditional_alert(name)
        self.click_continue_btn()
        self.select_case_type(case_type)
        self.click_continue_btn()
        self.select_what_to_send_input("Connect Survey")
        self.select_user_recipients(user_recipients)
        self.select_survey_form_for_alert(survey_form)
        self.enter_expire_after_for_alert(expire_after)
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
        self.scroll_into_view(self.SAVE_BUTTON)
        time.sleep(2)
        self.click_element(self.SAVE_BUTTON)

    # def click_last_page_in_pagination(self):
    #     pagination = self.wait_for_element(self.PAGINATION_CONTAINER)
    #     page_links = pagination.find_elements(By.XPATH,".//li//a")
    #     if not page_links:
    #         return
    #     last_page_link = page_links[-1]
    #     self.wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "i.fa-spinner")))
    #     self.driver.execute_script("arguments[0].scrollIntoView(true);", last_page_link)
    #     self.driver.execute_script("arguments[0].click();", last_page_link)
    #     time.sleep(15)

    def is_created_alert_name_present_in_list(self, name):
        time.sleep(2)
        self.wait_for_page_to_load()
        # self.click_last_page_in_pagination()
        self.scroll_into_view(self.ALERTS_LIST)
        table_ele = self.wait_for_element(self.ALERTS_LIST)
        name_elements = table_ele.find_elements(By.XPATH, "//tr//td[2]//a")
        assert any(name in n.text for n in name_elements)
        print(f"Created '{name}' conditional alert successfully")

    def click_add_broadcast_button(self):
        self.click_element(self.ADD_BROADCAST_BTN)
        time.sleep(1)
        self.verify_text_in_url("/broadcasts/add")

    def enter_broadcast_name(self, name):
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        self.broadcast_full_name = name + "_" + timestamp
        self.type(self.BROADCAST_NAME_INPUT, self.broadcast_full_name)

    def select_user_recipients(self, params):
        recipient_ele = self.wait_for_element(self.USER_RECIPIENT_INPUT)
        self.click_element(self.USER_RECIPIENT_INPUT)
        for each in params:
            recipient_ele.send_keys(each)
            time.sleep(1)
            recipient_ele.send_keys(Keys.ENTER)

    def enter_message_in_broadcast(self, message):
        self.scroll_into_view(self.MESSAGE_INPUT)
        self.type(self.MESSAGE_INPUT, message)

    def click_send_broadcast_btn(self):
        self.click_element(self.SEND_BROADCAST_BTN)

    def is_broadcast_name_present_in_list(self, name):
        time.sleep(2)
        self.wait_for_page_to_load()
        broadcasts_table = self.wait_for_element(self.BROADCASTS_TABLE)
        name_elements = broadcasts_table.find_elements(By.XPATH, "//tr//td//a")
        name_texts = [el.text.strip() for el in name_elements]
        assert name in name_texts, (
            f"Expected '{name}' not found in Name column. "
            f"Actual values: {name_texts}"
        )
        print(f"Created '{name}' broadcast successfully")

    def create_new_broadcast_with_connect_message_option(self, params):
        name, user_recipients, message = params
        self.click_add_broadcast_button()
        time.sleep(1)
        self.enter_broadcast_name(name)
        self.select_what_to_send_input("Connect Message")
        self.select_user_recipients(user_recipients)
        self.enter_message_in_broadcast(message)
        self.click_send_broadcast_btn()
        time.sleep(2)
        self.verify_text_in_url("/broadcasts/")
        self.is_broadcast_name_present_in_list(self.broadcast_full_name)

    def create_new_broadcast_with_connect_survey_option(self, params):
        name, user_recipients, survey_form, expire_after = params
        self.click_add_broadcast_button()
        time.sleep(1)
        self.enter_broadcast_name(name)
        self.select_what_to_send_input("Connect Survey")
        self.select_user_recipients(user_recipients)
        self.select_survey_form_for_alert(survey_form)
        self.enter_expire_after_for_alert(expire_after)
        self.click_send_broadcast_btn()
        time.sleep(2)
        self.verify_text_in_url("/broadcasts/")
        self.is_broadcast_name_present_in_list(self.broadcast_full_name)

