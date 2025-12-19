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

    def enter_phone_number(self, phone_number):
        self.type_element(self.PHONE_INPUT, phone_number)

    def enter_country_code(self, country_code):
        self.type_element(self.COUNTRY_CODE, country_code)

    def accept_terms(self):
        self.click_element(self.TERMS_CHECKBOX)

    def continue_next(self):
        self.click_when_enabled(self.CONTINUE_BTN)

    def start_signup(self, country_code, phone_number):
        """
        Assumes user is already on Phone Number screen
        """
        self.enter_country_code(country_code)
        self.enter_phone_number(phone_number)
        self.accept_terms()
        self.continue_next()
        self.wait_for_element(self.USE_FINGERPRINT_TXT)

    def click_configure_fingerprint(self):
        self.click_element(self.CONFIGURE_FINGERPRINT_BTN)

    def handle_fingerprint_auth(self):
        # small wait for system UI
        time.sleep(2)
        simulate_fingerprint()

    def demo_user_confirm(self):
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
        self.wait_for_element(self.POPUP_MESSAGE_TXT)
        wrong_backup_code_txt = self.get_text(self.POPUP_MESSAGE_TXT)
        self.click_element(self.OK_BTN)
        assert re.match(
            rf"You have entered the wrong Backup Code. Please try again. You will need to create a new account after 2 more incorrect attempts.",
            wrong_backup_code_txt
        )

    def account_locked_error(self):
        self.wait_for_element(self.POPUP_MESSAGE_TXT)
        locked_txt = self.get_text(self.POPUP_MESSAGE_TXT)
        self.click_element(self.OK_BTN)
        assert re.match(
            rf"Your account has been locked. Please contact support",
            locked_txt
        )
