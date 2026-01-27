import re
import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class PersonalIDPage(BasePage):

    PHONE_INPUT = locators.get("login_page", "phone_input")
    CONTINUE_BTN = locators.get("login_page", "continue_btn")
    COUNTRY_CODE = locators.get("login_page", "country_code")
    TERMS_CHECKBOX = locators.get("login_page", "terms_checkbox")
    USE_FINGERPRINT_TXT = locators.get("login_page", "use_fingerprint_txt")
    CONFIGURE_FINGERPRINT_BTN = locators.get("login_page", "configure_fingerprint_btn")
    DEMO_USER_CONFIRM = locators.get("login_page", "demo_user_confirm")
    OK_BTN = locators.get("login_page", "ok_btn")
    NAME_INPUT = locators.get("login_page", "name_input")
    BACKUP_CODE_WELCOME_TEXT = locators.get("login_page", "backup_code_welcome_text")
    BACKUP_CODE_INPUT = locators.get("login_page", "backup_code_input")
    POPUP_MESSAGE_TXT = locators.get("login_page", "popup_msg_txt")
    WRONG_BACKUP_CODE_TXT = locators.get("login_page", "wrong_backup_code_txt")
    NETWORK_ERROR_TXT = locators.get("login_page", "network_connection_err_txt")
    PROGRESS_BAR = locators.get("login_page", "progress_bar")

    def enter_phone_number(self, phone_number):
        self.type_element(self.PHONE_INPUT, phone_number)

    def enter_country_code(self, country_code):
        self.type_element(self.COUNTRY_CODE, country_code)

    def accept_terms(self):
        self.click_element(self.TERMS_CHECKBOX)

    def continue_next(self):
        try:
            self.click_when_enabled(self.CONTINUE_BTN)
        except Exception as e:
            self.click_element(self.TERMS_CHECKBOX)
            time.sleep(1)
            self.click_element(self.TERMS_CHECKBOX)
            time.sleep(2)
            self.click_element(self.CONTINUE_BTN)

    def start_signup(self, country_code, phone_number, retries=3):
        self.enter_country_code(country_code)
        self.enter_phone_number(phone_number)
        time.sleep(2)
        self.accept_terms()
        time.sleep(2)
        self.continue_next()
        time.sleep(5)
        self.wait_for_element_to_disappear(self.PROGRESS_BAR)

        if self.is_displayed(self.NETWORK_ERROR_TXT):
            for attempt in range(retries):
                print(f"Network Error: attempt {attempt + 1}")
                time.sleep(2)
                self.continue_next()
                self.wait_for_element_to_disappear(self.PROGRESS_BAR)
                if not self.is_displayed(self.NETWORK_ERROR_TXT):
                    break

            time.sleep(1)

    def click_configure_fingerprint(self):
        if self.BIOMETRIC_ENABLED:
            self.click_element(self.CONFIGURE_FINGERPRINT_BTN)
            time.sleep(2)

    def handle_fingerprint_auth(self):
        if self.BIOMETRIC_ENABLED:
            time.sleep(2)
            simulate_fingerprint(driver=self.driver, run_on=self.driver.run_on)

    def demo_user_confirm(self):
        if self.BIOMETRIC_ENABLED:
            time.sleep(2)
            self.wait_for_element(self.DEMO_USER_CONFIRM)
            self.click_element(self.OK_BTN)

    def enter_name(self, name):
        self.type_element(self.NAME_INPUT, name)
        time.sleep(2)
        self.click_when_enabled(self.CONTINUE_BTN)

    def verify_backup_code_screen(self, name):
        self.wait_for_element(self.BACKUP_CODE_WELCOME_TEXT)
        welcome_text = self.get_text(self.BACKUP_CODE_WELCOME_TEXT)
        assert re.match(
            rf"Welcome back\s+{name}",
            welcome_text
        )

    def enter_backup_code(self, code):
        self.type_element(self.BACKUP_CODE_INPUT, code)
        self.click_when_enabled(self.CONTINUE_BTN)
        self.wait_for_element(self.OK_BTN)
        self.click_element(self.OK_BTN)

    def signin_existing_user(self, mobile_country_code, mobile_num, username, mobile_backup_code):
        self.start_signup(mobile_country_code, mobile_num)
        self.click_configure_fingerprint()
        self.handle_fingerprint_auth()
        self.demo_user_confirm()
        self.enter_name(username)
        self.enter_backup_code(mobile_backup_code)

    def verify_wrong_backup_code_err(self):
        self.type_element(self.BACKUP_CODE_INPUT, "123456")
        self.click_when_enabled(self.CONTINUE_BTN)
        toast = self.wait_for_element(self.WRONG_BACKUP_CODE_TXT)
        toast_text = toast.text
        print(toast_text)
        assert "You have entered the wrong Backup Code" in toast_text
        self.wait_for_element(self.OK_BTN)
        self.click_element(self.OK_BTN)


    def account_locked_error(self):
        self.wait_for_element(self.POPUP_MESSAGE_TXT)
        locked_txt = self.get_text(self.POPUP_MESSAGE_TXT)
        assert re.match(
            rf"Your account has been locked. Please contact support",
            locked_txt
        )
        self.click_element(self.OK_BTN)


