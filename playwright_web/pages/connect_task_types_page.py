from utils.helpers import LocatorLoader, parse_org_and_opp

from pages.base_page import BasePage

locators = LocatorLoader()


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

    def verify_type_absent(self, name):
        # Archiving removes the task type from the config table entirely
        # (verified on staging 30-Jul-2026), it does not show an archived date.
        self.page.locator(self.ROW_BY_NAME.format(name=name)).first.wait_for(state="hidden", timeout=15000)
        self._step(f"Task type '{name}' no longer listed (archived)")

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

    def available_task_unit_labels(self):
        """Option labels currently offered by the Task Unit dropdown."""
        self.open_add_modal()
        options = self.page.locator(f"{self.TASK_UNIT_SELECT} option").all_inner_texts()
        self._step(f"Task unit dropdown options: {options}")
        self.click(self.CREATE_CANCEL_BTN)
        return [option.strip() for option in options]

    def _open_edit_modal(self, name):
        self._step(f"Open edit modal for task type '{name}'")
        self.click(self.ROW_EDIT_BTN_BY_NAME.format(name=name))
        self.page.locator(self.EDIT_FORM).wait_for(state="attached", timeout=15000)
        self.page.locator(self.EDIT_NAME_INPUT).first.wait_for(state="visible")

    def _save_edit_modal(self):
        # The form posts via htmx and the server answers with HX-Redirect;
        # wait for that navigation, or row assertions read the stale DOM.
        with self.page.expect_navigation(timeout=15000):
            self.click(self.EDIT_SAVE_BTN)
        self.page.wait_for_load_state("load")

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

    # -- dashboard tile ---------------------------------------------------------

    def is_tasks_tile_visible(self):
        visible = self.page.locator(self.TASKS_ASSIGNED_TILE).count() > 0
        self._step(f"'Tasks Assigned to Connect Workers' tile visible: {visible}")
        return visible
