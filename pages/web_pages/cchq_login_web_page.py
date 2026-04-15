import time

from selenium.common import TimeoutException, NoSuchElementException
from selenium.webdriver import Keys
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage


locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class LoginPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    TITLE_ELE = locators.get("cchq_login_page", "welcome_title")
    USERNAME_ELE = locators.get("cchq_login_page", "username_field")
    PASSWORD_ELE = locators.get("cchq_login_page", "password_field")
    SIGNIN_BUTTON = locators.get("cchq_login_page", "signin_button")
    ACCEPT_COOKIES_BUTTON = locators.get("cchq_login_page", "cookie_accept_button")
    CLOSE_NOTIFICATION = locators.get("cchq_login_page", "close_notification")
    IFRAME = locators.get("cchq_login_page", "iframe")
    VIEW_LATEST_UPDATES = locators.get("cchq_login_page", "view_latest_updates")

    def verify_login_page_title(self, title):
        assert title in self.get_text(self.TITLE_ELE)

    def enter_username_and_password(self, username, password):
        self.wait_for_element(self.USERNAME_ELE).send_keys(username)
        self.wait_for_element(self.PASSWORD_ELE).send_keys(password)
        try:
            self.click_element(self.ACCEPT_COOKIES_BUTTON)
        except:
            print("No Cookies alert present")
        self.dismiss_notification()
        self.wait_for_element(self.PASSWORD_ELE).send_keys(Keys.ENTER)
        #self.click_element(self.SIGNIN_BUTTON)


    def valid_login_cchq(self, config, settings):
        try:
            cchq_url = config.get("cchq_url")
            self.driver.get(cchq_url)
            self.wait_for_page_to_load()
            self.verify_login_page_title("Welcome")
            self.enter_username_and_password(
                settings.get(
                    section="creds",
                    key="hq_username",
                    env_var="hq_username"
                    ),
                settings.get(
                    section="creds",
                    key="hq_password",
                    env_var="hq_password"
                    )
                # config.get("hq_username"),
                # config.get("hq_password")
            )
            time.sleep(3)
        except:
            print("User is already logged in")

    def dismiss_notification(self):
        try:
            self.driver.switch_to.frame(self.find_element(self.IFRAME))
            if self.is_present(self.VIEW_LATEST_UPDATES):
                self.wait_for_element(self.VIEW_LATEST_UPDATES)
                self.click_element(self.CLOSE_NOTIFICATION)
                print("notification dismissed")
            else:
                print("no notification present")
            self.driver.switch_to.default_content()
        except TimeoutException:
            pass  # ignore if notification  not on page
        except NoSuchElementException:
            pass

    def navigate_to_connect_page(self, config):
        connect_url = config.get("connect_url")
        self.open_url_in_new_tab(connect_url)
        assert connect_url in self.driver.current_url
