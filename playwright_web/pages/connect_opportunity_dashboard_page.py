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
        if self.page.locator(self.HAMBURGER_MENU).count() == 0:
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
        joined = " | ".join(self.resource_modal_columns())
        missing = [c for c in expected if c not in joined]
        assert not missing, f"Missing modal columns {missing}"
        self._step(f"All expected modal columns present: {expected}")

    def verify_resource_modal_readonly(self):
        """The dialog is informational - no editable inputs beyond the close icon."""
        inputs = self.page.locator(self.RESOURCE_MODAL_INPUTS).count()
        assert inputs == 0, f"Resource modal unexpectedly has {inputs} editable field(s)"
        self._step("Resource modal is non-editable")

    def close_resource_modal(self):
        self.click(self.RESOURCE_MODAL_CLOSE)
        self.page.locator(self.RESOURCE_MODAL).first.wait_for(state="hidden", timeout=10000)

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
