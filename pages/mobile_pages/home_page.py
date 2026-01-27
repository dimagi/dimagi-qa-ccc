import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class HomePage(BasePage):

    NAVIGATION_DRAWER = locators.get("home_page", "navigation_drawer_btn")
    SIGNIN_REGISTER = locators.get("home_page", "nav_drawer_signin_btn")
    PHONE_INPUT = locators.get("login_page", "phone_input")
    HEADER_USERNAME = locators.get("home_page", "header_username")
    ABOUT_COMMCARE_TXT = locators.get("home_page", "about_commcare_txt")
    MORE_OPTION = locators.get("home_page", "more_option_btn")
    FORGET_PERSONAL_ID = locators.get("home_page", "forget_personalid_user_btn")
    REFRESH_OPPORTUNITIES = locators.get("home_page", "refresh_opportunities_btn")
    GOTO_CONNECT = locators.get("home_page", "go_to_connect_btn")

    OPPORTUNITIES_BTN = locators.get("home_page", "opportunities_btn")
    COMMCARE_APP_BTN = locators.get("home_page", "commcare_app_btn")
    MESSAGING_BTN = locators.get("home_page", "messaging_btn")
    WORK_HISTORY_BTN = locators.get("home_page", "work_history_btn")
    NOTIFICATIONS_BTN = locators.get("home_page", "notifications_btn")
    ABOUT_COMMCARE_BTN = locators.get("home_page", "about_commcare_btn")

    NOTIFICATIONS_HEADER_TXT = locators.get("app_notification", "notification_header_txt")
    CHANNELS_HEADER_TXT = locators.get("messaging", "channel_header_txt")

    def open_side_menu(self):
        self.wait_for_element(self.NAVIGATION_DRAWER)
        self.click_element(self.NAVIGATION_DRAWER)
        self.wait_for_element(self.ABOUT_COMMCARE_TXT)

    def click_signup(self):
        self.click_element(self.SIGNIN_REGISTER)
        self.wait_for_element(self.PHONE_INPUT)

    def is_username_displayed(self, name):
        return self.get_text(self.HEADER_USERNAME) == name

    def sign_out(self):
        # self.wait_for_element(self.NAVIGATION_DRAWER)
        # self.click_element(self.NAVIGATION_DRAWER)
        print("nav drawer before click")
        self.click_element(self.MORE_OPTION)
        time.sleep(1)
        self.click_element(self.MORE_OPTION)
        self.wait_for_element(self.FORGET_PERSONAL_ID)
        self.click_element(self.FORGET_PERSONAL_ID)

        self.wait_for_element(self.NAVIGATION_DRAWER)
        self.click_element(self.NAVIGATION_DRAWER)
        assert(self.is_displayed(self.SIGNIN_REGISTER))

    def verify_side_panel_options(self):
        menu_items = [
            self.OPPORTUNITIES_BTN,
            self.COMMCARE_APP_BTN,
            self.MESSAGING_BTN,
            self.WORK_HISTORY_BTN,
            self.NOTIFICATIONS_BTN,
            self.ABOUT_COMMCARE_BTN
        ]

        for item in menu_items:
            assert self.is_displayed(item), f"Side menu option not visible: {item}"

    def verify_refresh_opportunity(self):
        self.wait_for_element(self.NAVIGATION_DRAWER)
        self.click_element(self.NAVIGATION_DRAWER)
        time.sleep(5)
        self.click_element(self.MORE_OPTION)
        self.wait_for_element(self.REFRESH_OPPORTUNITIES)
        assert (self.is_displayed(self.REFRESH_OPPORTUNITIES))
        self.click_element(self.REFRESH_OPPORTUNITIES)


    def verify_go_to_connect(self):
        assert (self.is_displayed(self.GOTO_CONNECT))

    def nav_to_opportunities(self):
            if not self.is_displayed(self.OPPORTUNITIES_BTN):
                self.click_element(self.NAVIGATION_DRAWER)
            self.click_element(self.OPPORTUNITIES_BTN)
            time.sleep(2)


    def open_app_from_goto_connect(self):
        if self.is_displayed(self.MESSAGING_BTN):
            self.click_element(self.NAVIGATION_DRAWER)

        self.click_element(self.GOTO_CONNECT)
        time.sleep(2)
        simulate_fingerprint(driver=self.driver, run_on=self.driver.run_on)
        assert not self.is_displayed(self.GOTO_CONNECT)

    def nav_to_notifications(self):
        self.click_element(self.NOTIFICATIONS_BTN)
        time.sleep(2)
        assert self.is_displayed(self.NOTIFICATIONS_HEADER_TXT)

    def nav_to_messaging(self):
        self.click_element(self.NAVIGATION_DRAWER)
        self.click_element(self.MESSAGING_BTN)
        time.sleep(2)
        simulate_fingerprint(driver=self.driver, run_on=self.driver.run_on)






