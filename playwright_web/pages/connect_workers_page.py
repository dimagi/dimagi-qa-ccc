import re
import time
from datetime import date, datetime, timedelta

from utils.helpers import LocatorLoader

from pages.base_page import BasePage

locators = LocatorLoader()


class ConnectWorkersPage(BasePage):
    TASKS_TAB = locators.get("connect_workers_page", "tasks_tab")
    TAB_CONTENT = locators.get("connect_workers_page", "tab_content")
    DRILLDOWN_TASKS_TAB = locators.get("connect_workers_page", "drilldown_tasks_tab")
    TASK_DETAILS_PANEL = locators.get("connect_workers_page", "task_details_panel")
    DRILLDOWN_TASK_ROW = locators.get("connect_workers_page", "drilldown_task_row")
    WORKER_TASK_GROUP = locators.get("connect_workers_page", "worker_task_group_by_worker")
    WORKER_NAME_LINK = locators.get("connect_workers_page", "worker_name_link_by_worker")
    WORKER_TASKS_CREATE_BTN = locators.get("connect_workers_page", "worker_tasks_create_btn")
    WORKER_TASKS_DELETE_BTN = locators.get("connect_workers_page", "worker_tasks_delete_btn")
    WORKER_TASK_ROW_BY_SLUG = locators.get("connect_workers_page", "worker_task_row_by_slug")
    WORKER_TASK_ROW_CHECKBOX_BY_SLUG = locators.get("connect_workers_page", "worker_task_row_checkbox_by_slug")
    WORKER_TASK_STATUS_BY_SLUG = locators.get("connect_workers_page", "worker_task_status_by_slug")
    WORKER_VISIT_ROWS = locators.get("connect_workers_page", "worker_visit_rows")
    CONFIRM_MODAL_TITLE = locators.get("connect_workers_page", "confirm_modal_title")
    CONFIRM_DELETE_BTN = locators.get("connect_workers_page", "confirm_delete_btn")
    CREATE_TASK_FORM = locators.get("connect_assigned_tasks_page", "create_task_form")
    CREATE_TASK_SAVE_BTN = locators.get("connect_assigned_tasks_page", "create_task_save_btn")
    TASK_SELECT = locators.get("connect_assigned_tasks_page", "task_select")
    INVITE_USERS_TEXTAREA = locators.get("connect_worker_invite_page", "users_textarea")
    INVITE_SUBMIT_BTN = locators.get("connect_worker_invite_page", "submit_btn")

    # -- Worker List View (WLV_1-8): list / Learn / Deliver tables ----------------
    LV_TABLE = locators.get("connect_workers_page", "lv_table")
    LV_TAB_ITEM_BY_NAME = locators.get("connect_workers_page", "lv_tab_item_by_name")
    LV_NAME_IN_TABLE = locators.get("connect_workers_page", "lv_name_item_in_table")
    COUNT_BREAKDOWN_POPUP = locators.get("connect_workers_page", "count_breakdown_popup")
    LV_FILTER_BUTTON = locators.get("connect_workers_page", "lv_filter_button")
    LV_FILTER_BADGE = locators.get("connect_workers_page", "lv_filter_badge")
    LV_FILTER_MODAL = locators.get("connect_workers_page", "lv_filter_modal")
    LV_FILTER_APPLY = locators.get("connect_workers_page", "lv_filter_apply_btn")
    FILTER_LAST_ACTIVE = locators.get("connect_workers_page", "filter_last_active")
    FILTER_HAS_DUPLICATES = locators.get("connect_workers_page", "filter_has_duplicates")
    FILTER_HAS_FLAGS = locators.get("connect_workers_page", "filter_has_flags")
    FILTER_HAS_OVERLIMIT = locators.get("connect_workers_page", "filter_has_overlimit")
    FILTER_REVIEW_PENDING = locators.get("connect_workers_page", "filter_review_pending")

    # -- worker invite -------------------------------------------------------

    def invite_workers(self, base_url, org_slug, opp_id, phone_numbers):
        """Invite workers by full phone number, e.g. '+74267426000'.

        The invite page has no navigation entry; it takes a textarea with one
        '+<country code><number>' per line and hands the numbers to a celery
        task, so the worker's invite appears asynchronously.
        """
        self._step(f"Navigate to worker invite page for opp {opp_id}")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/user_invite/")
        self.page.wait_for_load_state("load")
        self._step(f"Invite workers: {', '.join(phone_numbers)}")
        self.page.locator(self.INVITE_USERS_TEXTAREA).first.fill("\n".join(phone_numbers))
        self.click(self.INVITE_SUBMIT_BTN)
        self.page.wait_for_load_state("load")

    def wait_for_worker_in_list(self, base_url, org_slug, opp_id, phone_number, timeout_seconds=120):
        """Poll the workers list until an invited number shows up (async invite)."""
        deadline = time.monotonic() + timeout_seconds
        attempt = 0
        while True:
            attempt += 1
            self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/workers/")
            self.page.wait_for_load_state("load")
            self.page.wait_for_timeout(2000)  # worker table arrives via htmx
            if phone_number in self.page.locator("body").inner_text():
                self._step(f"Worker {phone_number} listed after {attempt} check(s)")
                return True
            if time.monotonic() >= deadline:
                raise AssertionError(
                    f"Worker {phone_number} did not appear in the workers list within {timeout_seconds}s"
                )
            self._step(f"Worker {phone_number} not listed yet - retrying")
            self.page.wait_for_timeout(10000)

    def goto_workers_tasks_tab(self, base_url, org_slug, opp_id):
        """The Workers page Tasks tab (grouped per-worker table)."""
        self._step(f"Navigate to Workers > Tasks tab for opp {opp_id}")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/workers/tasks/")
        self.page.wait_for_load_state("load")
        self.page.locator(self.TAB_CONTENT).first.wait_for(state="visible", timeout=20000)

    def expand_worker_task_group(self, worker):
        """Open the worker's collapsible group and return its <tbody>.

        WorkerTasksTable is a GroupedTable: header_columns are only index, status
        and name, so the header row shows the worker plus an "<n> tasks" summary,
        and each task is a sibling row hidden behind Alpine's x-show/x-cloak.
        Clicking the header row is the only way to bring the task columns into
        view - reading the table's text without this finds the worker but never
        the task name.
        """
        group = self.page.locator(self.WORKER_TASK_GROUP.format(worker=worker)).first
        group.wait_for(state="visible", timeout=20000)
        first_task_row = group.locator("tr").nth(1)
        if not first_task_row.is_visible():
            self._step(f"Expand the task group for '{worker}'")
            group.locator("tr").first.click()
            first_task_row.wait_for(state="visible", timeout=10000)
        return group

    def verify_worker_has_task(self, worker, task_type):
        content = self.page.locator(self.TAB_CONTENT).first
        content.wait_for(state="visible")
        assert worker in content.inner_text(), f"Worker '{worker}' not shown in Tasks tab"
        group = self.expand_worker_task_group(worker)
        text = group.inner_text()
        assert task_type in text, (
            f"Task type '{task_type}' not shown for '{worker}' once the group was expanded: {text!r}"
        )
        self._step(f"Workers Tasks tab shows '{task_type}' for '{worker}'")

    def worker_user_id(self, base_url, org_slug, opp_id, worker):
        """A worker's ConnectUser.user_id, read from a drill-down link.

        Needed because the per-worker Tasks page raises Http404 ("A valid worker
        must be specified.") unless the request carries ?user=<user_id>, and the
        Workers > Tasks tab cannot supply it - its name column is a plain
        UserInfoColumn with no link. The Delivery tab uses GroupedByWorkerMixin,
        whose render_user wraps the name in a link carrying the id.
        """
        self._step(f"Read the user_id for '{worker}' from the Delivery tab")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/workers/deliver/")
        self.page.wait_for_load_state("load")
        link = self.page.locator(self.WORKER_NAME_LINK.format(worker=worker)).first
        # Attached, not visible: the row's chevron variant of this link is
        # rendered with opacity-0 until the row is hovered.
        link.wait_for(state="attached", timeout=20000)
        match = re.search(r"[?&]user=([^&]+)", link.get_attribute("href") or "")
        assert match, f"The Delivery-tab link for '{worker}' carries no ?user= parameter"
        user_id = match.group(1)
        self._step(f"Worker '{worker}' has user_id {user_id}")
        return user_id

    def goto_worker_tasks_page(self, base_url, org_slug, opp_id, user_id):
        """Per-worker Visits/Tasks drill-down page (user_tasks).

        user_id is required - WorkerPageView 404s without it.
        """
        self._step("Navigate to worker drill-down Tasks page")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/user_tasks/?user={user_id}")
        self.page.wait_for_load_state("load")
        self._await_real_table()

    def _await_real_table(self):
        """Wait for the htmx table to replace its loading skeleton.

        The page ships a placeholder `<table class="base-table animate-pulse">` and
        swaps the real one in on load, so reading rows straight after the navigation
        can see an empty table and conclude there is nothing there - which silently
        skipped a leftover cleanup and left a task assigned.
        """
        try:
            self.page.locator("//table[not(contains(@class,'animate-pulse'))]").first.wait_for(
                state="visible", timeout=20000
            )
        except Exception:
            self._step("Table did not settle within 20s - continuing, assertions will report")

    # -- Visits tab of the worker page (TC-E2E-002 / TC-E2E-003) -----------------

    # The table sorts oldest-first by default (the view's queryset ends
    # .order_by("visit_date", "pk")) and pages at DEFAULT_PAGE_SIZE = 20, and
    # visit_rows() can only read the page it is on. The long-lived opportunity gains
    # two visits per run, so on 2026-08-14 it crossed 20 and the newest visit landed
    # on page 2: the test polled a full page 1 for 900s and reported the visit as
    # never processed, when it was one page over.
    #
    # Newest-first keeps the row we just created on page 1 whatever the history, and
    # is what the Date column header itself links to - "sort=-date_time" is lifted
    # from that header's href, not guessed. page_size is belt and braces: 100 is the
    # largest PAGE_SIZE_OPTIONS allows, so even with the sort silently ignored there
    # are 100 rows of slack instead of 20.
    VISITS_SORT_NEWEST_FIRST = "-date_time"
    VISITS_PAGE_SIZE = 100

    def goto_worker_visits_page(self, base_url, org_slug, opp_id, user_id):
        """The Visits tab of the per-worker page. Needs ?user= like the Tasks tab."""
        self._step("Navigate to the worker's Visits tab")
        self.page.goto(
            f"{base_url}/a/{org_slug}/opportunity/{opp_id}/user_visits/"
            f"?user={user_id}&sort={self.VISITS_SORT_NEWEST_FIRST}&page_size={self.VISITS_PAGE_SIZE}"
        )
        self.page.wait_for_load_state("load")
        self._await_real_table()  # same htmx skeleton as the Tasks tab
        self._warn_if_not_newest_first()

    @staticmethod
    def _row_date(row):
        """The leading "14-Aug-2026 06:35" of a visit row, or None if unparseable."""
        try:
            return datetime.strptime(row.split("\t")[0].strip(), "%d-%b-%Y %H:%M")
        except (ValueError, IndexError):
            return None

    def _warn_if_not_newest_first(self):
        """Say so if the sort did not take, rather than quietly reading a stale page.

        A renamed param or a column made unorderable would silently restore the
        oldest-first order, and the only symptom would be "visit never arrived" once
        the list outgrows a page - which is the failure this whole change is for.
        Warn rather than fail: reading the wrong page is our problem, not a product
        defect, and page_size still leaves 100 rows of slack.
        """
        dates = [d for d in (self._row_date(r) for r in self.visit_rows()) if d]
        if len(dates) > 1 and dates[0] < dates[-1]:
            self._step(
                f"WARNING: visits are oldest-first ({dates[0]:%d-%b %H:%M} .. {dates[-1]:%d-%b %H:%M}) - "
                f"the sort={self.VISITS_SORT_NEWEST_FIRST} param did not take. Relying on "
                f"page_size={self.VISITS_PAGE_SIZE}; fix the sort before the list outgrows it."
            )

    def visit_rows(self):
        rows = [r.strip() for r in self.page.locator(self.WORKER_VISIT_ROWS).all_inner_texts()]
        return [r for r in rows if r]

    def wait_for_visit(self, entity_name, timeout_seconds=900, poll_seconds=20):
        """Reload the Visits tab until a row mentions `entity_name`; return its text.

        A submission travels device -> CommCare HQ -> Connect's form receiver, which
        takes minutes on staging, so this polls rather than reading once. On timeout
        it prints every row it did see, since the alternative - a bare "not found" -
        gives no way to tell "not processed yet" from "entity name renders
        differently than expected".
        """
        deadline = time.monotonic() + timeout_seconds
        attempt = 0
        while True:
            attempt += 1
            self.page.reload(wait_until="load")
            self.page.wait_for_timeout(2500)  # the table arrives via htmx
            rows = self.visit_rows()
            match = next((r for r in rows if entity_name in r), None)
            self._step(f"Visit check {attempt} for '{entity_name}': {len(rows)} row(s)")
            if match:
                self._step(f"Visit row found: {match!r}")
                return match
            if time.monotonic() >= deadline:
                # Say what was actually looked at. The first time this fired for real
                # the visit had been processed all along and was simply on page 2,
                # and the bare message sent us hunting a non-existent lag.
                raise AssertionError(
                    f"No visit row mentioning '{entity_name}' after {timeout_seconds}s. "
                    f"Read {len(rows)} row(s) sorted {self.VISITS_SORT_NEWEST_FIRST} with "
                    f"page_size={self.VISITS_PAGE_SIZE}; if that count equals the page size the "
                    f"row may simply be on a later page. Rows seen: {rows or 'none'}"
                )
            self.page.wait_for_timeout(poll_seconds * 1000)

    # -- assigning and deleting from the worker's own Tasks page (TC-TAS-008) ----

    def worker_page_task_type_labels(self):
        """Task types offered by the Create Task modal on the worker Tasks page.

        The view passes the worker's access into CreateTaskForm, so this list
        already excludes types currently assigned to them.
        """
        self._step("Open Create Task modal on the worker Tasks page")
        self.click(self.WORKER_TASKS_CREATE_BTN)
        self.page.locator(self.CREATE_TASK_FORM).first.wait_for(state="visible", timeout=15000)
        options = self.page.locator(f"{self.TASK_SELECT} option").all_inner_texts()
        labels = [o.strip() for o in options if o.strip() and not o.strip().startswith("Select")]
        self._step(f"Worker-page task options: {labels}")
        return labels

    def create_task_from_worker_page(self, task_label, due_in_days=7):
        """Assign a task from the worker's own Tasks page.

        The modal here is NOT the same as the task list's: because the view knows
        the worker, CreateTaskForm sets access.initial and swaps that field for a
        HiddenInput, so only the task and due date are selectable. Driving a worker
        picker here would fail - there isn't one.

        Call worker_page_task_type_labels() first; it leaves the modal open.
        """
        self.select_tomselect_by_label("id_task", task_label, scope=self.CREATE_TASK_FORM)
        due = (date.today() + timedelta(days=due_in_days)).isoformat()
        self._step(f"Set due date {due}")
        self.page.locator(self.CREATE_TASK_FORM).locator("#id_due_date").fill(due)
        self._step(f"Save task '{task_label}' from the worker Tasks page")
        self.click_and_await_redirect(self.CREATE_TASK_SAVE_BTN)
        return due

    def verify_worker_task_row(self, slug, status="To Do"):
        row = self.page.locator(self.WORKER_TASK_ROW_BY_SLUG.format(slug=slug)).first
        row.wait_for(state="visible", timeout=20000)
        badge = self.page.locator(self.WORKER_TASK_STATUS_BY_SLUG.format(slug=slug)).first.inner_text().strip()
        assert badge == status, f"Task row for slug '{slug}' shows {badge!r}, expected {status!r}"
        self._step(f"Worker Tasks page row for '({slug})' is {status}")

    def worker_task_row_exists(self, slug):
        return self.page.locator(self.WORKER_TASK_ROW_BY_SLUG.format(slug=slug)).count() > 0

    def delete_worker_task_by_slug(self, slug):
        """Select the row for this task type and delete it from the worker page."""
        checkbox = self.page.locator(self.WORKER_TASK_ROW_CHECKBOX_BY_SLUG.format(slug=slug)).first
        checkbox.wait_for(state="visible", timeout=15000)
        assert checkbox.is_enabled(), f"Checkbox for '({slug})' is disabled - the task is completed, not pending"
        self._step(f"Select the task row for '({slug})'")
        checkbox.check()
        self._step("Click Delete Task(s) on the worker Tasks page")
        self.click(self.WORKER_TASKS_DELETE_BTN)
        self.page.locator(self.CONFIRM_MODAL_TITLE).first.wait_for(state="visible")
        self._step("Confirm deletion")
        self.click_and_await_redirect(self.CONFIRM_DELETE_BTN)

    def open_first_task_details(self):
        self._step("Open first task row's details panel")
        row = self.page.locator(self.DRILLDOWN_TASK_ROW).first
        row.wait_for(state="visible", timeout=20000)
        row.click()
        panel = self.page.locator(self.TASK_DETAILS_PANEL).first
        self.page.wait_for_timeout(2000)  # htmx load
        text = panel.inner_text()
        assert "select a task" not in text.lower(), "Details panel did not load after row click"
        self._step("Task details panel loaded")
        return text

    # ========================================================================
    # Worker List View (WLV_1-8) - migrated from Selenium ConnectWorkersPage.
    # These act on the list / Learn / Deliver tables under #table, reached via
    # flows.workers_setup (dashboard stat panel), not by URL.
    # ========================================================================

    def _await_list_table(self):
        """The Learn/Deliver tables htmx-swap into #table after the tab loads."""
        self.page.locator(self.LV_TABLE).first.wait_for(state="visible", timeout=30000)

    def _header_texts(self):
        """All <th> texts of the current table, positions preserved (blank headers
        kept) so a text index lines up with the matching <td> index."""
        self._await_list_table()
        return [h.strip() for h in self.page.locator(self.LV_TABLE).locator("thead th").all_inner_texts()]

    def verify_table_headers_present(self, expected_headers):
        actual = [h for h in self._header_texts() if h]
        actual_lower = [h.lower() for h in actual]
        missing = [h for h in expected_headers if h.lower() not in actual_lower]
        assert not missing, f"Missing headers: {missing}\nActual headers found: {actual}"
        self._step(f"Table headers present: {actual}")

    def verify_connect_workers_table_headers_present(self):
        self.verify_table_headers_present([
            "#", "Status", "Name", "Phone Number", "Invited Date", "Last Active",
            "Started Learn", "Completed Learn", "Time to Complete Learning",
            "First Delivery", "Time to Start Deliver",
        ])

    def verify_learn_table_headers_present(self):
        self.verify_table_headers_present([
            "#", "Name", "Last active", "Started Learning", "Modules completed",
            "Completed Learning", "Assessment", "Attempts", "Learning hours",
        ])

    # Numeric status columns whose cell values open a count-breakdown popup. Which
    # of these the Deliver tab shows depends on the opportunity's verification mode:
    # a manual-review opp exposes 'Pending', while an auto-verify opp shows a
    # 'Status' column instead and no 'Pending'. So the review-state column is
    # asserted as "Status or Pending", and callers act only on the columns present.
    DELIVER_COUNT_COLUMNS = ["Delivered", "Pending", "Approved", "Rejected"]

    def verify_deliver_table_headers_present(self):
        """The Deliver tab's stable columns, plus a review-state column that is
        'Pending' on manual-review opportunities and 'Status' on auto-verify ones."""
        actual = [h for h in self._header_texts() if h]
        actual_lower = [h.lower() for h in actual]
        core = ["#", "Name", "Last active", "Payment unit", "Delivery progress",
                "Delivered", "Approved", "Rejected"]
        missing = [h for h in core if h.lower() not in actual_lower]
        assert not missing, f"Missing headers: {missing}\nActual headers found: {actual}"
        assert "pending" in actual_lower or "status" in actual_lower, (
            f"Deliver table has neither a 'Pending' nor a 'Status' column: {actual}"
        )
        self._step(f"Deliver table headers present: {actual}")

    def present_deliver_count_columns(self):
        """Which of the numeric status columns this opportunity's Deliver tab shows."""
        actual_lower = [h.lower() for h in self._header_texts()]
        present = [c for c in self.DELIVER_COUNT_COLUMNS if c.lower() in actual_lower]
        self._step(f"Deliver count columns present: {present}")
        return present

    def click_tab_by_name(self, tab_name):
        """Click a workers-page tab (Learn / Deliver / Connect Workers) and confirm
        it activates. The table re-renders into #table via htmx after the click."""
        self._step(f"Click '{tab_name}' tab")
        self.click(self.LV_TAB_ITEM_BY_NAME.format(tab_name=tab_name))
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)  # table htmx-swaps into #table
        self.verify_tab_active(tab_name)

    def verify_tab_active(self, tab_name):
        tab = self.page.locator(self.LV_TAB_ITEM_BY_NAME.format(tab_name=tab_name)).first
        tab.wait_for(state="visible", timeout=15000)
        cls = tab.get_attribute("class") or ""
        assert "active" in cls, f"Tab '{tab_name}' is not active (class={cls!r})"
        self._step(f"Tab '{tab_name}' is active")

    def click_name_in_table(self, name):
        self._step(f"Open worker '{name}' from the table")
        self.click(self.LV_NAME_IN_TABLE.format(name=name))
        self.page.wait_for_load_state("load")

    def navigate_to_worker_visits(self, worker_name):
        """Deliver tab -> click a worker -> their Visits page (WVVP entry)."""
        self.click_tab_by_name("Deliver")
        self.click_name_in_table(worker_name)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1000)

    def click_and_verify_status_count_breakdown_for_item(self, item_name, column_name):
        """Click a status cell's value (e.g. worker row x 'Delivered', or the Total
        row) and confirm the breakdown popup opens. WLV_4 / WLV_5."""
        headers = self._header_texts()  # positions preserved for td alignment
        idx = next(
            (i for i, h in enumerate(headers) if h.lower() == column_name.strip().lower()),
            None,
        )
        assert idx is not None, f"Column '{column_name}' not found in {headers}"
        table = self.page.locator(self.LV_TABLE).first
        if item_name.strip().lower() == "total":
            row = table.locator("xpath=.//tbody//tr[td[normalize-space()='Total']]").first
        else:
            row = table.locator(
                f"xpath=.//tbody//tr[.//p[normalize-space()='{item_name.strip()}']]"
            ).first
        row.wait_for(state="visible", timeout=15000)
        span = row.locator("xpath=./td").nth(idx).locator("span").first
        self._step(f"Click {item_name!r} x {column_name!r} count")
        span.click()
        self.page.locator(self.COUNT_BREAKDOWN_POPUP).first.wait_for(state="visible", timeout=10000)
        self._step(f"Count breakdown popup shown for {item_name!r} / {column_name!r}")

    # -- Deliver-tab filters (WLV_8) ---------------------------------------------

    def open_filter_modal(self):
        # Idempotent: the modal is an x-show backdrop that stays open until Apply,
        # and while open it intercepts pointer events on the filter button, so a
        # second open-click would hang. Skip the click when it is already showing.
        modal = self.page.locator(self.LV_FILTER_MODAL).first
        if modal.is_visible():
            self._step("Deliver-tab filter modal already open")
            return
        self._step("Open deliver-tab filter modal")
        self.click(self.LV_FILTER_BUTTON)
        modal.wait_for(state="visible", timeout=15000)

    def apply_filters(self):
        self._step("Apply deliver-tab filters")
        self.click(self.LV_FILTER_APPLY)
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1500)

    def _reset_optional_filter(self, selector, value="---------"):
        """Reset a filter select if it is present (some fields render only when the
        opportunity has the matching feature enabled, e.g. has_overlimit)."""
        if self.page.locator(selector).count() > 0:
            self.select_by_visible_text(selector, value)

    def clear_all_filters_deliver_table(self):
        self.open_filter_modal()
        self.select_by_visible_text(self.FILTER_LAST_ACTIVE, "Any time")
        self._reset_optional_filter(self.FILTER_HAS_DUPLICATES)
        self._reset_optional_filter(self.FILTER_HAS_FLAGS)
        self._reset_optional_filter(self.FILTER_HAS_OVERLIMIT)
        self._reset_optional_filter(self.FILTER_REVIEW_PENDING)
        self.apply_filters()

    def apply_and_verify_last_active_1_day_ago(self):
        self.open_filter_modal()
        self.select_by_visible_text(self.FILTER_LAST_ACTIVE, "1 day ago")
        self.apply_filters()
        badge = self.page.locator(self.LV_FILTER_BADGE).first
        badge.wait_for(state="visible", timeout=10000)
        text = badge.inner_text().strip()
        assert text == "1", f"Filter badge value mismatch: expected '1', got {text!r}"
        self._step(f"'Last active: 1 day ago' filter applied (badge={text})")

    # -- Deliver-tab filter modal inspection (Delivery_tab_10/11/13/14/16) --------

    def filter_present(self, selector):
        return self.page.locator(selector).count() > 0

    def filter_field_options(self, selector):
        """The option labels of a filter <select> (assumes the modal is open)."""
        opts = [o.strip() for o in self.page.locator(f"{selector} option").all_inner_texts()]
        opts = [o for o in opts if o]
        self._step(f"Options for {selector}: {opts}")
        return opts

    def filter_badge_count(self):
        """The number on the filter button's badge, or 0 when no badge is shown."""
        badge = self.page.locator(self.LV_FILTER_BADGE)
        if badge.count() == 0:
            return 0
        text = badge.first.inner_text().strip()
        return int(text) if text.isdigit() else 0

    def apply_filter_combination(self, selections):
        """Open the modal, set several filters at once, apply, and return the badge
        count. `selections` is a list of (select_selector, label) pairs; a field not
        present for this opportunity (e.g. review_pending under auto-verify) is
        skipped so the same combination works on either verification mode."""
        self.open_filter_modal()
        applied = 0
        for selector, label in selections:
            if self.filter_present(selector):
                self.select_by_visible_text(selector, label)
                applied += 1
            else:
                self._step(f"Filter {selector} absent for this opportunity - skipped")
        self.apply_filters()
        count = self.filter_badge_count()
        self._step(f"Applied {applied} filter(s); badge shows {count}")
        return applied, count

    # -- Connect Workers list sorting (Connect_worker_17) ------------------------

    def click_list_column_sort(self, label):
        """Click a Connect Workers list column header's sort link and return the
        resulting ?sort= value. django-tables2 renders orderable headers as <a>
        links that cycle field -> -field; the table HTMX-reloads and mirrors the
        sort into the page URL (HX-Replace-Url)."""
        from urllib.parse import parse_qs, urlparse

        table = self.page.locator(self.LV_TABLE).first
        link = table.locator(
            f"xpath=.//thead//th[.//a[contains(normalize-space(),'{label}')]]//a"
        ).first
        link.wait_for(state="visible", timeout=15000)
        self._step(f"Sort Connect Workers list by '{label}'")
        link.click()
        self.page.wait_for_load_state("load")
        self.page.wait_for_timeout(1200)
        sort = parse_qs(urlparse(self.page.url).query).get("sort", [""])[0]
        self._step(f"URL sort param after click: {sort!r}")
        return sort

    def sortable_list_columns(self):
        """Which Connect Workers list headers expose a sort link."""
        table = self.page.locator(self.LV_TABLE).first
        table.wait_for(state="visible", timeout=20000)
        headers = table.locator("xpath=.//thead//th[.//a]")
        labels = [h.strip() for h in headers.all_inner_texts() if h.strip()]
        self._step(f"Sortable list columns: {labels}")
        return labels
