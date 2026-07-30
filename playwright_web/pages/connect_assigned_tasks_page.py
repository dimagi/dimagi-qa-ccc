from datetime import date, timedelta

from utils.helpers import LocatorLoader

from pages.base_page import BasePage

locators = LocatorLoader()

EXPECTED_COLUMNS = ["Connect Worker", "Status", "Task Type", "Assigned Date", "Due Date", "Assigned By"]


class ConnectAssignedTasksPage(BasePage):
    PAGE_HEADING = locators.get("connect_assigned_tasks_page", "page_heading")
    METRIC_VALUE_BY_LABEL = locators.get("connect_assigned_tasks_page", "metric_value_by_label")
    TABLE_WRAPPER = locators.get("connect_assigned_tasks_page", "table_wrapper")
    CREATE_TASK_BTN = locators.get("connect_assigned_tasks_page", "create_task_btn")
    DELETE_TASKS_BTN = locators.get("connect_assigned_tasks_page", "delete_tasks_btn")
    FILTER_BTN = locators.get("connect_assigned_tasks_page", "filter_btn")
    COLUMN_HEADERS = locators.get("connect_assigned_tasks_page", "column_headers")
    ROW_BY_WORKER = locators.get("connect_assigned_tasks_page", "row_by_worker")
    ROW_CHECKBOX_BY_WORKER = locators.get("connect_assigned_tasks_page", "row_checkbox_by_worker")
    ROW_EDIT_BTN_BY_WORKER = locators.get("connect_assigned_tasks_page", "row_edit_btn_by_worker")
    STATUS_BADGE_BY_WORKER = locators.get("connect_assigned_tasks_page", "status_badge_by_worker")
    ALL_STATUS_BADGES = locators.get("connect_assigned_tasks_page", "all_status_badges")
    ALL_ROW_CHECKBOXES = locators.get("connect_assigned_tasks_page", "all_row_checkboxes")
    ALL_EDIT_BUTTONS = locators.get("connect_assigned_tasks_page", "all_edit_buttons")
    CREATE_TASK_FORM = locators.get("connect_assigned_tasks_page", "create_task_form")
    TASK_SELECT = locators.get("connect_assigned_tasks_page", "task_select")
    WORKER_SELECT = locators.get("connect_assigned_tasks_page", "worker_select")
    DUE_DATE_INPUT = locators.get("connect_assigned_tasks_page", "due_date_input")
    CREATE_TASK_SAVE_BTN = locators.get("connect_assigned_tasks_page", "create_task_save_btn")
    CREATE_TASK_CANCEL_BTN = locators.get("connect_assigned_tasks_page", "create_task_cancel_btn")
    FORM_ERROR_TEXT = locators.get("connect_assigned_tasks_page", "form_error_text")
    EDIT_ASSIGNED_FORM = locators.get("connect_assigned_tasks_page", "edit_assigned_form")
    EDIT_DUE_DATE_INPUT = locators.get("connect_assigned_tasks_page", "edit_due_date_input")
    EDIT_REASON_INPUT = locators.get("connect_assigned_tasks_page", "edit_reason_input")
    EDIT_ASSIGNED_SAVE_BTN = locators.get("connect_assigned_tasks_page", "edit_assigned_save_btn")
    CONFIRM_MODAL_TITLE = locators.get("connect_assigned_tasks_page", "confirm_modal_title")
    CONFIRM_DELETE_BTN = locators.get("connect_assigned_tasks_page", "confirm_delete_btn")
    SUCCESS_MESSAGE = locators.get("connect_assigned_tasks_page", "success_message")
    FILTER_STATUS_SELECT = locators.get("connect_assigned_tasks_page", "filter_status_select")
    FILTER_TASK_TYPE_SELECT = locators.get("connect_assigned_tasks_page", "filter_task_type_select")
    FILTER_APPLY_BTN = locators.get("connect_assigned_tasks_page", "filter_apply_btn")

    # -- navigation / structure -----------------------------------------------

    def goto_task_list(self, base_url, org_slug, opp_id):
        self._step(f"Navigate to assigned task list for opp {opp_id}")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/assigned_tasks/")
        self.page.wait_for_load_state("load")

    def verify_page_loaded(self):
        self.page.locator(self.PAGE_HEADING).first.wait_for(state="visible")
        self._step("Task List page loaded")

    def metric(self, label):
        value = self.get_text(self.METRIC_VALUE_BY_LABEL.format(label=label)).strip()
        self._step(f"Metric '{label}' = {value}")
        return int(value)

    def verify_columns(self):
        headers = [h.strip() for h in self.page.locator(self.COLUMN_HEADERS).all_inner_texts()]
        self._step(f"Table columns: {headers}")
        for col in EXPECTED_COLUMNS:
            assert col in headers, f"Missing column '{col}' in {headers}"
        assert "Task ID" not in headers, "Task ID column should have been removed (PR #1375)"
        return headers

    # -- create ------------------------------------------------------------------

    def open_create_modal(self):
        self._step("Open Create Task modal")
        self.click(self.CREATE_TASK_BTN)
        # modal is a <template x-if> - the form only exists after the click
        self.page.locator(self.CREATE_TASK_FORM).first.wait_for(state="visible", timeout=15000)

    def cancel_create_modal(self):
        self.click(self.CREATE_TASK_CANCEL_BTN)
        self.page.wait_for_timeout(500)

    def create_modal_task_type_labels(self):
        self.open_create_modal()
        options = self.page.locator(f"{self.TASK_SELECT} option").all_inner_texts()
        labels = [o.strip() for o in options if o.strip() and not o.strip().startswith("Select")]
        self._step(f"Create Task modal task options: {labels}")
        self.cancel_create_modal()
        return labels

    def _fill_create_form(self, task_type, worker, due_in_days):
        self.open_create_modal()
        self.select_tomselect_by_label("id_task", task_type, scope=self.CREATE_TASK_FORM)
        self.select_tomselect_by_label("id_access", worker, scope=self.CREATE_TASK_FORM)
        due = (date.today() + timedelta(days=due_in_days)).isoformat()
        self._step(f"Set due date {due}")
        self.page.locator(self.CREATE_TASK_FORM).locator("#id_due_date").fill(due)
        return due

    def create_task(self, task_type, worker, due_in_days=7):
        due = self._fill_create_form(task_type, worker, due_in_days)
        self._step(f"Save task '{task_type}' for '{worker}'")
        self.click(self.CREATE_TASK_SAVE_BTN)
        self.page.wait_for_load_state("load")
        return due

    def attempt_duplicate_task(self, task_type, worker, due_in_days=7):
        """Submit a duplicate assignment; returns the validation error text."""
        self._fill_create_form(task_type, worker, due_in_days)
        self._step("Submit expected-duplicate assignment")
        self.click(self.CREATE_TASK_SAVE_BTN)
        error = self.page.locator(self.FORM_ERROR_TEXT).first
        error.wait_for(state="visible", timeout=15000)
        text = error.inner_text().strip()
        self._step(f"Duplicate assignment rejected with: {text}")
        self.cancel_create_modal()
        return text

    # -- row assertions -------------------------------------------------------------

    def verify_success_message(self, fragment):
        banner = self.page.locator(self.SUCCESS_MESSAGE).first
        banner.wait_for(state="visible", timeout=15000)
        text = banner.inner_text()
        assert fragment in text, f"Expected success message containing {fragment!r}, got {text!r}"
        self._step(f"Success message shown: {text.strip()}")

    def verify_task_row(self, worker, task_type, due_date_iso=None, status="To Do"):
        row = self.page.locator(self.ROW_BY_WORKER.format(worker=worker)).first
        row.wait_for(state="visible", timeout=15000)
        text = row.inner_text()
        assert task_type in text, f"Row missing task type: {text!r}"
        badge = self.get_text(self.STATUS_BADGE_BY_WORKER.format(worker=worker)).strip()
        assert badge == status, f"Expected status {status!r}, got {badge!r}"
        if due_date_iso:
            due = date.fromisoformat(due_date_iso)
            candidates = {
                due.strftime("%b %d, %Y"),
                due.strftime("%d %b %Y"),
                due.strftime("%m/%d/%Y"),
                due.strftime("%Y-%m-%d"),
                due.strftime("%b. %d, %Y"),
            }
            assert any(fmt in text for fmt in candidates), (
                f"Row does not show due date {due_date_iso} in any known format: {text!r}"
            )
        self._step(f"Task row verified for '{worker}': {status}, {task_type}")

    def row_exists(self, worker):
        return self.page.locator(self.ROW_BY_WORKER.format(worker=worker)).count() > 0

    # -- edit ---------------------------------------------------------------------

    def edit_due_date(self, worker, due_in_days, reason):
        self._step(f"Edit due date for '{worker}'s task")
        self.click(self.ROW_EDIT_BTN_BY_WORKER.format(worker=worker))
        self.page.locator(self.EDIT_ASSIGNED_FORM).wait_for(state="attached", timeout=15000)
        due = (date.today() + timedelta(days=due_in_days)).isoformat()
        self.page.locator(self.EDIT_DUE_DATE_INPUT).first.fill(due)
        self.page.locator(self.EDIT_REASON_INPUT).first.fill(reason)
        self.click(self.EDIT_ASSIGNED_SAVE_BTN)
        self.page.wait_for_load_state("load")
        return due

    # -- delete ---------------------------------------------------------------------

    def delete_tasks_for_workers(self, workers):
        for worker in set(workers):
            self._step(f"Select task row(s) for '{worker}'")
            for box in self.page.locator(self.ROW_CHECKBOX_BY_WORKER.format(worker=worker)).all():
                if box.is_enabled():
                    box.check()
        self._step("Click Delete Task(s)")
        self.click(self.DELETE_TASKS_BTN)
        self.page.locator(self.CONFIRM_MODAL_TITLE).first.wait_for(state="visible")
        self._step("Confirm deletion")
        self.click(self.CONFIRM_DELETE_BTN)
        self.page.wait_for_load_state("load")

    # -- filters ------------------------------------------------------------------------

    def apply_status_filter(self, status_label):
        self._step(f"Filter by status '{status_label}'")
        self.click(self.FILTER_BTN)
        self.page.locator(self.FILTER_STATUS_SELECT).first.wait_for(state="visible")
        self.select_by_visible_text(self.FILTER_STATUS_SELECT, status_label)
        self.click(self.FILTER_APPLY_BTN)
        self.page.wait_for_timeout(2000)  # htmx swaps #task-list-table

    def clear_filters(self):
        self._step("Clear filters via URL reload")
        base = self.page.url.split("?")[0]
        self.page.goto(base)
        self.page.wait_for_load_state("load")

    def visible_status_badges(self):
        badges = [b.strip() for b in self.page.locator(self.ALL_STATUS_BADGES).all_inner_texts()]
        self._step(f"Visible status badges: {badges}")
        return badges

    # -- permissions -----------------------------------------------------------------------

    def manage_controls_visible(self):
        create_visible = self.page.locator(self.CREATE_TASK_BTN).count() > 0
        delete_visible = self.page.locator(self.DELETE_TASKS_BTN).count() > 0
        checkbox_visible = self.page.locator(self.ALL_ROW_CHECKBOXES).count() > 0
        self._step(
            f"Manage controls - create: {create_visible}, delete: {delete_visible}, checkboxes: {checkbox_visible}"
        )
        return create_visible, delete_visible, checkbox_visible

    def edit_buttons_visible(self):
        visible = self.page.locator(self.ALL_EDIT_BUTTONS).count() > 0
        self._step(f"Edit buttons visible: {visible}")
        return visible
