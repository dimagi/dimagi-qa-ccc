from utils.helpers import LocatorLoader

from pages.base_page import BasePage

locators = LocatorLoader()


class ConnectWorkersPage(BasePage):
    TASKS_TAB = locators.get("connect_workers_page", "tasks_tab")
    TAB_CONTENT = locators.get("connect_workers_page", "tab_content")
    DRILLDOWN_TASKS_TAB = locators.get("connect_workers_page", "drilldown_tasks_tab")
    TASK_DETAILS_PANEL = locators.get("connect_workers_page", "task_details_panel")
    DRILLDOWN_TASK_ROW = locators.get("connect_workers_page", "drilldown_task_row")

    def goto_workers_tasks_tab(self, base_url, org_slug, opp_id):
        """The Workers page Tasks tab (grouped per-worker table)."""
        self._step(f"Navigate to Workers > Tasks tab for opp {opp_id}")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/workers/tasks/")
        self.page.wait_for_load_state("load")
        self.page.locator(self.TAB_CONTENT).first.wait_for(state="visible", timeout=20000)

    def verify_worker_has_task(self, worker, task_type):
        content = self.page.locator(self.TAB_CONTENT).first
        content.wait_for(state="visible")
        text = content.inner_text()
        assert worker in text, f"Worker '{worker}' not shown in Tasks tab"
        assert task_type in text, f"Task type '{task_type}' not shown for '{worker}'"
        self._step(f"Workers Tasks tab shows '{task_type}' for '{worker}'")

    def goto_worker_tasks_page(self, base_url, org_slug, opp_id, user_id=None):
        """Per-worker Visits/Tasks drill-down page (user_tasks)."""
        url = f"{base_url}/a/{org_slug}/opportunity/{opp_id}/user_tasks/"
        if user_id:
            url += f"?user={user_id}"
        self._step("Navigate to worker drill-down Tasks page")
        self.page.goto(url)
        self.page.wait_for_load_state("load")

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
