import time
from selenium.webdriver import Keys
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from pages.web_pages.cchq_home_web_page import HomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage


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

    def navigate_to_connect_page(self, web_driver, config):
        connect_url = config.get("connect_url")
        bp = BaseWebPage(web_driver)
        bp.open_url_in_new_tab(connect_url)
        assert connect_url in web_driver.current_url

    def signin_to_connect_page_using_cchq(self, web_driver):
        chp = ConnectHomePage(web_driver)
        chp.click_signin_link()
        time.sleep(3)
        chp.click_login_with_cchq()

    def valid_login_cchq_and_signin_connect(self, web_driver, config):
        lp = LoginPage(web_driver)
        cchq_url = config.get("cchq_url")
        web_driver.get(cchq_url)
        lp.verify_login_page_title("Welcome")
        lp.enter_username_and_password(
            config.get("hq_username"),
            config.get("hq_password")
        )
        time.sleep(3)
        hp = HomePage(web_driver)
        hp.verify_home_page_title("Welcome")
        self.navigate_to_connect_page(web_driver, config)
        self.signin_to_connect_page_using_cchq(web_driver)
        time.sleep(3)

