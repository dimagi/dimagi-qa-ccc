import time

from selenium.webdriver import Keys

from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from datetime import datetime

locators = LocatorLoader("locators/web_locators.yaml", platform="web")


class CCHQApplicationPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    SIDEBAR_SETTINGS_ICON = locators.get("cchq_application_page", "sidebar_settings_icon")
    SETTINGS_TAB_BY_NAME = locators.get("cchq_application_page", "settings_tab_by_name")
    COPY_APP_TO_PROJECT_DROPDOWN = locators.get("cchq_application_page", "copy_app_to_project_dropdown")
    NAME_INPUT = locators.get("cchq_application_page", "name_input")
    COPY_BUTTON = locators.get("cchq_application_page", "copy_button")
    MAKE_NEW_VERSION_BUTTON = locators.get("cchq_application_page", "make_new_version_button")
    RELEASED_BUTTON = locators.get("cchq_application_page", "released_button")

    def click_sidebar_settings_icon(self):
        self.wait_for_element(self.SIDEBAR_SETTINGS_ICON)
        self.click_element(self.SIDEBAR_SETTINGS_ICON)
        self.wait_for_page_to_load()
        self.verify_text_in_url("/settings/")

    def verify_tab_is_active(self, tab_name):
        time.sleep(2)
        by, xpath = self.SETTINGS_TAB_BY_NAME
        tab_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_for_element((by, tab_xpath))
        assert "active" in tab.get_attribute("class")

    def click_tab_by_name_in_application_settings(self, tab_name):
        by, xpath = self.SETTINGS_TAB_BY_NAME
        tab_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_for_element((by, tab_xpath))
        self.click_element(tab)
        self.verify_tab_is_active(tab_name)

    def select_copy_app_to_project_dropdown(self, value):
        self.wait_for_element(self.COPY_APP_TO_PROJECT_DROPDOWN)
        self.select_by_visible_text(self.COPY_APP_TO_PROJECT_DROPDOWN, value)

    def enter_learn_app_name_in_copy_application(self):
        timestamp = datetime.now().strftime("[%d/%m/%Y : %H:%M]")
        self.learn_app_full_name = f"Learn App {timestamp}"
        self.wait_for_element(self.NAME_INPUT)
        self.type(self.NAME_INPUT, self.learn_app_full_name+Keys.TAB)
        time.sleep(5)

    def enter_delivery_app_name_in_copy_application(self):
        timestamp = datetime.now().strftime("[%d/%m/%Y : %H:%M]")
        self.delivery_app_full_name = f"Delivery App {timestamp}"
        self.wait_for_element(self.NAME_INPUT)
        self.type(self.NAME_INPUT, self.delivery_app_full_name)

    def click_copy_button(self):
        self.wait_for_element(self.COPY_BUTTON)
        self.scroll_into_view(self.COPY_BUTTON)
        self.click_element(self.COPY_BUTTON)
        time.sleep(2)
        self.wait_for_page_to_load()
        self.verify_text_in_url("/apps/view")

    def click_make_new_version_button(self):
        self.click_element(self.MAKE_NEW_VERSION_BUTTON)
        time.sleep(2)
        self.wait_for_element(self.RELEASED_BUTTON)
        self.click_element(self.RELEASED_BUTTON)
        time.sleep(2)

    def create_copy_of_learn_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        self.select_copy_app_to_project_dropdown("connetqa-prod")
        self.enter_learn_app_name_in_copy_application()
        self.click_copy_button()
        self.click_make_new_version_button()
        return f"Unreleased - {self.learn_app_full_name}"

    def create_copy_of_delivery_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        self.select_copy_app_to_project_dropdown("connetqa-prod")
        self.enter_delivery_app_name_in_copy_application()
        self.click_copy_button()
        self.click_make_new_version_button()
        return f"Unreleased - {self.delivery_app_full_name}"