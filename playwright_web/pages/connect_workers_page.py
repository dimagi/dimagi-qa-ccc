import re
import time
from datetime import date, timedelta

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

    # -- Visits tab of the worker page (TC-E2E-002 / TC-E2E-003) -----------------

    def goto_worker_visits_page(self, base_url, org_slug, opp_id, user_id):
        """The Visits tab of the per-worker page. Needs ?user= like the Tasks tab."""
        self._step("Navigate to the worker's Visits tab")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/user_visits/?user={user_id}")
        self.page.wait_for_load_state("load")

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
                raise AssertionError(
                    f"No visit row mentioning '{entity_name}' after {timeout_seconds}s. "
                    f"Rows on the page: {rows or 'none'}"
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
