"""CommCare HQ Messaging: Conditional Alerts and Broadcasts (CCCT-2671).

Playwright port of pages/web_pages/cchq_messaging_web_page.py, which drives the
HQ side of the Connect messaging tests. Three deliberate departures from the
Selenium original:

1. **No fixed sleeps.** The original spends ~2 minutes per alert in time.sleep()
   (50s after Save, 20s waiting for delivery). Every one of those is replaced by
   a wait on the condition it was standing in for, so a fast run is fast and a
   slow one still passes.
2. **Environment-specific values are arguments, not branches.** The original
   inspects the URL for "staging" to pick the survey form. Resolving the
   environment belongs to the test (the repo convention is an unsuffixed prod key
   with a `_staging` override), so `survey_form` is passed in.
3. **Nothing here touches base_page.py.** That file is modified on the open
   tasking branch (PR #23); keeping this page self-contained avoids a merge
   conflict, at the cost of a few small local helpers.

Keyword methods (TC-KWD-*) are deliberately absent: the Keywords pages have no
legacy locators to carry over and inventing selectors blind would only create
rework. They arrive once the DOM has been inspected.
"""

import time

from playwright.sync_api import expect

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class CCHQMessagingPage(BasePage):
    MESSAGING_TAB = locators.get("cchq_messaging_page", "messaging_tab")
    MESSAGING_MENU_LINK = locators.get("cchq_messaging_page", "messaging_menu_link")

    NEW_CONDITIONAL_ALERT = locators.get("cchq_messaging_page", "new_conditional_alert")
    CONDITIONAL_ALERT_NAME_INPUT = locators.get("cchq_messaging_page", "conditional_alert_name_input")
    CONTINUE_BTN = locators.get("cchq_messaging_page", "continue_btn")
    CASE_TYPE_INPUT = locators.get("cchq_messaging_page", "case_type_input")
    SELECT_A_FILTER_BTN = locators.get("cchq_messaging_page", "select_a_filter_btn")
    CASE_PROPERTY_FILTER_OPTION = locators.get("cchq_messaging_page", "case_property_filter_option")
    CASE_PROPERTY_ENTITY_DROPDOWN = locators.get("cchq_messaging_page", "case_property_entity_dropdown")
    CASE_PROPERTY_EQUALS_DROPDOWN = locators.get("cchq_messaging_page", "case_property_equals_dropdown")
    CASE_PROPERTY_NAME_INPUT = locators.get("cchq_messaging_page", "case_property_name_input")
    ALERTS_LIST_TABLE = locators.get("cchq_messaging_page", "alerts_list_table")
    ALERT_ROW = locators.get("cchq_messaging_page", "alert_row")
    SEARCH_BOX = locators.get("cchq_messaging_page", "search_box")
    SEARCH_BTN = locators.get("cchq_messaging_page", "search_btn")

    RECIPIENT_INPUT = locators.get("cchq_messaging_page", "recipient_input")
    USER_RECIPIENTS_INPUT = locators.get("cchq_messaging_page", "user_recipients_input")
    WHAT_TO_SEND_INPUT = locators.get("cchq_messaging_page", "what_to_send_input")
    MESSAGE_INPUT = locators.get("cchq_messaging_page", "message_input")
    SURVEY_FORM_INPUT = locators.get("cchq_messaging_page", "survey_form_input")
    EXPIRE_AFTER_INPUT = locators.get("cchq_messaging_page", "expire_after_input")
    SAVE_BTN = locators.get("cchq_messaging_page", "save_btn")

    ADD_BROADCAST_BTN = locators.get("cchq_messaging_page", "add_broadcast_btn")
    BROADCAST_NAME_INPUT = locators.get("cchq_messaging_page", "broadcast_name_input")
    SEND_BROADCAST_BTN = locators.get("cchq_messaging_page", "send_broadcast_btn")
    BROADCASTS_TABLE = locators.get("cchq_messaging_page", "broadcasts_table")

    # Fixed names, so a re-run finds and removes its own leftovers instead of
    # accumulating alerts on the domain. The timestamp suffix keeps each run's
    # alert individually identifiable in the list.
    MESSAGE_ALERT_NAME = "Automation Message Alert"
    SURVEY_ALERT_NAME = "Automation Survey Alert"

    def __init__(self, page):
        super().__init__(page)
        self.cond_alert_full_name = None
        self.broadcast_full_name = None

    # ------------------------------------------------------------------ helpers

    def _wait_loaded(self):
        self.page.wait_for_load_state("load")

    @staticmethod
    def _stamped(name):
        return f"{name} {int(time.time() * 1000)}"

    def _fill_token_field(self, selector, values):
        """Type each value into a select2-style token field and commit it.

        The widget is a textarea inside the field's wrapper; typing then pressing
        Enter is what turns the text into a token. fill() alone leaves the text
        uncommitted and the form saves with no recipients.
        """
        field = self._locator(selector)
        field.wait_for(state="visible")
        for value in values:
            field.click()
            field.type(str(value))
            # The dropdown has to resolve the typed text to a real option before
            # Enter will take it - without this the keystroke lands on an empty
            # result list and the token is silently dropped.
            self.page.wait_for_timeout(500)
            field.press("Enter")

    # --------------------------------------------------------------- navigation

    def open_messaging_option(self, option):
        """Messaging tab -> the named entry (Conditional Alerts, Broadcasts, Keywords)."""
        self._step(f"open Messaging > {option}")
        self.click(self.MESSAGING_TAB)
        self.click(self.MESSAGING_MENU_LINK.format(option=option))
        self._wait_loaded()
        assert "/messaging" in self.page.url, f"Not on a Messaging page: {self.page.url}"

    # -------------------------------------------------------- conditional alerts

    def click_new_conditional_alert_btn(self):
        self.click(self.NEW_CONDITIONAL_ALERT)
        self.page.wait_for_url("**/conditional/add**")

    def click_continue_btn(self):
        """Click the one visible, enabled Continue button on the current step.

        The wizard renders a Continue button per step and hides the others, so
        the first match is not reliably the live one.
        """
        for button in self.page.locator(self.CONTINUE_BTN).all():
            if button.is_visible() and button.is_enabled():
                button.click()
                return
        raise AssertionError("No enabled 'Continue' button on this step")

    def enter_name_in_conditional_alert(self, name):
        self.cond_alert_full_name = self._stamped(name)
        self.type(self.CONDITIONAL_ALERT_NAME_INPUT, self.cond_alert_full_name)
        return self.cond_alert_full_name

    def select_case_type(self, value):
        self.select_by_visible_text(self.CASE_TYPE_INPUT, value)

    def select_n_apply_case_property_filter_with_entity_id(self, entity_id_value):
        """Add the 'case property entity_id equals <value>' criterion.

        This value is the join between the alert and the mobile form submission
        that triggers it, so it must be unique per run.
        """
        self.click(self.SELECT_A_FILTER_BTN)
        self.click(self.CASE_PROPERTY_FILTER_OPTION)
        self.select_by_visible_text(self.CASE_PROPERTY_ENTITY_DROPDOWN, "entity_id")
        self.select_by_visible_text(self.CASE_PROPERTY_EQUALS_DROPDOWN, "equals")
        self.type(self.CASE_PROPERTY_NAME_INPUT, str(entity_id_value))

    def select_recipients(self, recipient_types):
        self._fill_token_field(self.RECIPIENT_INPUT, recipient_types)

    def select_user_recipients(self, user_ids):
        self._fill_token_field(self.USER_RECIPIENTS_INPUT, user_ids)

    def select_what_to_send(self, value):
        self._locator(self.WHAT_TO_SEND_INPUT).wait_for(state="visible")
        self.select_by_visible_text(self.WHAT_TO_SEND_INPUT, value)

    def what_to_send_options(self):
        """Every option offered by the 'What to Send' dropdown, as text."""
        dropdown = self._locator(self.WHAT_TO_SEND_INPUT)
        dropdown.wait_for(state="visible")
        return [text.strip() for text in dropdown.locator("option").all_inner_texts()]

    def verify_options_present_in_what_to_send(self, expected):
        actual = self.what_to_send_options()
        missing = [value for value in expected if value not in actual]
        assert not missing, f"'What to Send' is missing {missing}. Offered: {actual}"
        self._step(f"'What to Send' offers {expected}")

    def enter_message(self, message):
        self.scroll_into_view(self.MESSAGE_INPUT)
        self.type(self.MESSAGE_INPUT, message)

    def select_survey_form(self, value):
        self.scroll_into_view(self.SURVEY_FORM_INPUT)
        self.select_by_visible_text(self.SURVEY_FORM_INPUT, value)

    def enter_expire_after(self, hours):
        self.scroll_into_view(self.EXPIRE_AFTER_INPUT)
        self.type(self.EXPIRE_AFTER_INPUT, str(hours))

    def click_save_btn(self):
        self.scroll_into_view(self.SAVE_BTN)
        self.click(self.SAVE_BTN)
        # Saving leaves the wizard and returns to the list. Waiting for the URL to
        # stop being an /add page is what the original's sleep(50) was standing in
        # for, and it fails fast when a validation error keeps us on the form.
        self.page.wait_for_url(lambda url: "/add" not in url, timeout=180_000)
        self._wait_loaded()

    def verify_alert_in_list(self, name):
        """Search the alert list for `name` and assert a row exists.

        Searching rather than paging: the list accumulates and the new alert is
        not reliably on the first page.
        """
        self.page.reload()
        self._wait_loaded()
        self.type(self.SEARCH_BOX, name)
        self.click(self.SEARCH_BTN)
        self._wait_loaded()
        row = self.page.locator(f"//table//td//a[contains(normalize-space(), \"{name}\")]").first
        expect(row).to_be_visible(timeout=60_000)
        self._step(f"conditional alert '{name}' present in the list")

    def create_connect_message_conditional_alert(self, entity_id_value, user_recipients, message=None):
        """Create a Connect Message alert. Returns the message body it will send.

        The body is returned so the mobile half can assert on the exact text
        rather than merely that some message arrived.
        """
        message = message or f"Automation Test Message {int(time.time() * 1000)}"
        self.click_new_conditional_alert_btn()
        self.enter_name_in_conditional_alert(self.MESSAGE_ALERT_NAME)
        self.click_continue_btn()
        self.select_case_type("case")
        self.select_n_apply_case_property_filter_with_entity_id(entity_id_value)
        self.click_continue_btn()
        self.select_what_to_send("Connect Message")
        self.enter_message(message)
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.click_save_btn()
        self.verify_alert_in_list(self.cond_alert_full_name)
        return message

    def create_connect_survey_conditional_alert(
        self, entity_id_value, user_recipients, survey_form, expire_after_hours=1
    ):
        """Create a Connect Survey alert.

        survey_form is the environment's form path, e.g.
        'Delivery App - ETE > Surveys > Survey' on prod.
        """
        self.click_new_conditional_alert_btn()
        self.enter_name_in_conditional_alert(self.SURVEY_ALERT_NAME)
        self.click_continue_btn()
        self.select_case_type("case")
        self.select_n_apply_case_property_filter_with_entity_id(entity_id_value)
        self.click_continue_btn()
        self.select_what_to_send("Connect Survey")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.select_survey_form(survey_form)
        self.enter_expire_after(expire_after_hours)
        self.click_save_btn()
        self.verify_alert_in_list(self.cond_alert_full_name)

    def open_new_alert_and_read_what_to_send_options(self):
        """Walk far enough into the wizard for 'What to Send' to render, and read it.

        The dropdown only exists on the content step, so the name and case type
        have to be filled in first even though this asserts nothing about them.
        """
        self.click_new_conditional_alert_btn()
        self.enter_name_in_conditional_alert("Sample Test")
        self.click_continue_btn()
        self.select_case_type("case")
        self.click_continue_btn()
        return self.what_to_send_options()

    def delete_existing_alerts(self, name_prefix):
        """Delete every active alert whose name contains `name_prefix`.

        Deletion is confirmed by a native JS confirm(), so a dialog handler is
        registered for the duration. Rows are re-read after each delete: the
        table re-renders and previously captured handles go stale.
        """
        self.page.on("dialog", lambda dialog: dialog.accept())
        deleted = 0
        while True:
            deleted_any = False
            for row in self.page.locator(self.ALERT_ROW).all():
                try:
                    name = row.locator("td").nth(1).inner_text().strip()
                    status = row.locator("td").nth(3).inner_text().strip().lower()
                except Exception:
                    continue
                if name_prefix not in name or status != "active":
                    continue
                delete_btn = row.locator("td").nth(0).locator("button").first
                delete_btn.scroll_into_view_if_needed()
                delete_btn.click()
                self._wait_loaded()
                deleted += 1
                deleted_any = True
                break
            if not deleted_any:
                break
        self._step(f"removed {deleted} existing '{name_prefix}' alert(s)")
        return deleted

    # ---------------------------------------------------------------- broadcasts

    def click_add_broadcast_btn(self):
        self.click(self.ADD_BROADCAST_BTN)
        self.page.wait_for_url("**/broadcasts/add**")

    def enter_broadcast_name(self, name):
        self.broadcast_full_name = self._stamped(name)
        self.type(self.BROADCAST_NAME_INPUT, self.broadcast_full_name)
        return self.broadcast_full_name

    def click_send_broadcast_btn(self):
        self.click(self.SEND_BROADCAST_BTN)
        self.page.wait_for_url("**/broadcasts/**", timeout=180_000)
        self._wait_loaded()

    def verify_broadcast_in_list(self, name):
        table = self._locator(self.BROADCASTS_TABLE)
        table.wait_for(state="visible", timeout=60_000)
        row = table.locator(f"//tr//td//a[normalize-space()=\"{name}\"]").first
        expect(row).to_be_visible(timeout=60_000)
        self._step(f"broadcast '{name}' present in the list")

    def open_new_broadcast_and_read_what_to_send_options(self):
        self.click_add_broadcast_btn()
        return self.what_to_send_options()

    def create_broadcast_with_connect_message(self, user_recipients, message=None):
        """Send a Connect Message broadcast. Returns the body it sent."""
        message = message or f"Test Connect Message Broadcast {int(time.time() * 1000)}"
        self.click_add_broadcast_btn()
        self.enter_broadcast_name("Connect Message Broadcast")
        self.select_what_to_send("Connect Message")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.enter_message(message)
        self.click_send_broadcast_btn()
        self.verify_broadcast_in_list(self.broadcast_full_name)
        return message

    def create_broadcast_with_connect_survey(self, user_recipients, survey_form, expire_after_hours=1):
        self.click_add_broadcast_btn()
        self.enter_broadcast_name("Connect Survey Broadcast")
        self.select_what_to_send("Connect Survey")
        self.select_recipients(["Users"])
        self.select_user_recipients(user_recipients)
        self.select_survey_form(survey_form)
        self.enter_expire_after(expire_after_hours)
        self.click_send_broadcast_btn()
        self.verify_broadcast_in_list(self.broadcast_full_name)
