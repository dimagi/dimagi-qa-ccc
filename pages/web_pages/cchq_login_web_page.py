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
    IFRAME_GUIDE_POPUP = locators.get("cchq_login_page","iframe_guide_popup")
    RATING_POPUP_CLOSE = locators.get("cchq_login_page", "rating_popup_close")
    GUIDE_POPUP = locators.get("cchq_login_page","guide_popup")
    SKIP_ONBOARDING = locators.get("cchq_home_page", "skip_onboarding")
    VIEW_LATEST_UPDATES = locators.get("cchq_login_page", "view_latest_updates")

    def verify_login_page_title(self, title):
        print(self.get_text(self.TITLE_ELE))
        assert title in self.get_text(self.TITLE_ELE)

    def enter_username_and_password(self, username, password):
        self.wait_for_element(self.USERNAME_ELE)
        self.wait_for_element(self.PASSWORD_ELE)
        # self.dismiss_notification()
        self.switch_to_default_content()
        self.switch_to_latest_tab()
        try:
            self.click_element(self.ACCEPT_COOKIES_BUTTON)
        except:
            print("No Cookies alert present")
        self.type(self.USERNAME_ELE, username)
        self.type(self.PASSWORD_ELE, password+Keys.ENTER)
        # self.wait_for_element(self.PASSWORD_ELE).send_keys(Keys.ENTER)
        # self.wait_for_element(self.SIGNIN_BUTTON)
        # self.js_click(self.SIGNIN_BUTTON)
        time.sleep(3)


    def valid_login_cchq(self, config, settings):
        try:
            cchq_url = config.get("cchq_url")
            self.driver.get(cchq_url)
            self.wait_for_page_to_load()
            # self.verify_login_page_title("Welcome")
            time.sleep(3)
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

    def accept_alert(self):
        try:
            if self.is_present(self.ACCEPT_COOKIES_BUTTON):
                self.click(self.ACCEPT_COOKIES_BUTTON)
                print("banner accepted")
            else:
                print("no banner present")
        except (TimeoutException, NoSuchElementException):
            pass  # ignore if alert not on page

    def dismiss_notification(self):
        self.switch_to_frame(self.IFRAME)
        try:
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
        self.switch_to_default_content()

    def navigate_to_connect_page(self, config):
        connect_url = config.get("connect_url")
        self.open_url_in_new_tab(connect_url)
        assert connect_url in self.driver.current_url

    def dismiss_guide_popup(self):
        try:
            # wait a few seconds for popup iframe to appear
            self.wait_for_element(self.IFRAME_GUIDE_POPUP, timeout=8)

            self.switch_to_frame(self.IFRAME_GUIDE_POPUP)

            if self.is_present(self.GUIDE_POPUP):
                self.wait_for_element(self.SKIP_ONBOARDING)
                self.click_element(self.SKIP_ONBOARDING)
                print("Skipped onboarding popup")

        except (TimeoutException, NoSuchElementException):
            print("No onboarding popup occurred")

        finally:
            self.switch_to_default_content()

    def close_rating_popup(self):
        try:
            # wait a few seconds for popup iframe to appear
            self.wait_for_element(self.IFRAME_GUIDE_POPUP, timeout=8)

            self.switch_to_frame(self.IFRAME_GUIDE_POPUP)

            if self.is_present(self.GUIDE_POPUP):
                self.wait_for_element(self.RATING_POPUP_CLOSE)
                self.click_element(self.RATING_POPUP_CLOSE)
                print("Rating popup closed")

        except (TimeoutException, NoSuchElementException):
            print("No onboarding popup occurred")

        except (TimeoutException, NoSuchElementException):
            print("No onboarding popup occurred")

        finally:
            self.switch_to_default_content()


