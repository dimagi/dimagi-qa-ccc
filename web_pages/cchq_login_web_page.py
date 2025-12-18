import time
from selenium.webdriver import Keys
from web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class LoginPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    TITLE_ELE = locators.get("login_page", "welcome_title")
    USERNAME_ELE = locators.get("login_page", "username_field")
    PASSWORD_ELE = locators.get("login_page", "password_field")
    SIGNIN_BUTTON = locators.get("login_page", "signin_button")
    ACCEPT_COOKIES_BUTTON = locators.get("login_page", "cookie_accept_button")

    def verify_login_page_title(self, title):
        assert title in self.get_text(self.TITLE_ELE)

    def enter_username_and_password(self, username, password):
        self.wait_for_element(self.USERNAME_ELE).send_keys(username)
        self.wait_for_element(self.PASSWORD_ELE).send_keys(password)
        self.click_element(self.ACCEPT_COOKIES_BUTTON)
        self.wait_for_element(self.PASSWORD_ELE).send_keys(Keys.ENTER)
        #self.click_element(self.SIGNIN_BUTTON)
