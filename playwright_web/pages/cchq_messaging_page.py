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

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
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

    SIDEBAR_LINK = locators.get("cchq_messaging_page", "sidebar_link")
    ADD_KEYWORD_BTN = locators.get("cchq_messaging_page", "add_keyword_btn")
    KEYWORD_INPUT = locators.get("cchq_messaging_page", "keyword_input")
    KEYWORD_DESCRIPTION_INPUT = locators.get("cchq_messaging_page", "keyword_description_input")
    KEYWORD_SENDER_CONTENT_TYPE = locators.get("cchq_messaging_page", "keyword_sender_content_type")
    KEYWORD_SENDER_MESSAGE = locators.get("cchq_messaging_page", "keyword_sender_message")
    KEYWORD_SURVEY_FORM = locators.get("cchq_messaging_page", "keyword_survey_form")
    KEYWORDS_TABLE = locators.get("cchq_messaging_page", "keywords_table")
    KEYWORDS_ROW_BY_NAME = locators.get("cchq_messaging_page", "keywords_row_by_name")
    KEYWORDS_EMPTY_MSG = locators.get("cchq_messaging_page", "keywords_empty_msg")

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
        self._dialogs_accepted = False

    def _accept_dialogs(self):
        """Auto-accept native confirm() dialogs, registering the handler once.

        Both delete helpers are called more than once per test, and Playwright
        keeps every listener that is registered - a second handler tries to
        accept a dialog the first already handled.
        """
        if not self._dialogs_accepted:
            self.page.on("dialog", lambda dialog: dialog.accept())
            self._dialogs_accepted = True

    # ------------------------------------------------------------------ helpers

    def _wait_loaded(self):
        self.page.wait_for_load_state("load")

    @staticmethod
    def _stamped(name):
        return f"{name} {int(time.time() * 1000)}"

    def _wait_for_url(self, predicate, description, timeout=180):
        """Poll page.url until `predicate(url)` holds.

        Deliberately not page.wait_for_url(): that waits for a *navigation
        event* to reach a load state, so when HQ's save posts and lands on the
        list before the wait registers, it blocks for the whole timeout waiting
        for an event that has already happened - observed as a 180s timeout on a
        save that had plainly succeeded. Polling the URL asks the only question
        that actually matters.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            if predicate(self.page.url):
                return
            self.page.wait_for_timeout(250)
        raise AssertionError(
            f"Timed out after {timeout}s waiting for {description}; URL is still {self.page.url!r}"
        )

    def _type_keys(self, selector, text):
        """Type into a Knockout-bound field with real key events.

        These forms bind with `valueUpdate: 'afterkeydown'`, e.g.

            <input data-bind="value: name, valueUpdate: 'afterkeydown'">
            <button data-bind="enable: basicTabValid">Continue</button>

        Playwright's fill() sets the value without producing keydowns, so the
        observable never updates and Continue stays disabled with the field
        visibly populated - which reads like a product bug and is not one. The
        Selenium original only worked because send_keys fires real keys.
        """
        field = self._locator(selector)
        field.wait_for(state="visible")
        field.click()
        field.clear()
        field.press_sequentially(str(text), delay=20)

    def _fill_token_field(self, selector, values):
        """Type each value into a select2-style token field and commit it.

        The widget is a textarea inside the field's wrapper; typing then pressing
        Enter is what turns the text into a token. fill() alone leaves the text
        uncommitted and the form saves with no recipients.
        """
        field = self._locator(selector)
        field.wait_for(state="visible")
        # The wrapper holds the committed tokens, so it is what proves the value
        # actually took.
        container = field.locator("xpath=ancestor::div[starts-with(@id,'div_id_schedule')][1]")
        for value in values:
            field.click()
            field.type(str(value))
            # Wait for the option to exist rather than guessing at how long it
            # takes to arrive. The dropdown resolves the typed text against an
            # asynchronously loaded list, and Enter pressed before the option
            # exists is silently dropped, leaving the field empty.
            #
            # This used to be a flat 1.5s. That held on prod and lost on staging
            # inside a mid-build send, where the action runs in its own fresh
            # browser context with nothing warmed up: the token never committed,
            # the test failed after the device had already unsubscribed, and the
            # channel was left unsubscribed for every test after it.
            option = self.page.locator(".select2-results__option", has_text=str(value)).first
            try:
                option.wait_for(state="visible", timeout=15_000)
            except PlaywrightTimeoutError:
                # Not every build of the widget renders results the same way, so
                # fall back to the old behaviour rather than failing here - the
                # expect() below is the real check either way.
                self.page.wait_for_timeout(1500)
            field.press("Enter")
            # Verify rather than assume. An uncommitted token leaves a required
            # field blank, and the only symptom is that the form refuses to
            # submit with no visible error - which cost a BrowserStack build to
            # diagnose. A value that never resolves is usually an id that does
            # not exist on this environment.
            expect(container).to_contain_text(
                str(value),
                timeout=15_000,
            )

    # --------------------------------------------------------------- navigation

    def open_messaging_option(self, option):
        """Messaging tab -> the named entry (Conditional Alerts, Broadcasts, Keywords)."""
        self._step(f"open Messaging > {option}")
        # Wait for the page to settle and the nav to exist before clicking. This
        # is often called straight after a reload, and on staging the load can
        # outrun the default 30s click timeout - seen as "waiting for locator
        # #MessagingTab", which reads like a missing element rather than a slow
        # page.
        self._wait_loaded()
        tab = self._locator(self.MESSAGING_TAB)
        expect(tab).to_be_visible(timeout=60_000)
        tab.click()
        self.click(self.MESSAGING_MENU_LINK.format(option=option))
        self._wait_loaded()
        assert "/messaging" in self.page.url, f"Not on a Messaging page: {self.page.url}"

    # -------------------------------------------------------- conditional alerts

    def click_new_conditional_alert_btn(self):
        self.click(self.NEW_CONDITIONAL_ALERT)
        self.page.wait_for_url("**/conditional/add**")

    def click_continue_btn(self, timeout=30):
        """Click the live Continue button, waiting for it to become enabled.

        Two reasons this polls rather than clicking the first match: the wizard
        renders a Continue per step and hides the others, and the live one stays
        disabled until its step's Knockout validity observable turns true, which
        happens after the field bindings fire.
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            for button in self.page.locator(self.CONTINUE_BTN).all():
                if button.is_visible() and button.is_enabled():
                    button.click()
                    return
            self.page.wait_for_timeout(250)
        raise AssertionError(
            f"No enabled 'Continue' button after {timeout}s - the step's required fields are "
            "either unfilled or were populated without firing key events"
        )

    def enter_name_in_conditional_alert(self, name):
        self.cond_alert_full_name = self._stamped(name)
        self._type_keys(self.CONDITIONAL_ALERT_NAME_INPUT, self.cond_alert_full_name)
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
        self._type_keys(self.CASE_PROPERTY_NAME_INPUT, entity_id_value)

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
        # See enter_expire_after: no explicit scroll, for the same reason.
        self._type_keys(self.MESSAGE_INPUT, message)

    def select_survey_form(self, value):
        """Pick the survey form, e.g. 'Delivery App - ETE > Surveys > Survey'.

        Selecting "Connect Survey" re-renders the content panel and then fills
        this dropdown asynchronously, so the element is briefly present but
        detached - scrolling to it raced the re-render and failed with "Element
        is not attached to the DOM". Waiting for it to hold real options is the
        reliable signal, and Playwright scrolls to it on select anyway.
        """
        self.wait_for_select_options_loaded(self.SURVEY_FORM_INPUT)
        self.select_by_visible_text(self.SURVEY_FORM_INPUT, value)

    def enter_expire_after(self, hours):
        # No explicit scroll: _type_keys waits for visibility and clicking
        # scrolls the field into view, whereas a scroll issued during the
        # content panel's re-render hits a detached element.
        self._type_keys(self.EXPIRE_AFTER_INPUT, hours)

    def click_save_btn(self):
        # No explicit scroll: the content panel is still settling when Save
        # first appears, so scrolling to it raced the re-render and failed with
        # "Element is not attached to the DOM" - intermittently, which is worse
        # than always. Waiting for it to be enabled and letting click() scroll
        # is both simpler and stable.
        save = self._locator(self.SAVE_BTN)
        expect(save).to_be_enabled(timeout=60_000)
        save.click()
        # Saving leaves the wizard and returns to the list. Watching for the URL
        # to stop being an /add page is what the original's sleep(50) was
        # standing in for, and it still surfaces a validation error that keeps
        # us on the form - as a timeout naming the URL we are stuck on.
        self._wait_for_url(lambda url: "/add" not in url, "the wizard to leave /add")
        self._wait_loaded()

    def verify_alert_in_list(self, name):
        """Search the alert list for `name` and assert a row exists.

        Searching rather than paging: the list accumulates and the new alert is
        not reliably on the first page.
        """
        self.page.reload()
        self._wait_loaded()
        self._type_keys(self.SEARCH_BOX, name)
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

    def wait_for_alert_list(self, timeout=60_000):
        """Wait until the alert list has actually finished rendering.

        The table body is filled by JS after the load event, so enumerating rows
        straight away sees either nothing or half-rendered rows whose buttons
        detach mid-click - which is what made the delete intermittently time out
        with "element is not enabled ... detached from the DOM". Either a row or
        the explicit "There are no alerts to display" panel means it has settled.
        """
        self.page.wait_for_function(
            """() => {
                if (document.querySelectorAll("table[class*='table'] tbody tr").length > 0) return true;
                return Array.from(document.querySelectorAll('div,p,td'))
                    .some(el => el.textContent.trim().startsWith('There are no alerts to display'));
            }""",
            timeout=timeout,
        )

    def delete_existing_alerts(self, name_prefix, per_alert_timeout=60_000):
        """Delete every alert whose name contains `name_prefix`.

        Deletion is confirmed by a native JS confirm(), so a dialog handler is
        registered for the duration. The row is re-resolved by name on each pass
        rather than held across deletes, because the table re-renders and any
        captured handle goes stale.

        A freshly saved alert spends a while in a non-active state with its
        delete control disabled. Rather than blocking on that, this gives up on
        it after `per_alert_timeout` and leaves it: the next run's pre-test
        cleanup removes it once it has settled, so cleanup is self-healing
        instead of slow.
        """
        self._accept_dialogs()
        deleted = 0
        while True:
            self.wait_for_alert_list()
            rows = self.page.locator(
                "//table[contains(@class,'table')]/tbody/tr"
                f"[td[contains(normalize-space(), \"{name_prefix}\")]]"
            )
            if rows.count() == 0:
                break
            delete_btn = rows.first.locator("td").first.locator("button").first
            try:
                expect(delete_btn).to_be_enabled(timeout=per_alert_timeout)
            except AssertionError:
                self._step(
                    f"'{name_prefix}' alert is not deletable yet (still processing) - "
                    "leaving it for the next run's cleanup"
                )
                break
            delete_btn.click()
            self._wait_loaded()
            deleted += 1
        self._step(f"removed {deleted} existing '{name_prefix}' alert(s)")
        return deleted

    # ---------------------------------------------------------------- broadcasts

    def click_add_broadcast_btn(self):
        self.click(self.ADD_BROADCAST_BTN)
        self.page.wait_for_url("**/broadcasts/add**")

    def enter_broadcast_name(self, name):
        self.broadcast_full_name = self._stamped(name)
        self._type_keys(self.BROADCAST_NAME_INPUT, self.broadcast_full_name)
        return self.broadcast_full_name

    def click_send_broadcast_btn(self):
        self.click(self.SEND_BROADCAST_BTN)
        # Same reason as click_save_btn: poll rather than wait on a navigation
        # event that may already have fired.
        self._wait_for_url(
            lambda url: "/broadcasts/" in url and "/add" not in url,
            "the broadcast form to return to the list",
        )
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

    # ------------------------------------------------------- connect user consent

    REQUEST_CONSENT_BTN = locators.get("cchq_messaging_page", "request_consent_btn")
    CONSENT_RESULT_BANNER = locators.get("cchq_messaging_page", "consent_result_banner")

    def open_user_consent(self):
        """Messaging sidebar -> CONNECT MESSSAGING > User Consent.

        Served from /sms/connect_messaging_user/, and like Keywords it is only
        reachable from the left sidebar, which exists once a Messaging page is
        open. (HQ spells the sidebar heading "CONNECT MESSSAGING".)
        """
        if "/messaging/" not in self.page.url and "/sms/" not in self.page.url:
            self.open_messaging_option("Conditional Alerts")
        self.click(self.SIDEBAR_LINK.format(option="User Consent"))
        self.page.wait_for_url("**/sms/connect_messaging_user/**")
        self._wait_loaded()

    def request_messaging_consent(self):
        """Trigger the bulk consent request and return the banner it reports.

        There is no per-user picker: the action covers every Connect user linked
        to this domain through an opportunity's learn/deliver apps. A worker on
        an opportunity whose apps belong to a different domain is not one of
        them, and the banner then reads "No channels created".

        The banner is the only signal available - the page never lists channels -
        so it is returned rather than asserted on here, letting the caller decide
        whether "created" or "not created" is the expected outcome.
        """
        self.click(self.REQUEST_CONSENT_BTN)
        self._wait_loaded()
        text = ""
        banner = self._locator(self.CONSENT_RESULT_BANNER)
        try:
            banner.wait_for(state="visible", timeout=20_000)
            text = banner.inner_text().strip()
        except Exception:
            text = ""
        if not text:
            # The banner markup is not guaranteed; scan the page for the outcome
            # line instead. Returning "" would let a missed selector look exactly
            # like "the action reported nothing", and the caller decides real
            # behaviour from this string.
            for line in self.page.locator("body").inner_text().splitlines():
                lowered = line.lower()
                if "channel" in lowered and ("created" in lowered or "consent" in lowered):
                    text = line.strip()
                    break
        self._step(f"consent request reported: {text!r}")
        return text

    # ------------------------------------------------------------------ keywords

    KEYWORD_PREFIX = "AUTOKW"

    def open_keywords(self):
        """Messaging sidebar -> Keywords.

        Keywords is not in the Messaging top-nav dropdown and is served from
        /reminders/keywords/ rather than /messaging/, so it is reached from the
        left sidebar - which only renders once a Messaging page is open.
        """
        if "/messaging/" not in self.page.url and "/reminders/" not in self.page.url:
            self.open_messaging_option("Conditional Alerts")
        self.click(self.SIDEBAR_LINK.format(option="Keywords"))
        self.page.wait_for_url("**/reminders/keywords/**")
        self._wait_loaded()

    def wait_for_keyword_list(self, timeout=60_000):
        """Wait for the keyword table to finish binding.

        Same async-render problem as the alert list: rows come from a Knockout
        `foreach: paginatedList`, and the empty-state row is bound on
        `visible: isPaginatedListEmpty`. Either the empty message showing or a
        row carrying its Action controls means binding has run.
        """
        self.page.wait_for_function(
            """() => {
                const tbody = document.querySelector("table[class*='table-striped'] tbody");
                if (!tbody) return false;
                const rows = Array.from(tbody.rows);
                const empty = rows.find(r => r.textContent.includes('You have no keywords'));
                if (empty && empty.offsetParent !== null) return true;
                return rows.some(r => r.offsetParent !== null && r.querySelector('a, button'));
            }""",
            timeout=timeout,
        )

    def click_add_keyword_btn(self):
        self.click(self.ADD_KEYWORD_BTN)
        self.page.wait_for_url("**/keywords/normal/add**")

    def new_keyword_name(self):
        """A short unique token. Keywords are single words, so no spaces."""
        return f"{self.KEYWORD_PREFIX}{int(time.time() * 1000) % 1_000_000}"

    def keyword_content_type_options(self):
        dropdown = self._locator(self.KEYWORD_SENDER_CONTENT_TYPE)
        dropdown.wait_for(state="visible")
        return [text.strip() for text in dropdown.locator("option").all_inner_texts()]

    def verify_keyword_in_list(self, keyword):
        self.wait_for_keyword_list()
        row = self._locator(self.KEYWORDS_ROW_BY_NAME.format(keyword=keyword))
        expect(row).to_be_visible(timeout=60_000)
        self._step(f"keyword '{keyword}' present in the list")

    def create_keyword_with_connect_message(self, keyword=None, message=None):
        """Create a keyword whose reply is a Connect Message.

        Returns (keyword, message) so a later mobile step can send the keyword
        and assert on the exact reply text.
        """
        keyword = keyword or self.new_keyword_name()
        message = message or f"Automation keyword reply {int(time.time() * 1000)}"
        self.click_add_keyword_btn()
        self._type_keys(self.KEYWORD_INPUT, keyword)
        self._type_keys(self.KEYWORD_DESCRIPTION_INPUT, f"Automation keyword {keyword}")
        self.select_by_visible_text(self.KEYWORD_SENDER_CONTENT_TYPE, "Connect Message")
        self._type_keys(self.KEYWORD_SENDER_MESSAGE, message)
        self.click_save_btn()
        self.verify_keyword_in_list(keyword)
        return keyword, message

    def create_keyword_with_connect_survey(self, survey_form, keyword=None):
        """Create a keyword whose reply is a Connect Survey."""
        keyword = keyword or self.new_keyword_name()
        self.click_add_keyword_btn()
        self._type_keys(self.KEYWORD_INPUT, keyword)
        self._type_keys(self.KEYWORD_DESCRIPTION_INPUT, f"Automation keyword {keyword}")
        self.select_by_visible_text(self.KEYWORD_SENDER_CONTENT_TYPE, "Connect Survey")
        # Choosing Connect Survey reveals the form dropdown and fills it
        # asynchronously - same re-render race as the conditional alert.
        self.wait_for_select_options_loaded(self.KEYWORD_SURVEY_FORM)
        self.select_by_visible_text(self.KEYWORD_SURVEY_FORM, survey_form)
        self.click_save_btn()
        self.verify_keyword_in_list(keyword)
        return keyword

    def _first_visible(self, selector):
        """First genuinely visible match, or None.

        The keyword table carries hidden Knockout template rows ("New Items",
        "Deleted Items") that contain the same text as the real row, so taking
        .first silently picks a template whose controls can never be clicked.
        """
        candidates = self.page.locator(selector)
        for index in range(candidates.count()):
            candidate = candidates.nth(index)
            try:
                if candidate.is_visible():
                    return candidate
            except Exception:
                continue
        return None

    def delete_existing_keywords(self, name_prefix=None):
        """Delete every keyword whose name starts with `name_prefix`.

        Two steps, not one: the row's Delete button only opens a Bootstrap modal
        (`data-bs-toggle="modal"`). The link that actually deletes is
        `a.delete-item-confirm` *inside* that modal, so clicking it straight off
        the row fails with "element is not visible" - the modal is still closed.
        """
        name_prefix = name_prefix or self.KEYWORD_PREFIX
        self.open_keywords()
        deleted = 0
        while True:
            self.wait_for_keyword_list()
            row = self._first_visible(
                "//table[contains(@class,'table-striped')]/tbody/tr"
                f"[.//a[starts-with(normalize-space(), \"{name_prefix}\")]]"
                "[.//button[contains(@class,'btn-outline-danger')]]"
            )
            if row is None:
                break
            row.locator("button.btn-outline-danger").first.click()
            confirm = row.locator("a.delete-item-confirm").first
            expect(confirm).to_be_visible(timeout=15_000)
            confirm.click()
            self._wait_loaded()
            # The list re-renders in place after the delete; give the binding a
            # beat before re-reading, or the same row is found again.
            self.page.wait_for_timeout(1500)
            deleted += 1
        self._step(f"removed {deleted} existing '{name_prefix}' keyword(s)")
        return deleted

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
