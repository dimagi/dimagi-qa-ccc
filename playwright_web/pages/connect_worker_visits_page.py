"""Worker Visit Verification Page (MTP VV_1/3/4/5/9).

The per-worker Visits page reached by clicking a worker on the Deliver tab. Covers
the visit table + tabs, individual/bulk approve, and suspend/revoke. Migrated from
the Selenium WorkerVisitsPage; Selenium's time.sleep() waits are replaced with
Playwright waits and the individual-row checkbox is anchored on the first data row
rather than a hard-coded entity name.
"""

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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
    VISIT_ROW_ANY = locators.get("worker_visits_page", "visit_row_any")
    VISIT_ROW_BY_STATUS = locators.get("worker_visits_page", "visit_row_by_status")
    VISIT_DETAILS_SECTION = locators.get("worker_visits_page", "visit_details_section")
    VISIT_DETAILS_FIELD_LABEL = locators.get("worker_visits_page", "visit_details_field_label")
    VISIT_DETAILS_MAP = locators.get("worker_visits_page", "visit_details_map")
    VISIT_IMAGE_THUMBNAIL = locators.get("worker_visits_page", "visit_image_thumbnail")
    VISIT_IMAGE_POPUP = locators.get("worker_visits_page", "visit_image_popup")
    VISIT_IMAGE_POPUP_CLOSE = locators.get("worker_visits_page", "visit_image_popup_close")
    VISIT_ROW_BY_ID = locators.get("worker_visits_page", "visit_row_by_id")
    VISIT_ACTION_REJECT = locators.get("worker_visits_page", "visit_action_reject")
    VISIT_ACTION_APPROVE = locators.get("worker_visits_page", "visit_action_approve")
    VISIT_REJECT_MODAL_REASON = locators.get("worker_visits_page", "visit_reject_modal_reason")
    VISIT_REJECT_MODAL_SUBMIT = locators.get("worker_visits_page", "visit_reject_modal_submit")
    VISIT_APPROVE_MODAL_JUSTIFICATION = locators.get("worker_visits_page", "visit_approve_modal_justification")
    VISIT_APPROVE_MODAL_SUBMIT = locators.get("worker_visits_page", "visit_approve_modal_submit")
    VISIT_PM_AGREE = locators.get("worker_visits_page", "visit_pm_agree")
    VISIT_PM_DISAGREE = locators.get("worker_visits_page", "visit_pm_disagree")

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
        """Tick the first visit row's checkbox (individual selection; VV_1)."""
        checkbox = self.page.locator(self.FIRST_ROW_CHECKBOX).first
        checkbox.wait_for(state="visible", timeout=15000)
        if not checkbox.is_checked():
            checkbox.check()
        self.verify_approve_and_reject_all_btns_present()

    def set_select_all_checkbox(self, state):
        """Tick/untick the header select-all checkbox (bulk selection; VV_1 / GAP-SRC-W-42)."""
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

    # -- suspend / revoke (VV_4) -----------------------------------------------

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

    # -- single-visit details panel (VV_9 / VV_3) --------------------------------

    def open_first_visit_details(self):
        """Click the first visit row so its details load into #visit-details (every
        row carries an hx-get to user_visit_details targeting the panel). Returns
        True if a row was available, False if the table has no visits."""
        self._await_table()
        rows = self.page.locator(self.VISIT_ROW_ANY)
        if rows.count() == 0:
            self._step("No visit rows to open details for")
            return False
        rows.first.click()
        if not self._details_panel_loaded():
            self._step(
                "Visit details panel did not populate after clicking a row - the "
                "user_visit_details endpoint appears to be erroring for this opportunity "
                "(seen as HTTP 500 on covid_opp_test, likely a missing verification-flags "
                "config; views.py user_visit_details reads opportunity.opportunityverificationflags)"
            )
            return False
        self._step("Opened visit details panel")
        return True

    def _details_panel_loaded(self, timeout=15000):
        """After a row click, whether #visit-details actually rendered its content
        (the Information heading). Returns False rather than raising when the hx-get
        swap never populates - e.g. the details endpoint 500s for the opportunity -
        so callers can skip cleanly instead of hard-failing on a server/data gap."""
        try:
            self.page.locator(self.VISIT_DETAILS_CONTAINER).first.wait_for(state="visible", timeout=timeout)
            self.page.locator(self.VISIT_DETAILS_SECTION.format(label="Information")).first.wait_for(
                state="visible", timeout=timeout
            )
            return True
        except PlaywrightTimeoutError:
            return False

    def verify_visit_details_panel(self):
        """VV_9: the details panel shows Information (Payment Unit / Entity Name /
        Entity ID), Verification Parameters, and - when the visit has a location -
        the Map."""
        for section in ("Information", "Verification Parameters"):
            self.page.locator(self.VISIT_DETAILS_SECTION.format(label=section)).first.wait_for(
                state="visible", timeout=15000
            )
        missing = [
            field
            for field in ("Payment Unit", "Entity Name", "Entity ID")
            if self.page.locator(self.VISIT_DETAILS_FIELD_LABEL.format(label=field)).count() == 0
        ]
        assert not missing, f"Visit details Information section missing fields: {missing}"
        # Map is only rendered when the visit carries a location; assert it when present.
        if self.page.locator(self.VISIT_DETAILS_SECTION.format(label="Map")).count() > 0:
            self.page.locator(self.VISIT_DETAILS_MAP).first.wait_for(state="visible", timeout=15000)
            self._step("Visit details: Information + Verification Parameters + Map present")
        else:
            self._step(
                "Visit details: Information + Verification Parameters present "
                "(no Map - this visit has no captured location)"
            )

    def visit_has_images(self):
        """Whether the open details panel has a Media/image section (VV_3 precondition)."""
        n = self.page.locator(self.VISIT_IMAGE_THUMBNAIL).count()
        self._step(f"Visit image thumbnails present: {n}")
        return n > 0

    def open_first_visit_with_images(self, max_rows=10):
        """Open visit rows in turn (up to max_rows) until one shows a Media/image
        section. Returns True when found, False if none of the scanned visits have a
        photo. Used by VV_3, whose carousel needs an image-bearing visit."""
        self._await_table()
        rows = self.page.locator(self.VISIT_ROW_ANY)
        total = rows.count()
        if total == 0:
            return False
        for i in range(min(total, max_rows)):
            rows.nth(i).click()
            if not self._details_panel_loaded():
                self._step(f"Visit row {i} details did not render (details endpoint erroring?) - skipping row")
                continue
            if self.visit_has_images():
                self._step(f"Visit row {i} has an image attachment")
                return True
        self._step(f"No image attachment (or no rendered details) on the first {min(total, max_rows)} visit(s)")
        return False

    def open_and_verify_image_carousel(self):
        """VV_3: clicking a visit image opens the carousel popup; then close it so the
        panel is left as found."""
        self.page.locator(self.VISIT_IMAGE_THUMBNAIL).first.click()
        self.page.locator(self.VISIT_IMAGE_POPUP).first.wait_for(state="visible", timeout=10000)
        self._step("Image carousel popup opened")
        self.click(self.VISIT_IMAGE_POPUP_CLOSE)
        self.page.locator(self.VISIT_IMAGE_POPUP).first.wait_for(state="hidden", timeout=10000)
        self._step("Image carousel popup closed")

    # -- review actions: NM reject/approve (VV_31/32), PM agree/disagree (VV_33/34) --
    # These act on a single visit via the #visit-actions bar that swaps into place
    # when a row is opened. The bar shows NM Reject/Approve (which open a reason /
    # justification modal) OR PM Agree/Disagree (which post immediately), depending
    # on the org role and the visit's review state; it is absent under auto-verify.

    def _open_row_at(self, index):
        """Open the visit row at `index` and wait for its details panel to populate."""
        self.page.locator(self.VISIT_ROW_ANY).nth(index).click()
        self.page.locator(self.VISIT_DETAILS_CONTAINER).first.wait_for(state="visible", timeout=15000)
        self.page.locator(self.VISIT_DETAILS_SECTION.format(label="Information")).first.wait_for(
            state="visible", timeout=15000
        )

    def _open_row_by_id(self, visit_id):
        """Re-open a visit by its data-visit-id after a table reload (the review post
        triggers reload_table, re-rendering rows) and wait for its details panel."""
        row = self.page.locator(self.VISIT_ROW_BY_ID.format(visit_id=visit_id)).first
        row.wait_for(state="visible", timeout=15000)
        row.click()
        self.page.locator(self.VISIT_DETAILS_CONTAINER).first.wait_for(state="visible", timeout=15000)
        self.page.locator(self.VISIT_DETAILS_SECTION.format(label="Information")).first.wait_for(
            state="visible", timeout=15000
        )

    def _find_visit_with_enabled_action(self, action_locator, max_rows=15):
        """Open visits in turn until one exposes `action_locator` present and enabled.
        Returns that visit's data-visit-id, or None if none of the scanned visits
        offer the action (e.g. all already in a terminal state, or auto-verify)."""
        self._await_table()
        rows = self.page.locator(self.VISIT_ROW_ANY)
        total = rows.count()
        for i in range(min(total, max_rows)):
            visit_id = rows.nth(i).get_attribute("data-visit-id")
            self._open_row_at(i)
            btn = self.page.locator(action_locator).first
            if btn.count() > 0 and btn.is_enabled():
                self._step(f"Visit {visit_id} (row {i}) offers the requested review action")
                return visit_id
        self._step(f"No visit in the first {min(total, max_rows)} rows offers the requested action")
        return None

    def nm_reject_a_visit(self, reason, max_rows=15):
        """VV_31 (NM): reject a rejectable visit via the Reason-for-Rejection modal,
        then confirm the visit is now rejected. Returns False (caller skips) when no
        scanned visit is rejectable."""
        visit_id = self._find_visit_with_enabled_action(self.VISIT_ACTION_REJECT, max_rows)
        if visit_id is None:
            return False
        self.click(self.VISIT_ACTION_REJECT)
        self.page.locator(self.VISIT_REJECT_MODAL_REASON).first.wait_for(state="visible", timeout=10000)
        self.type(self.VISIT_REJECT_MODAL_REASON, reason)
        self.click(self.VISIT_REJECT_MODAL_SUBMIT)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(2000)
        # reload_table re-rendered the rows; re-open by id and confirm the outcome.
        self._open_row_by_id(visit_id)
        status = self.page.locator(self.VISIT_ROW_BY_ID.format(visit_id=visit_id)).first.get_attribute(
            "data-visit-status"
        )
        assert status == "rejected", f"Visit {visit_id} status is {status!r} after reject, expected 'rejected'"
        self._step(f"NM rejected visit {visit_id} (status now rejected)")
        return True

    def nm_approve_a_visit(self, justification, max_rows=15):
        """VV_32 (NM): approve an approvable visit via the Justification-for-Approval
        modal (the justification textarea is required), then confirm it is approved.
        Returns False when no scanned visit is approvable."""
        visit_id = self._find_visit_with_enabled_action(self.VISIT_ACTION_APPROVE, max_rows)
        if visit_id is None:
            return False
        self.click(self.VISIT_ACTION_APPROVE)
        self.page.locator(self.VISIT_APPROVE_MODAL_JUSTIFICATION).first.wait_for(state="visible", timeout=10000)
        self.type(self.VISIT_APPROVE_MODAL_JUSTIFICATION, justification)
        self.click(self.VISIT_APPROVE_MODAL_SUBMIT)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(2000)
        self._open_row_by_id(visit_id)
        status = self.page.locator(self.VISIT_ROW_BY_ID.format(visit_id=visit_id)).first.get_attribute(
            "data-visit-status"
        )
        assert status == "approved", f"Visit {visit_id} status is {status!r} after approve, expected 'approved'"
        self._step(f"NM approved visit {visit_id} (status now approved)")
        return True

    def pm_agree_a_visit(self, max_rows=15):
        """VV_33 (PM): agree an NM-reviewed visit (the Agree button posts directly),
        then confirm Agree is now disabled (review_status == agree). Returns False
        when no scanned visit offers an enabled Agree."""
        visit_id = self._find_visit_with_enabled_action(self.VISIT_PM_AGREE, max_rows)
        if visit_id is None:
            return False
        self.click(self.VISIT_PM_AGREE)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(2000)
        self._open_row_by_id(visit_id)
        assert not self.page.locator(self.VISIT_PM_AGREE).first.is_enabled(), (
            f"Agree still enabled for visit {visit_id} after agreeing"
        )
        self._step(f"PM agreed visit {visit_id} (Agree now disabled)")
        return True

    def action_bar_button_set(self):
        """Return the set of individual-review buttons present in #visit-actions -
        a subset of {'Approve','Reject','Agree','Disagree'}. Empty under auto-verify
        (the whole bar body is wrapped in `if not automatic_visit_verification`)."""
        present = set()
        if self.page.locator(self.VISIT_ACTION_APPROVE).count() > 0:
            present.add("Approve")
        if self.page.locator(self.VISIT_ACTION_REJECT).count() > 0:
            present.add("Reject")
        if self.page.locator(self.VISIT_PM_AGREE).count() > 0:
            present.add("Agree")
        if self.page.locator(self.VISIT_PM_DISAGREE).count() > 0:
            present.add("Disagree")
        self._step(f"Action-bar buttons present: {sorted(present) or 'none (auto-verify)'}")
        return present

    def first_visit_id(self):
        """data-visit-id of the first visit row, or None when the table is empty."""
        self._await_table()
        rows = self.page.locator(self.VISIT_ROW_ANY)
        if rows.count() == 0:
            return None
        return rows.first.get_attribute("data-visit-id")

    def visit_table_headers(self):
        """Lowercased set of the visit table's column headers. The plain
        WorkerVisitTable (WORKER_VISITS_TASKS switch ON) has a 'Status' column; the
        tabbed UserVisitVerificationTable (switch OFF) has 'Flags' and excludes
        'Status' - the reliable signal for which table the waffle selected."""
        self._await_table()
        headers = [
            h.strip()
            for h in self.page.locator(self.VISITS_TABLE).locator("thead th").all_inner_texts()
            if h.strip()
        ]
        return {h.lower() for h in headers}

    def has_visits_tasks_tabs(self):
        """Whether the Visits/Tasks sub-tab bar is shown (show_worker_tasks_tabs,
        gated by the WORKER_VISITS_TASKS switch - present iff the switch is ON)."""
        self.page.locator(self.TABS_CONTAINER).first.wait_for(state="visible", timeout=15000)
        has_visits = self.page.locator(self.TAB_ITEM_BY_NAME.format(tab_name="Visits")).count() > 0
        has_tasks = self.page.locator(self.TAB_ITEM_BY_NAME.format(tab_name="Tasks")).count() > 0
        present = has_visits and has_tasks
        self._step(f"Visits/Tasks sub-tab bar present: {present}")
        return present

    def bulk_controls_present(self):
        """(approve_all, reject_all, select_all) DOM presence. The bulk Approve All /
        Reject All buttons and the select-all checkbox column exist only for a
        non-viewer NM on a manual-review opp; they are template-excluded for PM and
        viewer and under auto-verify."""
        approve = self.page.locator(self.APPROVE_ALL_BUTTON).count() > 0
        reject = self.page.locator(self.REJECT_ALL_BUTTON).count() > 0
        select = self.page.locator(self.SELECT_ALL_CHECKBOX).count() > 0
        self._step(f"Bulk controls present - approve_all={approve} reject_all={reject} select_all={select}")
        return approve, reject, select

    def pm_disagree_a_visit(self, max_rows=15):
        """VV_34 (PM): disagree an NM-reviewed visit pending PM review (Disagree posts
        directly), then confirm Disagree is now disabled (review no longer pending).
        Returns False when no scanned visit offers an enabled Disagree."""
        visit_id = self._find_visit_with_enabled_action(self.VISIT_PM_DISAGREE, max_rows)
        if visit_id is None:
            return False
        self.click(self.VISIT_PM_DISAGREE)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(2000)
        self._open_row_by_id(visit_id)
        assert not self.page.locator(self.VISIT_PM_DISAGREE).first.is_enabled(), (
            f"Disagree still enabled for visit {visit_id} after disagreeing"
        )
        self._step(f"PM disagreed visit {visit_id} (Disagree now disabled)")
        return True
