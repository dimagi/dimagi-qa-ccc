import time

from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class CCHQHomePage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    TITLE_ELE = locators.get("cchq_home_page", "welcome_title")
    MESSAGING_TAB = locators.get("cchq_home_page", "messaging_tab")
    BREADCRUMB_CONTAINER = locators.get("cchq_home_page", "breadcrumb_container")
    APPLICATIONS_TAB = locators.get("cchq_home_page", "applications_tab")

    def verify_home_page_title(self, title):
        assert title in self.get_text(self.TITLE_ELE)

    def click_option_under_messaging_tab(self, option):
        messaging_tab = self.wait_for_element(self.MESSAGING_TAB)
        self.click_element(self.MESSAGING_TAB)
        options = messaging_tab.find_elements(By.XPATH, "//li//a")
        for each in options:
            if option in each.text:
                self.click_element(each)
                break
        time.sleep(2)
        self.verify_text_in_url("/messaging")

    def verify_breadcrumb_text_present_cchq(self, expected_text):
        breadcrumb_ele = self.wait_for_element(self.BREADCRUMB_CONTAINER)
        breadcrumb_items = breadcrumb_ele.find_elements(By.TAG_NAME, "li")
        breadcrumb_texts = [item.text.strip() for item in breadcrumb_items]
        assert any(expected_text in text for text in breadcrumb_texts), (
            f"Expected breadcrumb '{expected_text}' not found. "
            f"Actual breadcrumbs: {breadcrumb_texts}"
        )

    def select_app_under_applications_tab(self, app):
        applications_tab = self.wait_for_element(self.APPLICATIONS_TAB)
        self.click_element(self.APPLICATIONS_TAB)
        options = applications_tab.find_elements(By.XPATH, "//li//a")
        for each in options:
            if app in each.text:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", each)
                time.sleep(1)
                each.click()
                break
        time.sleep(2)
        self.wait_for_page_to_load()
        self.verify_text_in_url("/apps/view")

    def verify_app_present_under_applications_tab(self, app):
        applications_tab = self.wait_for_element(self.APPLICATIONS_TAB)
        self.click_element(self.APPLICATIONS_TAB)
        options = applications_tab.find_elements(By.XPATH, "//li//a")
        for each in options:
            if app in each.text:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", each)
                time.sleep(1)
                assert app in each.text, f"{app} not found under applications tab"
                print(f"{app} present under applications tab")
                break
        self.click_element(self.APPLICATIONS_TAB)