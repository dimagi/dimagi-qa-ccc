"""Worker Visit Verification Page (WVVP_1-7).

The per-worker Visits page reached by clicking a worker on the Deliver tab. Covers
the visit table + tabs, individual/bulk approve, and suspend/revoke. Migrated from
the Selenium WorkerVisitsPage; Selenium's time.sleep() waits are replaced with
Playwright waits and the individual-row checkbox is anchored on the first data row
rather than a hard-coded entity name.
"""

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class WorkerVisitsPage(BasePage):
    VISITS_TABLE = locators.get("worker_visits_page", "visits_table")
    SELECT_ALL_CHECKBOX = locators.get("worker_visits_page", "select_all_checkbox")
    FIRST_ROW_CHECKBOX = locators.get("worker_visits_page", "first_row_checkbox")
    APPROVE_ALL_BUTTON = locators.get("worker_visits_page", "approve_all_button")
    APPROVE_POPUP_BUTTON = locators.get("worker_visits_page", "approve_popup_button")
    REJECT_ALL_BUTTON = locators.get("worker_visits_page", "reject_all_button")
    REJECT_POPUP_BUTTON = locators.get("worker_visits_page", "reject_popup_button")
    APPROVE_BUTTON = locators.get("worker_visits_page", "approve_button")
    REJECT_BUTTON = locators.get("worker_visits_page", "reject_button")
    TABS_CONTAINER = locators.get("worker_visits_page", "tabs_container")
    TAB_ITEM_BY_NAME = locators.get("worker_visits_page", "tab_item_by_name")
    VISIT_DETAILS_CONTAINER = locators.get("worker_visits_page", "visit_details_container")
    USERNAME_SECTION = locators.get("worker_visits_page", "username_section")
    SUSPEND_BUTTON = locators.get("worker_visits_page", "suspend_button")
    SUSPEND_REASON_INPUT = locators.get("worker_visits_page", "suspend_reason_input")
    SUSPEND_POPUP_BUTTON = locators.get("worker_visits_page", "suspend_popup_button")
    REVOKE_SUSPEND_BUTTON = locators.get("worker_visits_page", "revoke_suspend_button")

    # -- table / tabs ------------------------------------------------------------

    def _await_table(self):
        self.page.locator(self.VISITS_TABLE).first.wait_for(state="visible", timeout=30000)

    def verify_worker_visits_table_headers_present(self, pending=False):
        self._await_table()
        actual = [h.strip() for h in self.page.locator(self.VISITS_TABLE).locator("thead th").all_inner_texts() if h.strip()]
        actual_lower = [h.lower() for h in actual]
        # The header is "Flags" when the opportunity surfaces flags, else "Status".
        flag_or_status = "Flags" if "flags" in actual_lower else "Status"
        expected = ["Date", "Entity Name", "Deliver Unit", "Payment Unit", flag_or_status]
        if not pending:
            expected.append("Last Activity")
        missing = [h for h in expected if h.lower() not in actual_lower]
        assert not missing, f"Missing headers: {missing}\nActual headers found: {actual}"
        self._step(f"Worker visits table headers present: {actual}")

    def has_visit_rows(self):
        """Whether the current visits table has any data rows with a select checkbox
        (i.e. there is something to approve/reject)."""
        self._await_table()
        n = self.page.locator(self.FIRST_ROW_CHECKBOX).count()
        self._step(f"Visit rows with a checkbox: {n}")
        return n > 0

    def verify_tabs_present(self, expected_tabs):
        container = self.page.locator(self.TABS_CONTAINER).first
        container.wait_for(state="visible", timeout=15000)
        missing = [
            tab
            for tab in expected_tabs
            if self.page.locator(self.TAB_ITEM_BY_NAME.format(tab_name=tab)).count() == 0
        ]
        assert not missing, f"Missing tabs: {', '.join(missing)}"
        self._step(f"Worker visits tabs present: {expected_tabs}")

    REVIEW_TABS = ["Pending NM Review", "Approved", "Rejected", "All"]

    def has_review_tabs(self):
        """Whether this worker's Visits page exposes the NM-review sub-tabs
        (Pending NM Review / Approved / Rejected / All). Opportunities without NM
        review show only the Visits/Tasks pair."""
        self.page.locator(self.TABS_CONTAINER).first.wait_for(state="visible", timeout=15000)
        present = self.page.locator(self.TAB_ITEM_BY_NAME.format(tab_name="Pending NM Review")).count() > 0
        self._step(f"NM-review tabs present: {present}")
        return present

    def verify_worker_visits_tabs_present(self):
        """Verification opportunities show the review tabs; opportunities without
        NM review only show the Visits/Tasks pair. Either is valid."""
        if self.has_review_tabs():
            self.verify_tabs_present(self.REVIEW_TABS)
        else:
            self.verify_tabs_present(["Visits", "Tasks"])

    def click_tab_by_name(self, tab_name):
        self._step(f"Click visits '{tab_name}' tab")
        self.click(self.TAB_ITEM_BY_NAME.format(tab_name=tab_name))
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)
        self.verify_tab_active(tab_name)

    def verify_tab_active(self, tab_name):
        tab = self.page.locator(self.TAB_ITEM_BY_NAME.format(tab_name=tab_name)).first
        tab.wait_for(state="visible", timeout=15000)
        cls = tab.get_attribute("class") or ""
        assert "active" in cls, f"Tab '{tab_name}' is not active (class={cls!r})"
        self._step(f"Visits tab '{tab_name}' is active")

    # -- approve / reject --------------------------------------------------------

    def verify_approve_and_reject_all_btns_present(self):
        self.page.locator(self.APPROVE_ALL_BUTTON).first.wait_for(state="visible", timeout=15000)
        self.page.locator(self.REJECT_ALL_BUTTON).first.wait_for(state="visible", timeout=15000)
        self._step("Approve All / Reject All buttons present")

    def select_first_row(self):
        """Tick the first visit row's checkbox (individual selection, WVVP_1)."""
        checkbox = self.page.locator(self.FIRST_ROW_CHECKBOX).first
        checkbox.wait_for(state="visible", timeout=15000)
        if not checkbox.is_checked():
            checkbox.check()
        self.verify_approve_and_reject_all_btns_present()

    def set_select_all_checkbox(self, state):
        """Tick/untick the header select-all checkbox (bulk selection, WVVP_2)."""
        checkbox = self.page.locator(self.SELECT_ALL_CHECKBOX).first
        checkbox.wait_for(state="visible", timeout=15000)
        if checkbox.is_checked() != state:
            checkbox.click()
        self.page.wait_for_timeout(1000)
        self.verify_approve_and_reject_all_btns_present()

    def click_approve_all_btn(self):
        self._step("Approve All -> confirm")
        self.click(self.APPROVE_ALL_BUTTON)
        self.page.locator(self.APPROVE_POPUP_BUTTON).first.wait_for(state="visible", timeout=10000)
        self.click(self.APPROVE_POPUP_BUTTON)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)

    def click_reject_all_btn(self):
        self._step("Reject All -> confirm")
        self.click(self.REJECT_ALL_BUTTON)
        self.page.locator(self.REJECT_POPUP_BUTTON).first.wait_for(state="visible", timeout=10000)
        self.click(self.REJECT_POPUP_BUTTON)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)

    # -- suspend / revoke (WVVP_3) -----------------------------------------------

    def suspend_user_in_worker_visits(self, reason):
        self._step("Suspend the worker")
        self.page.locator(self.USERNAME_SECTION).first.wait_for(state="visible", timeout=15000)
        self.click(self.USERNAME_SECTION)
        self.page.locator(self.SUSPEND_BUTTON).first.wait_for(state="visible", timeout=15000)
        self.click(self.SUSPEND_BUTTON)
        self.page.locator(self.SUSPEND_REASON_INPUT).first.wait_for(state="visible", timeout=15000)
        self.type(self.SUSPEND_REASON_INPUT, reason)
        self.click(self.SUSPEND_POPUP_BUTTON)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)
        self._step("Worker suspended")

    def revoke_suspension_for_worker(self):
        self._step("Revoke the worker's suspension")
        self.click(self.USERNAME_SECTION)
        self.page.locator(self.REVOKE_SUSPEND_BUTTON).first.wait_for(state="visible", timeout=15000)
        self.click(self.REVOKE_SUSPEND_BUTTON)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(2000)
        # Back to the visits page, reload, and confirm the user is suspendable again.
        self.page.go_back()
        self.page.wait_for_load_state("load")
        self.page.locator(self.USERNAME_SECTION).first.wait_for(state="visible", timeout=15000)
        self.page.reload(wait_until="load")
        self.click(self.USERNAME_SECTION)
        self.page.locator(self.SUSPEND_BUTTON).first.wait_for(state="visible", timeout=15000)
        self._step("Suspension revoked (worker is suspendable again)")
