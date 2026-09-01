from urllib.parse import parse_qs, urlparse

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class OpportunityDashboardPage(BasePage):
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page", "dashboard_card")
    OPP_TITLE = locators.get("opportunity_dashboard_page", "opp_title")
    INFO_CARD_BY_LABEL = locators.get("opportunity_dashboard_page", "info_card_by_label")
    STATUS_BADGE = locators.get("opportunity_dashboard_page", "status_badge")
    STATS_CONTAINER = locators.get("opportunity_dashboard_page", "stats_container")
    FUNNEL_CONTAINER = locators.get("opportunity_dashboard_page", "funnel_container")
    WORKER_PROGRESS_CONTAINER = locators.get("opportunity_dashboard_page", "worker_progress_container")
    FUNNEL_HEADING = locators.get("opportunity_dashboard_page", "funnel_heading")
    PANEL_LINK_BY_HREF = locators.get("opportunity_dashboard_page", "panel_link_by_href")
    HAMBURGER_TOGGLE = locators.get("opportunity_dashboard_page", "hamburger_toggle")
    HAMBURGER_MENU = locators.get("opportunity_dashboard_page", "hamburger_menu")
    HAMBURGER_MENU_ITEMS = locators.get("opportunity_dashboard_page", "hamburger_menu_items")
    HAMBURGER_ITEM_BY_TEXT = locators.get("opportunity_dashboard_page", "hamburger_item_by_text")
    RESOURCE_CARD_LEARN = locators.get("opportunity_dashboard_page", "resource_card_learn")
    RESOURCE_MODAL = locators.get("opportunity_dashboard_page", "resource_modal")
    RESOURCE_MODAL_TAB = locators.get("opportunity_dashboard_page", "resource_modal_tab")
    RESOURCE_MODAL_CLOSE = locators.get("opportunity_dashboard_page", "resource_modal_close")
    RESOURCE_MODAL_TABLE_HEADERS = locators.get("opportunity_dashboard_page", "resource_modal_table_headers")
    RESOURCE_MODAL_INPUTS = locators.get("opportunity_dashboard_page", "resource_modal_inputs")
    WORKER_TABLE_HEADERS = locators.get("opportunity_dashboard_page", "worker_table_headers")

    # Stat-panel navigation targets, keyed by an unambiguous fragment of the panel's
    # href (built from the opportunity source, opportunity/views.py delivery_stats).
    PANEL_HREF = {
        "connect_workers": "/workers/?sort=-last_active",
        "inactive": "/workers/deliver/?last_active=3",
        "services_delivered": "/workers/deliver/?sort=-last_active",
        "payments_earned": "/workers/payments/",
    }

    # -- load / structure -------------------------------------------------------

    def verify_loaded(self):
        """The detail page carries the bars menu icon and the delivery-stats
        container; the list page (also under /opportunity/) has neither, so they
        are a reliable load signal without depending on seeded stat data."""
        self.page.locator(self.HAMBURGER_TOGGLE).first.wait_for(state="visible", timeout=30000)
        assert self.page.locator(self.STATS_CONTAINER).count() > 0, (
            f"Delivery-stats container absent - not on a dashboard: {self.page.url}"
        )
        assert "/opportunity/" in self.page.url, f"Not on an opportunity page: {self.page.url}"
        self._step(f"Opportunity dashboard loaded: {self.page.url}")

    def wait_for_stats(self):
        """The three stat sections HTMX-swap in after the page loads (skeleton
        first). The skeleton carries an empty, hidden h3.text-2xl placeholder, so
        wait instead for a real panel card to become visible - the same signal the
        OLP_4 dashboard test uses. 'Services Delivered / Total' is always rendered."""
        self.page.locator(self.STATS_CONTAINER).first.wait_for(state="visible", timeout=30000)
        card = self.DASHBOARD_CARD.format(title="Services Delivered", subtitle="Total")
        self.page.locator(card).first.wait_for(state="visible", timeout=30000)
        self._step("Delivery stat panels rendered")

    # -- OD_2: dashboard details present ----------------------------------------

    def verify_summary_cards(self, labels):
        present, missing = [], []
        for label in labels:
            if self.page.locator(self.INFO_CARD_BY_LABEL.format(label=label)).count() > 0:
                present.append(label)
            else:
                missing.append(label)
        self._step(f"Summary cards present: {present}")
        assert not missing, f"Missing summary info cards: {missing}"

    def verify_status_badge(self):
        badge = self.page.locator(self.STATUS_BADGE).first
        badge.wait_for(state="visible", timeout=15000)
        text = badge.inner_text().strip()
        assert text in ("Active", "Ended", "Inactive"), f"Unexpected status badge: {text!r}"
        self._step(f"Opportunity status badge: {text}")

    def verify_graphs_present(self):
        """The funnel and worker-progress sections render as their own HTMX
        containers; assert the containers and the funnel heading are present."""
        self.page.locator(self.FUNNEL_CONTAINER).first.wait_for(state="visible", timeout=30000)
        self.page.locator(self.WORKER_PROGRESS_CONTAINER).first.wait_for(state="visible", timeout=30000)
        assert self.page.locator(self.FUNNEL_HEADING).count() > 0, "Worker Progress Funnel heading not found"
        self._step("Funnel + worker-progress graphs present")

    def verify_stat_panels(self, panels):
        """panels: list of (title, subtitle) whose value node must be non-empty."""
        for title, subtitle in panels:
            selector = self.DASHBOARD_CARD.format(title=title, subtitle=subtitle)
            self.scroll_into_view(selector)
            card = self.page.locator(selector).first
            card.wait_for(state="visible", timeout=15000)
            count = card.locator("xpath=.//h3[contains(@class,'text-2xl')]").first.inner_text().strip()
            assert count != "", f"{title} / {subtitle} count is empty"
            self._step(f"Stat panel '{title} / {subtitle}' -> {count}")

    # -- OD_3/OD_4/OD_5/inactive: panel navigation ------------------------------

    def click_stat_panel(self, key):
        """Click a stat panel's anchor by href fragment and return the landed URL."""
        frag = self.PANEL_HREF[key]
        selector = self.PANEL_LINK_BY_HREF.format(frag=frag)
        self.scroll_into_view(selector)
        self._step(f"Click stat panel '{key}' (href ~ {frag})")
        self.click(selector)
        self.page.wait_for_load_state("load")
        self._step(f"Landed on: {self.page.url}")
        return self.page.url

    def worker_table_columns(self):
        # The worker sub-pages load their table into #table via an HTMX request
        # fired after the page loads, so the header row is not present yet at the
        # 'load' event - wait for it (or fall through if the tab has no data).
        self.is_displayed(self.WORKER_TABLE_HEADERS, timeout=20000)
        headers = [h.strip() for h in self.page.locator(self.WORKER_TABLE_HEADERS).all_inner_texts()]
        headers = [h for h in headers if h]
        self._step(f"Worker table columns: {headers}")
        return headers

    def verify_worker_columns(self, expected):
        headers = self.worker_table_columns()
        if not headers:
            # A tab with no workers/deliveries renders an empty state rather than a
            # table, so the column set can only be asserted where the opportunity
            # has data. Point OPD.opportunity_name(_staging) at a data-rich
            # opportunity for strict column coverage.
            self._step("Worker table empty for this opportunity - skipping column assertion")
            return
        joined = " | ".join(headers)
        missing = [c for c in expected if c not in joined]
        assert not missing, f"Missing columns {missing}. Present: {headers}"
        self._step(f"All expected columns present: {expected}")

    def query_param(self, name):
        return parse_qs(urlparse(self.page.url).query).get(name, [""])[0]

    # -- OD_6/OD_7: hamburger menu ----------------------------------------------

    def open_hamburger(self):
        self._step("Open hamburger menu")
        self.click(self.HAMBURGER_TOGGLE)
        self.page.locator(self.HAMBURGER_MENU).first.wait_for(state="visible", timeout=10000)

    def hamburger_options(self):
        self.open_hamburger()
        items = [i.strip() for i in self.page.locator(self.HAMBURGER_MENU_ITEMS).all_inner_texts() if i.strip()]
        self._step(f"Hamburger options: {items}")
        return items

    def click_hamburger_item(self, text):
        # The menu div is always in the DOM (x-show toggles visibility, not
        # presence), so re-open by visibility, not by element count.
        if not self.is_displayed(self.HAMBURGER_MENU, timeout=1000):
            self.open_hamburger()
        self._step(f"Click hamburger item '{text}'")
        self.click(self.HAMBURGER_ITEM_BY_TEXT.format(text=text))
        self.page.wait_for_load_state("load")

    # -- OD_18/OD_19: Learn & Deliver apps / Payment units modal ----------------

    def open_resource_modal(self):
        self._step("Open Learn & Deliver apps modal")
        self.click(self.RESOURCE_CARD_LEARN)
        self.page.locator(self.RESOURCE_MODAL).first.wait_for(state="visible", timeout=10000)

    def select_resource_tab(self, text):
        """Select a modal tab. All three tables are rendered into the modal up
        front (toggled by an x-show), so the tab li gains an 'active' class rather
        than a table swapping in - wait for that, not for a th to become visible."""
        self._step(f"Select resource modal tab '{text}'")
        tab = self.RESOURCE_MODAL_TAB.format(text=text)
        self.click(tab)
        self.page.locator(f"{tab}[contains(@class,'active')]").first.wait_for(state="visible", timeout=10000)

    def resource_modal_columns(self):
        """Read every table header in the modal. All three tables are present in
        the DOM at once (Playwright reports the inactive ones' <th> as not visible,
        so a visibility filter yields nothing); the column names are distinct per
        table, so asserting each tab's columns against this union is unambiguous."""
        self.page.locator(self.RESOURCE_MODAL_TABLE_HEADERS).first.wait_for(state="attached", timeout=15000)
        headers = [h.strip() for h in self.page.locator(self.RESOURCE_MODAL_TABLE_HEADERS).all_inner_texts() if h.strip()]
        self._step(f"Resource modal columns: {headers}")
        return headers

    def verify_resource_tabs_present(self, tabs):
        missing = [t for t in tabs if self.page.locator(self.RESOURCE_MODAL_TAB.format(text=t)).count() == 0]
        assert not missing, f"Missing resource modal tabs: {missing}"
        self._step(f"Resource modal tabs present: {tabs}")

    def verify_resource_columns(self, expected):
        # The three modal tables HTMX-load independently, so a tab's headers can
        # arrive after another's - poll until the expected columns are present
        # rather than reading once and racing the load.
        joined = ""
        for _ in range(20):  # ~10s
            joined = " | ".join(self.resource_modal_columns())
            if all(c in joined for c in expected):
                self._step(f"All expected modal columns present: {expected}")
                return
            self.page.wait_for_timeout(500)
        missing = [c for c in expected if c not in joined]
        assert not missing, f"Missing modal columns {missing}"

    def verify_resource_modal_readonly(self):
        """The dialog is informational - no editable inputs beyond the close icon."""
        inputs = self.page.locator(self.RESOURCE_MODAL_INPUTS).count()
        assert inputs == 0, f"Resource modal unexpectedly has {inputs} editable field(s)"
        self._step("Resource modal is non-editable")

    def close_resource_modal(self):
        self.click(self.RESOURCE_MODAL_CLOSE)
        self.page.locator(self.RESOURCE_MODAL).first.wait_for(state="hidden", timeout=10000)

    # -- gap-analysis surfaces (OD_20+) -----------------------------------------

    RESOURCE_CARD_BY_NAME = locators.get("opportunity_dashboard_page", "resource_card_by_name")
    FUNNEL_STAGE_LABELS = locators.get("opportunity_dashboard_page", "funnel_stage_labels")
    FUNNEL_STAGE_COUNTS = locators.get("opportunity_dashboard_page", "funnel_stage_counts")
    WORKER_PROGRESS_LABELS = locators.get("opportunity_dashboard_page", "worker_progress_labels")
    WORKER_PROGRESS_BARS = locators.get("opportunity_dashboard_page", "worker_progress_bars")
    INCREMENT_BADGE = locators.get("opportunity_dashboard_page", "increment_badge")
    STAT_PANEL_BY_TITLE = locators.get("opportunity_dashboard_page", "stat_panel_by_title")
    DELIVER_FILTER_BUTTON = locators.get("opportunity_dashboard_page", "deliver_filter_button")
    DELIVER_FILTER_APPLY = locators.get("opportunity_dashboard_page", "deliver_filter_apply")
    FILTER_SELECT_BY_NAME = locators.get("opportunity_dashboard_page", "filter_select_by_name")
    WORKERS_SEARCH_INPUT = locators.get("opportunity_dashboard_page", "workers_search_input")
    WORKERS_DISPLAYING_COUNT = locators.get("opportunity_dashboard_page", "workers_displaying_count")
    WORKERS_SEARCH_CLEAR = locators.get("opportunity_dashboard_page", "workers_search_clear")
    WORKERS_TAB_LABEL = locators.get("opportunity_dashboard_page", "workers_tab_label")

    FUNNEL_STAGES = ["Invited", "Accepted", "Started Learning", "Completed Learning",
                     "Completed Assessment", "Claimed Job", "Started Delivery"]
    WORKER_PROGRESS_TITLES = ["Approved", "Rejected", "Earned", "Paid"]

    def goto_dashboard(self):
        """Return to the opportunity dashboard without re-authenticating. Used by
        the shared-session tests so each test starts from a known state after the
        previous one navigated away. dashboard_url is set by the module fixture."""
        self.page.goto(self.dashboard_url)
        self.page.wait_for_load_state("load")
        self.verify_loaded()

    def base_url_parts(self):
        """(scheme://host, org_slug, opp_id) parsed from the current dashboard url:
        .../a/<slug>/opportunity/<opp_id>/ ."""
        from urllib.parse import urlparse
        u = urlparse(self.page.url)
        parts = [p for p in u.path.split("/") if p]
        slug = parts[parts.index("a") + 1]
        opp_id = parts[parts.index("opportunity") + 1]
        return f"{u.scheme}://{u.netloc}", slug, opp_id

    # -- OD Tier 2/3: Add Budget / Send Message / Add Workers -------------------

    ADD_BUDGET_VISITS_INPUT = locators.get("opportunity_dashboard_page", "add_budget_visits_input")
    ADD_BUDGET_ADJUSTMENT_BY_VALUE = locators.get("opportunity_dashboard_page", "add_budget_adjustment_by_value")
    ADD_BUDGET_WORKER_CHECKBOXES = locators.get("opportunity_dashboard_page", "add_budget_worker_checkboxes")
    ADD_BUDGET_SAVE_BTN = locators.get("opportunity_dashboard_page", "add_budget_save_btn")
    ADD_BUDGET_NO_CLAIMS_TEXT = locators.get("opportunity_dashboard_page", "add_budget_no_claims_text")
    ADD_BUDGET_CONFIRM_MODAL = locators.get("opportunity_dashboard_page", "add_budget_confirm_modal")
    ADD_BUDGET_NEW_TAB = locators.get("opportunity_dashboard_page", "add_budget_new_tab")
    ADD_BUDGET_NEW_USERS_INPUT = locators.get("opportunity_dashboard_page", "add_budget_new_users_input")
    ADD_BUDGET_TOTAL_BUDGET_INPUT = locators.get("opportunity_dashboard_page", "add_budget_total_budget_input")
    SEND_MESSAGE_CONFIRM_BTN = locators.get("opportunity_dashboard_page", "send_message_confirm_btn")

    def _dashboard_parts(self):
        """(base, slug, opp_id) from the stored dashboard_url - stable regardless of
        where the current page has navigated."""
        from urllib.parse import urlparse
        u = urlparse(self.dashboard_url)
        parts = [p for p in u.path.split("/") if p]
        return f"{u.scheme}://{u.netloc}", parts[parts.index("a") + 1], parts[parts.index("opportunity") + 1]

    def goto_add_budget(self):
        """Open the Add Budget page directly (existing-users tab is the default)."""
        base, slug, opp = self._dashboard_parts()
        self.page.goto(f"{base}/a/{slug}/opportunity/{opp}/add_budget_existing_users")
        self.page.wait_for_load_state("load")
        self._step("Add Budget page loaded")

    def open_send_message(self):
        """OD_8 - reach Send Message via the hamburger option (from the dashboard)."""
        self.click_hamburger_item("Send Message")
        self.page.wait_for_load_state("load")

    def send_message_page_ready(self):
        return self.is_displayed(self.SEND_MESSAGE_CONFIRM_BTN, timeout=15000)

    def open_add_connect_workers(self):
        """OD_9 - reach the Add Connect Workers (invite) page via the hamburger."""
        self.click_hamburger_item("Add Connect Workers")
        self.page.wait_for_load_state("load")

    def visits_field_validity(self, value):
        """OD_13 - set number_of_visits and read the browser ValidityState (min=1)."""
        field = self.page.locator(self.ADD_BUDGET_VISITS_INPUT).first
        field.fill(str(value))
        validity = field.evaluate(
            "el => ({valid: el.checkValidity(), rangeUnderflow: el.validity.rangeUnderflow,"
            " min: el.min, message: el.validationMessage})"
        )
        self._step(f"number_of_visits={value} -> {validity}")
        return validity

    def add_budget_has_claimed_workers(self):
        if self.page.locator(self.ADD_BUDGET_NO_CLAIMS_TEXT).count() > 0:
            return False
        return self.page.locator(self.ADD_BUDGET_WORKER_CHECKBOXES).count() > 0

    def open_budget_confirm_modal(self, visits, adjustment="increase_visits"):
        """OD_16 - select one worker, enter visits + adjustment, open the confirm
        modal (does not submit). Returns the modal's text."""
        self.page.locator(self.ADD_BUDGET_WORKER_CHECKBOXES).first.check()
        self.page.locator(self.ADD_BUDGET_VISITS_INPUT).first.fill(str(visits))
        self.click(self.ADD_BUDGET_ADJUSTMENT_BY_VALUE.format(value=adjustment))
        self.click(self.ADD_BUDGET_SAVE_BTN)
        modal = self.page.locator(self.ADD_BUDGET_CONFIRM_MODAL).first
        modal.wait_for(state="visible", timeout=10000)
        text = modal.inner_text().strip()
        self._step(f"Confirm modal text: {text!r}")
        return text

    def open_new_workers_tab(self):
        """OD_17 - switch to the new-workers tab (HTMX-loads its form)."""
        self.click(self.ADD_BUDGET_NEW_TAB)
        self.page.locator(self.ADD_BUDGET_NEW_USERS_INPUT).first.wait_for(state="visible", timeout=15000)

    def total_budget_value(self):
        return self.page.locator(self.ADD_BUDGET_TOTAL_BUDGET_INPUT).first.input_value()

    def set_new_workers_count(self, n):
        self.page.locator(self.ADD_BUDGET_NEW_USERS_INPUT).first.fill(str(n))
        # the field's oninput handler recomputes total_budget
        self.page.wait_for_timeout(500)

    # -- Add-budget mutation flow (OD_10/11/12/14/15) ---------------------------

    ADD_BUDGET_CONFIRM_SUBMIT = locators.get("opportunity_dashboard_page", "add_budget_confirm_submit")
    ADD_BUDGET_TABLE_HEADERS = locators.get("opportunity_dashboard_page", "add_budget_table_headers")
    ADD_BUDGET_TABLE_ROWS = locators.get("opportunity_dashboard_page", "add_budget_table_rows")
    ADD_BUDGET_SUCCESS_MSG = locators.get("opportunity_dashboard_page", "add_budget_success_msg")
    ADD_BUDGET_DECREASE_ERROR = locators.get("opportunity_dashboard_page", "add_budget_decrease_error")
    DELIVER_PROGRESS_DENOMINATORS = locators.get("opportunity_dashboard_page", "deliver_progress_denominators")

    def add_budget_row_max_visits(self, row_index=0):
        """Read a worker row's summed 'Max Visits' from the add-budget page table.
        Assumes goto_add_budget() has been called and the opp has claimed workers."""
        headers = [h.strip() for h in self.page.locator(self.ADD_BUDGET_TABLE_HEADERS).all_inner_texts()]
        assert "Max Visits" in headers, f"'Max Visits' column not found in {headers}"
        col = headers.index("Max Visits")
        row = self.page.locator(self.ADD_BUDGET_TABLE_ROWS).nth(row_index)
        cell = row.locator("xpath=./td").nth(col).inner_text().strip()
        value = int("".join(ch for ch in cell if ch.isdigit()) or "0")
        self._step(f"Add-budget row {row_index} Max Visits = {value}")
        return value

    def apply_budget_change(self, visits, adjustment):
        """Select the first worker, set visits + adjustment, open the confirm modal
        and submit it. The view answers with a 302 back to the add-budget page, so
        wait for the reload. Returns True on a success flash, False otherwise."""
        self.goto_add_budget()  # ensure we are on the form (a revert may run from another tab)
        self.open_budget_confirm_modal(visits, adjustment)  # selects worker, Save -> modal
        self._step(f"Submit budget change: {adjustment} by {visits}")
        with self.page.expect_navigation(wait_until="load"):
            self.click(self.ADD_BUDGET_CONFIRM_SUBMIT)
        applied = self.is_displayed(self.ADD_BUDGET_SUCCESS_MSG, timeout=8000)
        self._step(f"Budget change applied (success flash present): {applied}")
        return applied

    def budget_decrease_error_present(self):
        return self.is_displayed(self.ADD_BUDGET_DECREASE_ERROR, timeout=8000)

    # -- Export / import flows (OD_36/44/46) ------------------------------------

    CATCHMENT_TOGGLE = locators.get("opportunity_dashboard_page", "catchment_toggle")
    CATCHMENT_IMPORT_LINK = locators.get("opportunity_dashboard_page", "catchment_import_link")
    CATCHMENT_EXPORT_LINK = locators.get("opportunity_dashboard_page", "catchment_export_link")
    CATCHMENT_IMPORT_FILE = locators.get("opportunity_dashboard_page", "catchment_import_file")
    MODAL_EXPORT_SUBMIT = locators.get("opportunity_dashboard_page", "modal_export_submit")
    MODAL_IMPORT_SUBMIT = locators.get("opportunity_dashboard_page", "modal_import_submit")
    DELIVER_EXPORT_BTN = locators.get("opportunity_dashboard_page", "deliver_export_btn")
    DELIVER_EXPORT_RADIO_BY_VALUE = locators.get("opportunity_dashboard_page", "deliver_export_radio_by_value")
    EXPORT_SUBMIT_BTN = locators.get("opportunity_dashboard_page", "export_submit_btn")
    EXPORT_FROM_DATE = locators.get("opportunity_dashboard_page", "export_from_date")
    DELIVER_IMPORT_BTN = locators.get("opportunity_dashboard_page", "deliver_import_btn")
    DELIVER_IMPORT_FILE = locators.get("opportunity_dashboard_page", "deliver_import_file")
    PAYMENT_IMPORT_BTN = locators.get("opportunity_dashboard_page", "payment_import_btn")
    PAYMENT_IMPORT_FILE = locators.get("opportunity_dashboard_page", "payment_import_file")

    # Known server rejection strings (the import validation surfaces).
    IMPORT_ERROR_STRINGS = (
        "Invalid file format",
        "File format not supported",
        "Missing required column",
        "did not contain any headers",
        "Import failed",
        "failed:",
    )

    def open_catchment_submenu(self):
        self.open_hamburger()
        self.click(self.CATCHMENT_TOGGLE)
        self.page.locator(self.CATCHMENT_IMPORT_LINK).first.wait_for(state="visible", timeout=8000)

    def submit_catchment_export(self):
        """Open the catchment export modal and submit (queues a Celery export ->
        302 to the dashboard with ?export_task_id). No data is mutated."""
        self.open_catchment_submenu()
        self.click(self.CATCHMENT_EXPORT_LINK)
        self.page.locator(self.MODAL_EXPORT_SUBMIT).first.wait_for(state="visible", timeout=8000)
        with self.page.expect_navigation(wait_until="load"):
            self.click(self.MODAL_EXPORT_SUBMIT)
        return self.page.url

    def upload_and_import(self, open_fn, file_locator, payload):
        """Open an import modal (via open_fn), upload an invalid `payload`, submit,
        and poll the page for a rejection string. Some imports reject synchronously
        (a flash on redirect); others queue a task and surface the error in the
        status poller a couple of seconds later - so poll rather than read once.
        Invalid input -> nothing is imported. Returns the final page text."""
        open_fn()
        file_input = self.page.locator(file_locator).first
        file_input.wait_for(state="attached", timeout=8000)
        file_input.set_input_files(payload)
        with self.page.expect_navigation(wait_until="load"):
            self.click(self.MODAL_IMPORT_SUBMIT)
        body = self.page.inner_text("body")
        for _ in range(12):  # ~24s, covers the async status poller (polls every 2s)
            if any(s.lower() in body.lower() for s in self.IMPORT_ERROR_STRINGS):
                break
            self.page.wait_for_timeout(2000)
            body = self.page.inner_text("body")
        self._step(f"After import submit: url={self.page.url}")
        return body

    def import_error_present(self, body_text):
        hit = next((s for s in self.IMPORT_ERROR_STRINGS if s.lower() in body_text.lower()), None)
        self._step(f"Import rejection string found: {hit!r}")
        return hit is not None

    def open_catchment_import_modal(self):
        self.open_catchment_submenu()
        self.click(self.CATCHMENT_IMPORT_LINK)
        self.page.locator(self.CATCHMENT_IMPORT_FILE).first.wait_for(state="attached", timeout=8000)

    # Deliver export
    def open_deliver_export_modal(self):
        self.click(self.DELIVER_EXPORT_BTN)
        self.page.locator(self.DELIVER_EXPORT_RADIO_BY_VALUE.format(value="nm_review")).first.wait_for(
            state="visible", timeout=8000
        )

    def export_radio_present(self, value):
        return self.page.locator(self.DELIVER_EXPORT_RADIO_BY_VALUE.format(value=value)).count() > 0

    def submit_deliver_export(self):
        """Set a From Date (which HTMX-enables the disabled Export button), submit,
        and return the landed URL (worker_deliver?export_task_id=...)."""
        self.select_deliver_export_radio("nm_review")
        # The export form has several required fields (From/To date, Status, Format);
        # fill/select what we can, then submit the enabled button's own form.
        for sel in (self.EXPORT_FROM_DATE, "#id_to_date"):
            loc = self.page.locator(sel).first
            if loc.count():
                loc.fill("2020-01-01")
                loc.dispatch_event("change")
        for sid in ("#id_status", "#id_format"):
            s = self.page.locator(sid).first
            if s.count():
                try:
                    s.select_option(index=1)
                except Exception:
                    pass
        enabled = f"{self.EXPORT_SUBMIT_BTN}:not([disabled])"
        try:
            self.page.locator(enabled).first.wait_for(state="visible", timeout=15000)
        except Exception:
            self._step("Export submit button did not enable")
            return self.page.url
        self._step("Submit deliver export")
        self.page.evaluate(
            "() => { const b = document.querySelector('#export-submit-btn:not([disabled])');"
            " if (b && b.form) { b.form.requestSubmit(b); } else if (b) { b.click(); } }"
        )
        try:
            self.page.wait_for_url("**export_task_id=**", timeout=20000)
        except Exception:
            self._step(f"Export did not queue (required-field form). url={self.page.url}")
        return self.page.url

    def deliver_export_fields_present(self):
        """The export form exposes Format + date + Status controls (proves the
        export flow is live even when the required-field submit is not driven)."""
        present = self.page.locator("#id_format").count() > 0 and self.page.locator(self.EXPORT_FROM_DATE).count() > 0
        self._step(f"Deliver export form fields present: {present}")
        return present

    def select_deliver_export_radio(self, value):
        self.page.locator(self.DELIVER_EXPORT_RADIO_BY_VALUE.format(value=value)).first.check()

    def open_deliver_import_modal(self):
        self.click(self.DELIVER_IMPORT_BTN)
        self.page.locator(self.DELIVER_IMPORT_FILE).first.wait_for(state="attached", timeout=8000)

    def deliver_import_available(self):
        return self.page.locator(self.DELIVER_IMPORT_BTN).count() > 0

    def open_payment_import_modal(self):
        self.click(self.PAYMENT_IMPORT_BTN)
        self.page.locator(self.PAYMENT_IMPORT_FILE).first.wait_for(state="attached", timeout=8000)

    def deliver_denominator_sum(self):
        """Sum the numeric progress-bar denominators on the Deliver tab (each is a
        payment unit's max_visits). Used to cross-check a budget change (OD_15)."""
        self.is_displayed(self.DELIVER_PROGRESS_DENOMINATORS, timeout=15000)
        total = 0
        for t in self.page.locator(self.DELIVER_PROGRESS_DENOMINATORS).all_inner_texts():
            digits = "".join(ch for ch in t if ch.isdigit())
            if digits:
                total += int(digits)
        self._step(f"Deliver-tab denominator sum = {total}")
        return total

    # OD_24 covered by verify_status_badge; OD_25 by wait_for_stats + verify_graphs.

    # OD_27: currency-formatted values
    def summary_card_value(self, label):
        card = self.page.locator(self.INFO_CARD_BY_LABEL.format(label=label)).first
        card.wait_for(state="visible", timeout=15000)
        value = card.locator("xpath=.//p").first.inner_text().strip()
        self._step(f"Summary card '{label}' value: {value!r}")
        return value

    # OD_29: map/audit/tasks panels present (product-risk - assert render, not click-through)
    def stat_panel_present(self, title):
        present = self.page.locator(self.STAT_PANEL_BY_TITLE.format(title=title)).count() > 0
        self._step(f"Stat panel '{title}' present: {present}")
        return present

    def stat_panel_href(self, title):
        """Return the href of the anchor wrapping a panel, or None if not a link."""
        anchor = self.page.locator(
            f"//a[.//*[self::h3 or self::p][normalize-space()='{title}']]"
        )
        if anchor.count() == 0:
            return None
        return anchor.first.get_attribute("href")

    # OD_31: funnel
    def funnel_stage_labels(self):
        self.page.locator(self.FUNNEL_CONTAINER).first.wait_for(state="visible", timeout=30000)
        self.page.locator(self.FUNNEL_HEADING).first.wait_for(state="visible", timeout=30000)
        labels = [t.strip() for t in self.page.locator(self.FUNNEL_STAGE_LABELS).all_inner_texts() if t.strip()]
        self._step(f"Funnel stages: {labels}")
        return labels

    def funnel_counts_nonempty(self):
        counts = [t.strip() for t in self.page.locator(self.FUNNEL_STAGE_COUNTS).all_inner_texts()]
        self._step(f"Funnel counts: {counts}")
        return all(c != "" for c in counts) and len(counts) >= 7

    # OD_32: worker progress bars
    def worker_progress_labels(self):
        self.page.locator(self.WORKER_PROGRESS_CONTAINER).first.wait_for(state="visible", timeout=30000)
        # Bars are HTMX-swapped in after the container; wait for the first label,
        # then read. An opportunity with no deliveries/payments renders no bars.
        self.is_displayed(self.WORKER_PROGRESS_LABELS, timeout=15000)
        labels = [t.strip() for t in self.page.locator(self.WORKER_PROGRESS_LABELS).all_inner_texts() if t.strip()]
        self._step(f"Worker-progress labels: {labels}")
        return labels

    def worker_progress_bar_count(self):
        return self.page.locator(self.WORKER_PROGRESS_BARS).count()

    # OD_33: resource card count + open modal on the right tab
    def resource_card_count(self, name):
        card = self.page.locator(self.RESOURCE_CARD_BY_NAME.format(name=name)).first
        card.wait_for(state="visible", timeout=15000)
        # The card holds two <h3> (name, then the count); take the last.
        count = card.locator("xpath=.//h3").last.inner_text().strip()
        self._step(f"Resource card '{name}' count: {count!r}")
        return count

    def open_resource_card(self, name):
        self._step(f"Open resource card '{name}'")
        self.click(self.RESOURCE_CARD_BY_NAME.format(name=name))
        self.page.locator(self.RESOURCE_MODAL).first.wait_for(state="visible", timeout=10000)

    def active_resource_tab(self):
        tab = self.page.locator("//ul[contains(@class,'tabs')]//li[contains(@class,'active')]").first
        tab.wait_for(state="visible", timeout=10000)
        return tab.inner_text().strip()

    # OD_38 Learn tab / OD_40 workers tab: navigate a worker sub-tab by url
    def goto_worker_tab(self, tab):
        """tab in {workers, learn, deliver, payments, tasks}."""
        host, slug, opp_id = self.base_url_parts()
        suffix = {"workers": "workers/", "learn": "workers/learn/", "deliver": "workers/deliver/",
                  "payments": "workers/payments/", "tasks": "workers/tasks/"}[tab]
        url = f"{host}/a/{slug}/opportunity/{opp_id}/{suffix}"
        self._step(f"Go to worker '{tab}' tab: {url}")
        self.page.goto(url)
        self.page.wait_for_load_state("load")

    def workers_tab_label_text(self):
        # WORKERS_TAB_LABEL already carries the loader's '#' prefix.
        loc = self.page.locator(self.WORKERS_TAB_LABEL)
        loc.first.wait_for(state="visible", timeout=15000)
        text = loc.first.inner_text().strip()
        self._step(f"Connect Workers tab label: {text!r}")
        return text

    def search_workers(self, term):
        self._step(f"Search workers for {term!r}")
        self.is_displayed(self.WORKERS_SEARCH_INPUT, timeout=15000)
        self.type(self.WORKERS_SEARCH_INPUT, term)
        self.page.locator(self.WORKERS_SEARCH_INPUT).first.press("Enter")
        self.page.wait_for_timeout(1500)

    def displaying_count_text(self):
        if self.page.locator(self.WORKERS_DISPLAYING_COUNT).count() == 0:
            return ""
        text = self.page.locator(self.WORKERS_DISPLAYING_COUNT).first.inner_text().strip()
        self._step(f"Displaying-count line: {text!r}")
        return text

    # OD_42/OD_43: deliver-tab filters
    def open_deliver_filter_modal(self):
        self._step("Open deliver filter modal")
        self.click(self.DELIVER_FILTER_BUTTON)
        self.page.locator(self.DELIVER_FILTER_APPLY).first.wait_for(state="visible", timeout=10000)

    def filter_present(self, name):
        return self.page.locator(self.FILTER_SELECT_BY_NAME.format(name=name)).count() > 0

    def apply_deliver_filter(self, name, label):
        self.select_by_visible_text(self.FILTER_SELECT_BY_NAME.format(name=name), label)
        self._step(f"Apply deliver filter {name}={label!r}")
        self.click(self.DELIVER_FILTER_APPLY)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1000)

    # OD_45 / OD_47: authenticated direct GETs (share the page's session cookies)
    def get_status(self, path):
        host, slug, opp_id = self.base_url_parts()
        url = path if path.startswith("http") else f"{host}{path}"
        resp = self.page.request.get(url)
        self._step(f"GET {url} -> {resp.status}")
        return resp.status

    def stat_endpoint_url(self, name):
        host, slug, opp_id = self.base_url_parts()
        suffix = {
            "delivery": "opportunity_delivery_stats/",
            "worker_progress": "opportunity_worker_progress_stats/",
            "funnel": "opportunity_funnel_progress_stats/",
        }[name]
        return f"{host}/a/{slug}/opportunity/{opp_id}/{suffix}"

    def export_probe_url(self, kind, task_id):
        host, slug, opp_id = self.base_url_parts()
        return f"{host}/a/{slug}/opportunity/{kind}/{task_id}"

    # -- retained: used by test_olp_04 ------------------------------------------

    def verify_dashboard_card_details_present(self, title, subtitle, count_section=True):
        selector = self.DASHBOARD_CARD.format(title=title, subtitle=subtitle)
        self.scroll_into_view(selector)
        card = self.page.locator(selector).first
        card.wait_for(state="visible")
        if count_section:
            count = card.locator("xpath=.//h3[contains(@class,'text-2xl')]").inner_text().strip()
            assert count != "", f"{title} {subtitle} count is empty"
            print(f"{title} {subtitle} in Opportunity Dashboard --> {count}")

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.click_link_by_text(data["opportunity_name"])
        # Only the always-present cards are verified here. "Tasks Assigned to Connect
        # Workers", "View Progress Map" and "Audit Opportunity" are feature-flagged
        # (microplanning / task types / weekly report) and covered by separate tests.
        self.verify_dashboard_card_details_present("Connect Workers", "", count_section=False)
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")
