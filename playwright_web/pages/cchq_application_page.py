from datetime import datetime

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class CCHQApplicationPage(BasePage):
    SIDEBAR_SETTINGS_ICON = locators.get("cchq_application_page", "sidebar_settings_icon")
    SETTINGS_TAB_BY_NAME = locators.get("cchq_application_page", "settings_tab_by_name")
    COPY_APP_TO_PROJECT_DROPDOWN = locators.get("cchq_application_page", "copy_app_to_project_dropdown")
    NAME_INPUT = locators.get("cchq_application_page", "name_input")
    COPY_BUTTON = locators.get("cchq_application_page", "copy_button")
    MAKE_NEW_VERSION_BUTTON = locators.get("cchq_application_page", "make_new_version_button")
    RELEASED_BUTTON = locators.get("cchq_application_page", "released_button")

    def click_sidebar_settings_icon(self):
        self.click(self.SIDEBAR_SETTINGS_ICON)
        self.page.wait_for_load_state("load")
        assert "/settings/" in self.page.url

    def click_tab_by_name_in_application_settings(self, tab_name):
        tab_selector = self.SETTINGS_TAB_BY_NAME.format(tab_name=tab_name)
        self.click(tab_selector)
        tab = self.page.locator(tab_selector).first
        assert "active" in (tab.get_attribute("class") or "")

    def select_copy_app_to_project_dropdown(self, value):
        self.select_by_visible_text(self.COPY_APP_TO_PROJECT_DROPDOWN, value)

    def _enter_app_name(self, prefix):
        timestamp = datetime.now().strftime("[%d/%m/%Y : %H:%M]")
        full_name = f"{prefix} {timestamp}"
        self.page.locator(self.NAME_INPUT).first.fill(full_name)
        self.page.locator(self.NAME_INPUT).first.press("Tab")
        self.page.wait_for_timeout(5000)
        return full_name

    def click_copy_button(self):
        self.scroll_into_view(self.COPY_BUTTON)
        self.page.locator(self.COPY_BUTTON).first.click(force=True)
        self.page.wait_for_load_state("load")
        assert "/apps/view" in self.page.url
        self.page.wait_for_timeout(5000)

    def click_make_new_version_button(self):
        self.click(self.MAKE_NEW_VERSION_BUTTON)
        self.click(self.RELEASED_BUTTON)

    def create_copy_of_learn_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        project = "connectqa-automation-prod" if "www" in self.page.url else "connectqa-automation"
        self.select_copy_app_to_project_dropdown(project)
        learn_app_full_name = self._enter_app_name("Learn App")
        self.click_copy_button()
        self.click_make_new_version_button()
        return learn_app_full_name

    def create_copy_of_delivery_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        project = "connectqa-automation-prod" if "www" in self.page.url else "connectqa-automation"
        self.select_copy_app_to_project_dropdown(project)
        delivery_app_full_name = self._enter_app_name("Delivery App")
        self.click_copy_button()
        self.click_make_new_version_button()
        return delivery_app_full_name
