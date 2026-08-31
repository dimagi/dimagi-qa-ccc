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
        # The button's presence is guaranteed by _open_copy_form; still wait for it
        # to be actionable so a slow render surfaces here rather than as a bare click
        # timeout, and confirm the copy by the resulting navigation.
        button = self.page.locator(self.COPY_BUTTON).first
        button.wait_for(state="visible", timeout=60000)
        self.scroll_into_view(self.COPY_BUTTON)
        button.click(force=True)
        self.page.wait_for_url("**/apps/view/**", timeout=60000)
        self.page.wait_for_timeout(5000)

    def click_make_new_version_button(self):
        self.click(self.MAKE_NEW_VERSION_BUTTON)
        self.click(self.RELEASED_BUTTON)

    def _open_copy_form(self):
        """Open the app-settings Actions tab and wait until the copy form's Copy
        button is actually rendered.

        The Actions-tab content loads asynchronously and is slow on staging, so the
        Copy button can be absent for tens of seconds - the historical cause of the
        setup flow's intermittent 30s click timeout. Retrying the tab open (a
        read-only action - it copies nothing) until the button appears removes the
        flake without risking a duplicate copy.
        """
        last_error = None
        for attempt in range(3):
            try:
                self.click_sidebar_settings_icon()
                self.click_tab_by_name_in_application_settings("Actions")
                self.page.wait_for_load_state("networkidle")
                self.page.locator(self.COPY_BUTTON).first.wait_for(state="visible", timeout=30000)
                return
            except Exception as error:  # noqa: BLE001 - ret/reload on any readiness failure
                last_error = error
                self._step(f"Copy form not ready (attempt {attempt + 1}/3) - reloading")
                self.page.reload(wait_until="load")
                self.page.wait_for_timeout(2000)
        raise AssertionError(f"App copy form (Actions tab) never became ready: {last_error}")

    def _create_copy(self, prefix):
        self._open_copy_form()
        project = "connectqa-automation-prod" if "www" in self.page.url else "connectqa-automation"
        self.select_copy_app_to_project_dropdown(project)
        full_name = self._enter_app_name(prefix)
        self.click_copy_button()
        self.click_make_new_version_button()
        return full_name

    def create_copy_of_learn_app(self):
        return self._create_copy("Learn App")

    def create_copy_of_delivery_app(self):
        return self._create_copy("Delivery App")
