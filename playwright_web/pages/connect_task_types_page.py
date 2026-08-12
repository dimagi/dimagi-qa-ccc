import re
from datetime import date

from utils.helpers import LocatorLoader, parse_org_and_opp

from pages.base_page import BasePage

locators = LocatorLoader()

# TaskTable renders exactly one date column - "Archived" - so the presence of a
# date in a row is equivalent to that task type being archived.
ROW_DATE = re.compile(r"\d{2}/\d{2}/\d{4}")


class ConnectTaskTypesPage(BasePage):
    MENU_TOGGLE = locators.get("opportunity_dashboard_page_menu", "menu_toggle")
    CONFIGURE_TASK_TYPES_LINK = locators.get("opportunity_dashboard_page_menu", "configure_task_types_link")
    TASKS_ASSIGNED_TILE = locators.get("opportunity_dashboard_page_menu", "tasks_assigned_tile")

    PAGE_HEADING = locators.get("connect_task_types_page", "page_heading")
    CONNECTED_APP_NAME = locators.get("connect_task_types_page", "connected_app_name")
    ADD_TASK_TYPE_BTN = locators.get("connect_task_types_page", "add_task_type_btn")
    CREATE_MODAL = locators.get("connect_task_types_page", "create_modal")
    TASK_UNIT_SELECT = locators.get("connect_task_types_page", "task_unit_select")
    CREATE_NAME_INPUT = locators.get("connect_task_types_page", "create_name_input")
    CREATE_DESCRIPTION_INPUT = locators.get("connect_task_types_page", "create_description_input")
    CASE_PROPERTY_INPUT = locators.get("connect_task_types_page", "case_property_input")
    CREATE_SAVE_BTN = locators.get("connect_task_types_page", "create_save_btn")
    CREATE_CANCEL_BTN = locators.get("connect_task_types_page", "create_cancel_btn")
    ROW_BY_NAME = locators.get("connect_task_types_page", "row_by_name")
    ROW_EDIT_BTN_BY_NAME = locators.get("connect_task_types_page", "row_edit_btn_by_name")
    EMPTY_TABLE_TEXT = locators.get("connect_task_types_page", "empty_table_text")
    EDIT_FORM = locators.get("connect_task_types_page", "edit_form")
    EDIT_NAME_INPUT = locators.get("connect_task_types_page", "edit_name_input")
    EDIT_DESCRIPTION_INPUT = locators.get("connect_task_types_page", "edit_description_input")
    ARCHIVE_CHECKBOX = locators.get("connect_task_types_page", "archive_checkbox")
    EDIT_SAVE_BTN = locators.get("connect_task_types_page", "edit_save_btn")

    # -- navigation ---------------------------------------------------------

    def open_from_dashboard_menu(self):
        """From the opportunity dashboard: kebab menu -> Configure Task Types."""
        self._step("Open menu on opportunity dashboard")
        self.click(self.MENU_TOGGLE)
        link = self.page.locator(self.CONFIGURE_TASK_TYPES_LINK).first
        link.wait_for(state="visible")
        self._step("Click 'Configure Task Types'")
        link.click()
        self.page.wait_for_url("**/task_types/**")

    def opportunity_ids_from_current_url(self):
        return parse_org_and_opp(self.page.url)

    def goto_task_types(self, base_url, org_slug, opp_id):
        self._step(f"Navigate to task types config for opp {opp_id}")
        self.page.goto(f"{base_url}/a/{org_slug}/opportunity/{opp_id}/task_types/")
        self.page.wait_for_load_state("load")

    # -- assertions -----------------------------------------------------------

    def verify_page_loaded(self, expected_app_name=None):
        self.page.locator(self.PAGE_HEADING).first.wait_for(state="visible")
        self._step("Task types config page loaded")
        connected = self.get_text(self.CONNECTED_APP_NAME)
        assert connected.strip(), "Connected Delivery App name is empty"
        if expected_app_name:
            assert expected_app_name in connected, (
                f"Connected app '{connected}' does not match expected '{expected_app_name}'"
            )
        self._step(f"Connected Delivery App: {connected}")

    def verify_no_task_types_yet(self):
        self.page.locator(self.EMPTY_TABLE_TEXT).first.wait_for(state="visible")
        self._step("Task type table is empty as expected")

    def verify_row_present(self, name):
        self.page.locator(self.ROW_BY_NAME.format(name=name)).first.wait_for(state="visible")
        self._step(f"Task type row '{name}' present")

    def verify_row_shows_unit(self, name, unit_name):
        # The Linked Task Unit column renders the unit's display name (unit_name),
        # not the slug - the slug never appears in the table.
        row = self.page.locator(self.ROW_BY_NAME.format(name=name)).first
        assert unit_name in row.inner_text(), f"Row for '{name}' does not show linked task unit '{unit_name}'"
        self._step(f"Row '{name}' shows linked task unit '{unit_name}'")

    def row_exists(self, name):
        return self.page.locator(self.ROW_BY_NAME.format(name=name)).count() > 0

    def find_existing_row(self, names):
        """First of `names` that has a row, or None.

        J1's sandbox type is renamed on every run (TC-TTC-005) and the slug is
        never rendered in the table, so the row has to be found by whichever of
        its two canonical names is currently in use.
        """
        for name in names:
            if self.row_exists(name):
                self._step(f"Found existing task type row '{name}'")
                return name
        self._step(f"No task type row named any of {names}")
        return None

    def verify_row_archived(self, name):
        # Archived rows stay listed, with the archive date (MM/DD/YYYY on
        # staging) in the Archived column - verified via network-instrumented
        # run on 30-Jul-2026.
        row = self.page.locator(self.ROW_BY_NAME.format(name=name)).first
        row.wait_for(state="visible")
        expected_date = date.today().strftime("%m/%d/%Y")
        text = row.inner_text()
        assert expected_date in text, (
            f"Row '{name}' does not show today's archive date {expected_date}: {text!r}"
        )
        self._step(f"Task type '{name}' shows archived date {expected_date}")

    def verify_row_not_archived(self, name):
        """Archived column empty again - EditTaskTypeForm.save() clears `archived`
        and restores is_active when the box is unticked."""
        row = self.page.locator(self.ROW_BY_NAME.format(name=name)).first
        row.wait_for(state="visible")
        text = row.inner_text()
        assert not ROW_DATE.search(text), f"Row '{name}' still shows an archived date: {text!r}"
        self._step(f"Task type '{name}' is no longer archived")

    # -- actions --------------------------------------------------------------

    def open_add_modal(self):
        self.click(self.ADD_TASK_TYPE_BTN)
        self.page.locator(self.CREATE_MODAL).first.wait_for(state="visible")

    def add_task_type(self, unit_label, case_property, expected_slug=None):
        """Create a task type from a task unit; returns the auto-filled name.

        expected_slug: the option VALUE of the selected task unit becomes the
        TaskType slug, so asserting it here is the slug-integrity check
        (TC-TTC-003) - the slug is not rendered anywhere on the page.
        """
        self.open_add_modal()
        self._step(f"Select task unit '{unit_label}'")
        self.select_by_visible_text(self.TASK_UNIT_SELECT, unit_label)
        if expected_slug:
            selected_value = self.page.locator(self.TASK_UNIT_SELECT).first.input_value()
            assert selected_value == expected_slug, (
                f"Task unit '{unit_label}' has slug {selected_value!r}, expected {expected_slug!r}"
            )
            self._step(f"Selected task unit slug verified: '{selected_value}'")
        name_value = self.page.locator(self.CREATE_NAME_INPUT).first.input_value()
        assert name_value, "Name was not auto-filled after selecting the task unit"
        self._step(f"Name auto-filled: '{name_value}'")
        self.type(self.CASE_PROPERTY_INPUT, case_property)
        self._step("Save new task type")
        self.click(self.CREATE_SAVE_BTN)
        self.page.wait_for_load_state("load")
        return name_value

    def add_task_type_by_unit_value(self, unit_slug, case_property):
        """Create a task type from the task unit whose option VALUE is unit_slug.

        Selected by value rather than label because the two registered units have
        near-identical labels ("Relearn Task Unit" / "Relearn Task Unit 2"), and
        the value IS the slug the TaskType is saved with (AddTaskTypeForm.save).
        Returns the auto-filled name.
        """
        self.open_add_modal()
        self._step(f"Select task unit with slug '{unit_slug}'")
        self.page.locator(self.TASK_UNIT_SELECT).first.select_option(value=unit_slug)
        name_value = self.page.locator(self.CREATE_NAME_INPUT).first.input_value()
        assert name_value, "Name was not auto-filled after selecting the task unit"
        self._step(f"Name auto-filled: '{name_value}'")
        self.type(self.CASE_PROPERTY_INPUT, case_property)
        self._step("Save new task type")
        self.click_and_await_redirect(self.CREATE_SAVE_BTN)
        return name_value

    def available_task_unit_options(self):
        """(value, label) pairs currently offered by the Task Unit dropdown.

        AddTaskTypeForm excludes every slug already used on the deliver app, and
        that exclusion is unconditional - archiving a task type does NOT put its
        unit back. When nothing is left the select is disabled and carries only a
        "No available task units" placeholder, which has an empty value and so is
        filtered out here.
        """
        self.open_add_modal()
        options = self.page.locator(f"{self.TASK_UNIT_SELECT} option").evaluate_all(
            "els => els.map(e => [e.value, e.textContent.trim()])"
        )
        offered = [(value, label) for value, label in options if value]
        self._step(f"Task unit dropdown offers: {offered or 'nothing'}")
        self.click(self.CREATE_CANCEL_BTN)
        return offered

    def available_task_unit_labels(self):
        """Option labels currently offered by the Task Unit dropdown."""
        return [label for _value, label in self.available_task_unit_options()]

    def available_task_unit_values(self):
        """Option values (= task unit slugs) currently offered."""
        return [value for value, _label in self.available_task_unit_options()]

    def _open_edit_modal(self, name):
        self._step(f"Open edit modal for task type '{name}'")
        self.click(self.ROW_EDIT_BTN_BY_NAME.format(name=name))
        self.page.locator(self.EDIT_FORM).wait_for(state="attached", timeout=15000)
        self.page.locator(self.EDIT_NAME_INPUT).first.wait_for(state="visible")

    def _save_edit_modal(self):
        self.click_and_await_redirect(self.EDIT_SAVE_BTN)

    def edit_task_type_name(self, name, new_name, new_description):
        self._open_edit_modal(name)
        self.page.locator(self.EDIT_NAME_INPUT).first.fill(new_name)
        self.page.locator(self.EDIT_DESCRIPTION_INPUT).first.fill(new_description)
        self._step(f"Save task type rename to '{new_name}'")
        self._save_edit_modal()

    def archive_task_type(self, name):
        self._open_edit_modal(name)
        self._step(f"Archive task type '{name}'")
        checkbox = self.page.locator(self.ARCHIVE_CHECKBOX).first
        if not checkbox.is_checked():
            checkbox.check()
        self._save_edit_modal()

    def unarchive_task_type(self, name):
        """Untick "Archive this task type" - the reverse of archive_task_type.

        Keeps J1 repeatable: it archives only its own sandbox type and must put
        it back, or every later run (and J2-J4) loses an assignable type.
        """
        self._open_edit_modal(name)
        self._step(f"Unarchive task type '{name}'")
        checkbox = self.page.locator(self.ARCHIVE_CHECKBOX).first
        if checkbox.is_checked():
            checkbox.uncheck()
        self._save_edit_modal()

    # -- dashboard tile ---------------------------------------------------------

    def is_tasks_tile_visible(self):
        visible = self.page.locator(self.TASKS_ASSIGNED_TILE).count() > 0
        self._step(f"'Tasks Assigned to Connect Workers' tile visible: {visible}")
        return visible

    def open_task_list_from_dashboard_tile(self):
        """Click the 'Tasks Assigned to Connect Workers' card on the dashboard.

        The card is an anchor straight to .../assigned_tasks/, so this covers the
        navigation a PM actually uses to reach the Task List - the tests otherwise
        only ever go there by URL.
        """
        tile = self.page.locator(self.TASKS_ASSIGNED_TILE).first
        tile.wait_for(state="visible", timeout=20000)
        self._step("Click the 'Tasks Assigned to Connect Workers' dashboard card")
        tile.click()
        self.page.wait_for_url("**/assigned_tasks/**")
