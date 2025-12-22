from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectHomePage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    SIGNIN_LINK = locators.get("connect_home_page", "signin_link")
    LOGIN_WITH_CC_HQ = locators.get("connect_home_page", "login_with_cc_hq")
    AUTHORIZE_BUTTON = locators.get("connect_home_page", "authorize_button")
    OPPORTUNITIES_NAVBAR_LINK = locators.get("connect_home_page", "opportunities_navbar_item")

    def click_signin_link(self):
        self.click_element(self.SIGNIN_LINK)

    def click_login_with_cchq(self):
        self.click_element(self.LOGIN_WITH_CC_HQ)
        self.click_element(self.AUTHORIZE_BUTTON)
        self.click_element(self.OPPORTUNITIES_NAVBAR_LINK)
        self.verify_text_in_url("/opportunity/")

