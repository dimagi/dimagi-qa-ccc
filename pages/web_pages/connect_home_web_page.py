import time
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from selenium.webdriver.common.by import By
from selenium.common import NoSuchElementException

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectHomePage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    SIGNIN_LINK = locators.get("connect_home_page", "signin_link")
    LOGIN_WITH_CC_HQ = locators.get("connect_home_page", "login_with_cc_hq")
    AUTHORIZE_BUTTON = locators.get("connect_home_page", "authorize_button")
    OPPORTUNITIES_NAVBAR_LINK = locators.get("connect_home_page", "opportunities_navbar_item")
    PROGRAMS_NAVBAR_LINK = locators.get("connect_home_page", "programs_navbar_item")
    MY_ORGANIZATION_NAVBAR_LINK = locators.get("connect_home_page", "my_organization_navbar_item")
    ORGANIZATION_CONTAINER = locators.get("connect_home_page", "organization_container")
    ORGANIZATION_DROPDOWN = locators.get("connect_home_page", "organization_dropdown")
    ORGANIZATION_NAME = locators.get("connect_home_page", "organization_name")


    def click_signin_link(self):
        self.click_element(self.SIGNIN_LINK)

    def click_login_with_cchq(self):
        self.click_element(self.LOGIN_WITH_CC_HQ)
        self.click_element(self.AUTHORIZE_BUTTON)
        self.click_organizations_in_sidebar()

    def signin_to_connect_page_using_cchq(self):
        self.click_signin_link()
        time.sleep(2)
        self.click_login_with_cchq()

    def click_organizations_in_sidebar(self):
        self.click_element(self.OPPORTUNITIES_NAVBAR_LINK)
        self.verify_text_in_url("/opportunity/")

    def click_programs_in_sidebar(self):
        self.click_element(self.PROGRAMS_NAVBAR_LINK)
        self.verify_text_in_url("/program/")

    def click_my_organization_in_sidebar(self):
        self.click_element(self.MY_ORGANIZATION_NAVBAR_LINK)
        self.verify_text_in_url("/organization/")

    def click_organization_dropdown(self):
        self.click_element(self.ORGANIZATION_DROPDOWN)

    def is_org_selected(self, organization_name):
        time.sleep(1)
        return organization_name in self.get_text(self.ORGANIZATION_NAME)

    def select_organization_from_list(self, organization_name):
        if self.is_org_selected(organization_name):
            print(f"{organization_name} organization is already selected")
            return
        self.click_organization_dropdown()
        container = self.wait_for_element(self.ORGANIZATION_CONTAINER)
        item_xpath = f".//li[.//p[normalize-space() = {organization_name}]]"
        try:
            item = container.find_element(By.XPATH, item_xpath)
            self.click_element(item)
        except NoSuchElementException:
            print(f"Organization {organization_name} not found")
            raise NoSuchElementException
