"""CommCare HQ Web Apps - submit a delivery form AS a Connect worker ("Log in as").

Used to seed visits for the one-way review tests (VV_31-35): Connect/PersonalID workers
authenticate to HQ with a token we can't mint without a device, but Web Apps' "Log in as"
needs no worker credential. Submissions made this way are attributed to the worker's
HQ user id, which is what Connect keys visits on.
"""

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class WebAppsPage(BasePage):
    RESTORE_AS_TILE = locators.get("cchq_web_apps_page", "restore_as_tile")
    FILTER_WORKERS = locators.get("cchq_web_apps_page", "filter_workers_input")
    LOGIN_AS_CONFIRM = locators.get("cchq_web_apps_page", "login_as_confirm")
    WORKING_AS_BANNER = locators.get("cchq_web_apps_page", "working_as_banner")
    APP_TILE = locators.get("cchq_web_apps_page", "app_tile_by_name")
    MENU_ENTRY = locators.get("cchq_web_apps_page", "menu_entry_by_text")
    NAME_TEXTAREA = locators.get("cchq_web_apps_page", "question_name_textarea")
    ID_INPUT = locators.get("cchq_web_apps_page", "question_id_input")
    GPS_MAP = locators.get("cchq_web_apps_page", "gps_map")
    GPS_SEARCH_INPUT = locators.get("cchq_web_apps_page", "gps_search_input")
    GPS_SEARCH_BUTTON = locators.get("cchq_web_apps_page", "gps_search_button")
    GPS_UNSET = locators.get("cchq_web_apps_page", "gps_unset_label")
    SUBMIT = locators.get("cchq_web_apps_page", "form_submit_button")
    SUBMITTED = locators.get("cchq_web_apps_page", "form_submitted_message")

    def open(self, hq_url, domain):
        self._step(f"Open Web Apps for {domain}")
        self.page.goto(f"{hq_url}/a/{domain}/cloudcare/apps/v2/")
        self.page.wait_for_load_state("load")
        self.page.locator(self.RESTORE_AS_TILE).first.wait_for(state="visible", timeout=60000)

    def log_in_as(self, worker_username):
        """Web Apps -> 'Log in as' -> filter -> pick the worker -> confirm. Filtering needs
        Enter (typing alone leaves the full list), and picking a row opens a confirm dialog."""
        self._step(f"Log in as {worker_username}")
        self.page.locator(self.RESTORE_AS_TILE).first.click()
        box = self.page.locator(self.FILTER_WORKERS).first
        box.wait_for(state="visible", timeout=20000)
        box.fill(worker_username)
        box.press("Enter")
        self.page.get_by_text(worker_username, exact=False).first.click()
        self.page.locator(self.LOGIN_AS_CONFIRM).first.click()
        self.page.locator(self.WORKING_AS_BANNER).first.wait_for(state="visible", timeout=30000)

    def open_form(self, app_name, module, form):
        """Navigate to the form from wherever Web Apps currently is: the app list (first
        time) or inside the app (after a previous submit returns to its menu)."""
        self._step(f"Open {app_name} > {module} > {form}")
        tile = self.page.locator(self.APP_TILE.format(name=app_name)).first
        try:
            tile.wait_for(state="visible", timeout=5000)
            tile.click()
        except PlaywrightTimeoutError:
            pass  # already inside the app
        for entry in (module, form):
            if self.page.locator(self.NAME_TEXTAREA).first.is_visible():
                break
            try:
                self._click_first_visible(self.MENU_ENTRY.format(text=entry), timeout_ms=8000)
            except AssertionError:
                continue  # e.g. already inside the module, so its label isn't a menu entry
        self.page.locator(self.NAME_TEXTAREA).first.wait_for(state="visible", timeout=30000)

    def _click_first_visible(self, selector, timeout_ms=30000):
        import time

        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            matches = self.page.locator(selector)
            for i in range(matches.count()):
                if matches.nth(i).is_visible():
                    matches.nth(i).click()
                    return
            self.page.wait_for_timeout(500)
        raise AssertionError(f"No visible element for {selector}")

    def fill_delivery_form(self, entity_name, entity_id, location_query):
        """name (required textarea), id (number) and a GPS point. Clicking the map does not
        set the coordinates (they stay '??.?????'), so search a place instead."""
        self._step(f"Fill delivery form: name={entity_name!r} id={entity_id} location={location_query!r}")
        self.page.locator(self.NAME_TEXTAREA).first.fill(entity_name)
        self.page.locator(self.ID_INPUT).first.fill(str(entity_id))
        self.page.locator(self.GPS_SEARCH_INPUT).first.fill(location_query)
        self._click_first_visible(self.GPS_SEARCH_BUTTON)
        self.page.locator(self.GPS_UNSET).first.wait_for(state="hidden", timeout=20000)

    def submit(self):
        self._step("Submit delivery form")
        self._click_first_visible(self.SUBMIT)
        # The form closes (Submit disappears) as soon as it is sent, but the POST to HQ can
        # still be in flight: closing the page right after the LAST submit dropped the final
        # visit (3 of 4 arrived in Connect, prod 2026-10-16). Wait for HQ's confirmation
        # message, falling back to the network settling.
        self.page.locator(self.SUBMIT).first.wait_for(state="hidden", timeout=30000)
        try:
            self.page.locator(self.SUBMITTED).first.wait_for(state="visible", timeout=20000)
        except PlaywrightTimeoutError:
            self.page.wait_for_load_state("networkidle")
            self.page.wait_for_timeout(5000)
