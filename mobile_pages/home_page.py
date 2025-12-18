from mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class HomePage(BasePage):

    NAVIGATION_DRAWER = locators.get("home_page", "navigation_drawer_btn")
    SIGNIN_REGISTER = locators.get("home_page", "nav_drawer_signin_btn")
    PHONE_INPUT = locators.get("login_page", "phone_input")
    HEADER_USERNAME = locators.get("home_page", "header_username")
    ABOUT_COMMCARE_TXT = locators.get("home_page", "about_commcare_txt")
    MORE_OPTION = locators.get("home_page", "more_option_btn")
    FORGET_PERSONALID = locators.get("home_page", "forget_personalid_user_btn")

    OPPORTUNITIES_BTN = locators.get("side_menu", "opportunities_btn")
    COMMCARE_APP_BTN = locators.get("side_menu", "commcare_app_btn")
    MESSAGING_BTN = locators.get("side_menu", "messaging_btn")
    WORK_HISTORY_BTN = locators.get("side_menu", "work_history_btn")
    NOTIFICATIONS_BTN = locators.get("side_menu", "notifications_btn")
    ABOUT_COMMCARE_BTN = locators.get("side_menu", "about_commcare_btn")

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
        self.wait_for_element(self.NAVIGATION_DRAWER)
        self.click_element(self.NAVIGATION_DRAWER)
        self.click_element(self.MORE_OPTION)
        self.wait_for_element(self.FORGET_PERSONALID)
        self.click_element(self.FORGET_PERSONALID)

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
        pass

