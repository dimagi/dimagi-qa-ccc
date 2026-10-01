# Tasking Web Automation Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate the Connect web tasking (re-learn) workflow — CCCT-2658 — as 4 journey tests (J1 task-type config, J2 assignment lifecycle, J3 views/filters, J4 permissions) in `playwright_web/`, plus a reusable-setup refactor of the existing OLP flow.

**Architecture:** Extract the OLP end-to-end setup (CCHQ login → app copies → program handshake → opportunity/budget) from `test_olp_01_02_03.py` into a `flows/olp_setup.py` module both old and new tests call. Add three page objects for the tasking UI (task types config, assigned task list, workers/tasks views) driven by locators extracted from the commcare-connect templates at origin/main. J1 runs against a fresh per-run opportunity (task-type slugs are unique per app, so only a fresh app copy guarantees a creatable type); J2–J4 run against a designated static opportunity with enrolled workers and **self-skip** until that opportunity is recorded in test data — CI stays green meanwhile.

**Tech Stack:** pytest + pytest-playwright (sync), page-object model with YAML locators (`LocatorLoader`), pytest-html reporting with `STEP` logging, staging env `connect-staging.dimagi.com` + `staging.commcarehq.org/a/connectqa-automation`.

**Test plan traceability:** `Tasking_Workflow_Automation_Test_Plan.xlsx` — Automation Target column values J1–J4 map to the four test files below.

**Key facts (verified against commcare-connect origin/main and staging on 30-Jul-2026):**
- Task unit in master deliver app "[08/12] Delivey App": slug `relearn_task`, name `Relearn Task Unit` (saved state; automation copies inherit it and build+release the copy).
- Create Task modal is inside `<template x-if>` — NOT in DOM until the + button is clicked; `#id_task`/`#id_access` are TomSelect widgets. All other modals are `x-show` + `x-cloak` (in DOM, hidden).
- Task-type modal's `#id_task_unit_id` is a **native** select; selecting fires Alpine autofill of `#id_name`/`#id_description`.
- `#id_name`/`#id_description`/`#id_due_date` ids are duplicated across create/edit modals — always scope to the form/modal.
- Edit flows are two-step htmx: click Edit → wait for `#edit-task-form-el` / `#edit-assigned-task-form-el` → interact → Save button sits OUTSIDE the form (`button[form=...]`).
- Success feedback = Django message banner `div.bg-message-success` after HX-Redirect.
- The dashboard "Tasks Assigned to Connect Workers" tile requires the `worker_visits_tasks` waffle switch AND ≥1 active task type. Switch state unconfirmed → tile assertions are gated by `TASKING.switch_enabled` in test data.

---

## Task 0: Worktree + environment

The user's checkout `C:\Users\DIMAGI\PythonScripts\dimagi-qa-ccc` is on `feature/connect-test-migration-pilot` (open PR #22) with local modifications — do not work there.

- [ ] **Step 0.1: Create worktree and branch**

```bash
git -C /c/Users/DIMAGI/PythonScripts/dimagi-qa-ccc worktree add /c/dqccc-tasking -b feature/tasking-web-automation feature/connect-test-migration-pilot
```

Expected: `HEAD is now at db590a6 ...`. All subsequent file paths are relative to `C:\dqccc-tasking`.

- [ ] **Step 0.2: Copy untracked credentials file**

```powershell
Copy-Item C:\Users\DIMAGI\PythonScripts\dimagi-qa-ccc\settings.cfg C:\dqccc-tasking\settings.cfg
```

- [ ] **Step 0.3: Ensure deps + browser present**

```powershell
python -m pip install -r C:\dqccc-tasking\playwright_web\requirements.txt; python -m playwright install chromium
```

Expected: "Requirement already satisfied" lines are fine; chromium download skipped if cached.

- [ ] **Step 0.4: Sanity-run the framework unit tests**

```powershell
cd C:\dqccc-tasking\playwright_web; python -m pytest tests/test_helpers.py tests/test_base_page.py -p no:playwright -v
```

Expected: all PASS. (`-p no:playwright` avoids launching a browser for pure-python tests; drop the flag if the plugin objects.)

---

## Task 1: URL parsing helper (TDD)

Tasking pages are reached by URL construction (`/a/{org_slug}/opportunity/{opp_id}/...`) because the assigned-tasks page has no nav entry. We need to parse org/opp from the dashboard URL.

**Files:**
- Modify: `playwright_web/utils/helpers.py` (append)
- Test: `playwright_web/tests/test_helpers.py` (append)

- [ ] **Step 1.1: Write the failing tests** — append to `playwright_web/tests/test_helpers.py`:

```python
from utils.helpers import parse_org_and_opp


class TestParseOrgAndOpp:
    def test_parses_dashboard_url(self):
        url = "https://connect-staging.dimagi.com/a/pm-automation-01/opportunity/612/"
        assert parse_org_and_opp(url) == ("pm-automation-01", "612")

    def test_parses_nested_page_url(self):
        url = "https://connect-staging.dimagi.com/a/my-org/opportunity/45/workers/tasks/?x=1"
        assert parse_org_and_opp(url) == ("my-org", "45")

    def test_raises_on_non_opportunity_url(self):
        import pytest as _pytest
        with _pytest.raises(ValueError):
            parse_org_and_opp("https://connect-staging.dimagi.com/a/my-org/program/")
```

- [ ] **Step 1.2: Run to verify failure**

Run: `python -m pytest tests/test_helpers.py -k ParseOrgAndOpp -p no:playwright -v`
Expected: FAIL — `ImportError: cannot import name 'parse_org_and_opp'`

- [ ] **Step 1.3: Implement** — append to `playwright_web/utils/helpers.py`:

```python
import re


def parse_org_and_opp(url):
    """Extract (org_slug, opp_id) from any Connect opportunity URL.

    Connect URLs look like https://<host>/a/<org_slug>/opportunity/<opp_id>/...
    The assigned-tasks page has no navigation entry, so tasking tests build its
    URL from these parts.
    """
    match = re.search(r"/a/([^/]+)/opportunity/(\d+)", url)
    if not match:
        raise ValueError(f"Not an opportunity URL: {url}")
    return match.group(1), match.group(2)
```

(`import re` goes at the top of the file with the other imports.)

- [ ] **Step 1.4: Run to verify pass**

Run: `python -m pytest tests/test_helpers.py -k ParseOrgAndOpp -p no:playwright -v`
Expected: 3 PASS

- [ ] **Step 1.5: Commit**

```bash
git add playwright_web/utils/helpers.py playwright_web/tests/test_helpers.py
git commit -m "Add parse_org_and_opp URL helper for tasking page navigation"
```

---

## Task 2: Extract reusable OLP setup flow

**Files:**
- Create: `playwright_web/flows/__init__.py` (empty)
- Create: `playwright_web/flows/olp_setup.py`
- Modify: `playwright_web/tests/test_olp_01_02_03.py` (thin wrapper over flows)

- [ ] **Step 2.1: Create `playwright_web/flows/olp_setup.py`** — code moved verbatim from `test_olp_01_02_03.py` (same call order, same waits):

```python
"""Reusable OLP setup flows shared by the OLP regression test and the tasking
journey tests. Extracted from test_olp_01_02_03 - behavior must stay identical."""

from dataclasses import dataclass

from pages.cchq_application_page import CCHQApplicationPage
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_programs_page import ConnectProgramsPage

PM_ORG = "PM_Automation_01"
LEARN_APP_MASTER = "[08/12] Learn App"
DELIVER_APP_MASTER = "[08/12] Delivey App"


@dataclass
class OlpSetup:
    connect_page: object
    program_name: str
    opportunity_name: str
    learn_app_name: str
    delivery_app_name: str


def login_cchq_and_copy_master_apps(page, config, settings):
    """CCHQ login + copy Learn/Deliver masters, returns (learn_copy, deliver_copy)."""
    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_application_page = CCHQApplicationPage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()

    cchq_home_page.select_app_under_applications_tab(LEARN_APP_MASTER)
    learn_app_name = cchq_application_page.create_copy_of_learn_app()
    cchq_home_page.verify_app_present_under_applications_tab(learn_app_name)

    cchq_home_page.select_app_under_applications_tab(DELIVER_APP_MASTER)
    delivery_app_name = cchq_application_page.create_copy_of_delivery_app()
    cchq_home_page.verify_app_present_under_applications_tab(delivery_app_name)
    return learn_app_name, delivery_app_name


def open_connect_as_org(page, config, organization=PM_ORG):
    """Open Connect in a new tab, OAuth in via CCHQ, select the organization."""
    connect_page = LoginPage(page).navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list(organization)
    return connect_page


def create_program_with_nm_handshake(connect_page, olp1_data):
    """PM creates program and invites the NM org, NM applies, PM accepts."""
    connect_home_page = ConnectHomePage(connect_page)
    connect_programs_page = ConnectProgramsPage(connect_page)

    connect_home_page.click_programs_in_sidebar()
    program_name = connect_programs_page.create_program(olp1_data)
    connect_programs_page.invite_network_manager(program_name, olp1_data["network_manager"])

    connect_home_page.select_organization_from_list(olp1_data["network_manager"])
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.apply_to_program(program_name)

    connect_home_page.select_organization_from_list(PM_ORG)
    connect_home_page.click_programs_in_sidebar()
    connect_programs_page.accept_application(program_name, olp1_data["network_manager"])
    return program_name


def create_opportunity_with_budget(connect_page, config, test_data, program_name, learn_app_name, delivery_app_name):
    """Create opportunity under the program, add payment unit, set budget."""
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")
    connect_programs_page = ConnectProgramsPage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)

    connect_programs_page.open_create_opportunity_form(program_name, olp1_data["network_manager"])
    env = "staging" if "staging" in config.get("cchq_url") else "prod"
    opportunity_name = connect_opp_page.create_opportunity_in_connect_page(
        olp1_data, learn_app_name, delivery_app_name, env, network_manager=olp1_data["network_manager_slug"]
    )
    connect_opp_page.create_payment_unit_in_connect_page(olp2_data)
    connect_opp_page.setup_budget_in_connect_page(olp3_data)
    return opportunity_name


def full_olp_setup(page, config, settings, test_data):
    """Complete OLP flow: apps copied, program handshake done, opportunity ready."""
    learn_app_name, delivery_app_name = login_cchq_and_copy_master_apps(page, config, settings)
    connect_page = open_connect_as_org(page, config)
    olp1_data = test_data.get("OLP_1")
    program_name = create_program_with_nm_handshake(connect_page, olp1_data)
    opportunity_name = create_opportunity_with_budget(
        connect_page, config, test_data, program_name, learn_app_name, delivery_app_name
    )
    return OlpSetup(connect_page, program_name, opportunity_name, learn_app_name, delivery_app_name)
```

- [ ] **Step 2.2: Create empty `playwright_web/flows/__init__.py`**

- [ ] **Step 2.3: Rewrite `playwright_web/tests/test_olp_01_02_03.py`** as a thin wrapper (must keep identical behavior):

```python
from flows.olp_setup import full_olp_setup


def test_olp_01_02_03_setup_budget_in_connect(page, test_data, config, settings):
    full_olp_setup(page, config, settings, test_data)
```

Note: the original test read `olp2_data`/`olp3_data` at the top; that moved into `create_opportunity_with_budget`. `create_opportunity_in_connect_page` returns the (timestamped) opportunity name — the original discarded it, the flow now returns it.

- [ ] **Step 2.4: Regression gate (TC-IMP-004) — run the refactored OLP test against staging**

Run: `cd C:\dqccc-tasking\playwright_web; python -m pytest tests/test_olp_01_02_03.py -v`
Expected: PASS in ~2 min (opens a headed browser — pytest.ini forces `--headed`).

- [ ] **Step 2.5: Commit**

```bash
git add playwright_web/flows playwright_web/tests/test_olp_01_02_03.py
git commit -m "Extract reusable OLP setup flow for tasking journey tests"
```

---

## Task 3: Locators + test data

**Files:**
- Modify: `playwright_web/locators/web_locators.yaml` (append sections; extend `opportunity_dashboard_page`)
- Modify: `test_data/web_test_data.yaml` (append `TASKING` block)

- [ ] **Step 3.1: Append to `playwright_web/locators/web_locators.yaml`:**

```yaml
# --- Tasking (CCCT-2658) ---

opportunity_dashboard_page_menu:
  menu_toggle: "//i[contains(@class,'fa-solid') and contains(@class,'cursor-pointer') and (contains(@class,'fa-bars') or contains(@class,'fa-xmark'))]"
  configure_task_types_link: "//a[normalize-space()='Configure Task Types']"
  tasks_assigned_tile: "//a[.//h3[normalize-space()='Tasks Assigned to Connect Workers']]"
  tasks_assigned_tile_count: "//a[.//h3[normalize-space()='Tasks Assigned to Connect Workers']]//h3[contains(@class,'text-2xl')]"

connect_task_types_page:
  page_heading: "//h2[contains(@class,'title') and normalize-space()='Configure Task Types']"
  connected_app_name: "//span[normalize-space()='Connected Delivery App:']/following-sibling::span[1]"
  add_task_type_btn: "//button[normalize-space()='Add New Task Type']"
  # New Task Type modal (x-show; scope everything to the backdrop containing its title)
  create_modal: "//div[contains(@class,'modal-backdrop')][.//h2[normalize-space()='New Task Type']]"
  task_unit_select: "id_task_unit_id"
  create_name_input: "//div[contains(@class,'modal-backdrop')][.//h2[normalize-space()='New Task Type']]//input[@id='id_name']"
  create_description_input: "//div[contains(@class,'modal-backdrop')][.//h2[normalize-space()='New Task Type']]//textarea[@id='id_description']"
  case_property_input: "id_case_property"
  create_save_btn: "//div[contains(@class,'modal-backdrop')][.//h2[normalize-space()='New Task Type']]//button[@type='submit'][normalize-space()='Save']"
  create_cancel_btn: "//div[contains(@class,'modal-backdrop')][.//h2[normalize-space()='New Task Type']]//button[normalize-space()='Cancel']"
  # Table
  row_by_name: "//table[contains(@class,'base-table')]//tr[.//td[normalize-space()='{name}']]"
  row_edit_btn_by_name: "//table[contains(@class,'base-table')]//tr[.//td[normalize-space()='{name}']]//button[.//i[contains(@class,'fa-pen-to-square')]]"
  empty_table_text: "//td[contains(normalize-space(),'No task types configured for this opportunity')]"
  # Edit Task Type modal (htmx-loaded form)
  edit_form: "edit-task-form-el"
  edit_name_input: "//form[@id='edit-task-form-el']//input[@id='id_name']"
  edit_description_input: "//form[@id='edit-task-form-el']//textarea[@id='id_description']"
  archive_checkbox: "id_is_archived"
  edit_save_btn: "//button[@form='edit-task-form-el'][normalize-space()='Save']"

connect_assigned_tasks_page:
  page_heading: "//h1[normalize-space()='Task List']"
  metric_value_by_label: "//div[contains(@class,'metric-card')][.//span[normalize-space()='{label}']]//span[contains(@class,'text-2xl')]"
  table_wrapper: "task-list-table"
  create_task_btn: "//div[@id='task-list-table']//button[@x-tooltip.raw='Create Task' or @aria-label='Create Task']"
  delete_tasks_btn: "//button[@x-tooltip.raw='Delete Task(s)' or @aria-label='Delete Task(s)']"
  filter_btn: "//div[@id='task-list-table']//button[contains(@class,'button-icon')][.//i[contains(@class,'fa-sliders')]]"
  column_headers: "//div[@id='task-list-table']//table//th"
  row_by_worker: "//div[@id='task-list-table']//table//tr[contains(@class,'group')][.//p[normalize-space()='{worker}']]"
  row_checkbox_by_worker: "//div[@id='task-list-table']//table//tr[contains(@class,'group')][.//p[normalize-space()='{worker}']]//input[@name='row_select']"
  row_edit_btn_by_worker: "//div[@id='task-list-table']//table//tr[contains(@class,'group')][.//p[normalize-space()='{worker}']]//button[.//i[contains(@class,'fa-pen-to-square')]]"
  status_badge_by_worker: "//div[@id='task-list-table']//table//tr[contains(@class,'group')][.//p[normalize-space()='{worker}']]//span[contains(@class,'bg-amber-100') or contains(@class,'bg-green-100')]"
  # Create Task modal (template x-if - absent from DOM until + clicked)
  create_task_form: "create-task-form"
  task_select: "id_task"
  worker_select: "id_access"
  due_date_input: "id_due_date"
  create_task_save_btn: "//form[@id='create-task-form']//button[@type='submit']"
  create_task_cancel_btn: "//div[@id='create-task-form-wrapper']/ancestor::div[contains(@class,'modal-backdrop')]//button[normalize-space()='Cancel']"
  form_error_text: "//div[@id='create-task-form-wrapper']//*[contains(@class,'invalid-feedback') or contains(@class,'text-red') or contains(@class,'errorlist') or contains(@class,'alert')]"
  # Edit Assigned Task modal (htmx-loaded form)
  edit_assigned_form: "edit-assigned-task-form-el"
  edit_due_date_input: "//form[@id='edit-assigned-task-form-el']//input[@id='id_due_date']"
  edit_reason_input: "id_reason"
  edit_assigned_save_btn: "//button[@form='edit-assigned-task-form-el']"
  # Confirm modal + messages
  confirm_modal_title: "confirm-modal-title"
  confirm_delete_btn: "//div[contains(@class,'modal-backdrop')][.//h2[@id='confirm-modal-title']]//button[.//span[normalize-space()='Delete'] or normalize-space()='Delete']"
  success_message: "//div[contains(@class,'bg-message-success')]"
  # Filter modal
  filter_form: "assignedTaskFilterForm"
  filter_status_select: "id_task_status"
  filter_task_type_select: "id_task_type"
  filter_apply_btn: "//button[@form='assignedTaskFilterForm'][@type='submit']"
  filter_close_btn: "//div[@id='assignedTaskFilterForm']/ancestor::div[contains(@class,'modal-backdrop')]//button[normalize-space()='Close']"

connect_workers_page:
  tasks_tab: "tasks-tab"
  tab_content: "table"
  loading_indicator: "loadingIndicator"
  worker_group_row_by_name: "//div[@id='table']//tr[.//text()[contains(., '{worker}')]] | //div[@id='table']//*[contains(@class,'accordion')][contains(., '{worker}')]"
  # Worker drill-down (user_tasks page)
  drilldown_tasks_tab: "//a[contains(@class,'tab') and normalize-space()='Tasks']"
  task_details_panel: "task-details"
```

Note on `filter_form`: the shared filter component renders the form with `id="assignedTaskFilterForm"` — the close-button xpath climbs from it. If the Apply/Close footer turns out to sit outside the form's ancestor backdrop on the live page, fix the xpath during the J2 run (all filter locators are exercised there).

- [ ] **Step 3.2: Append to `test_data/web_test_data.yaml`:**

```yaml
TASKING:
  task_unit_name: "Relearn Task Unit"       # visible label in the Task Unit dropdown
  task_unit_slug: "relearn_task"            # must match HQ Task Unit ID exactly
  case_property: "relearn_complete"
  edited_type_name: "Relearn Task Unit (edited)"
  switch_enabled: false        # set true once waffle switch worker_visits_tasks is confirmed ON
  # --- Static opportunity for J2/J3/J4 (fill in to un-skip those tests) ---
  static_opp: ""               # opportunity name as shown in the list, e.g. "Tasking Static Opp"
  static_org: ""               # PM org slug in URLs, e.g. "pm-automation-01"
  static_nm_org: ""            # NM org slug for permission tests
  static_nm_org_name: ""       # NM org display name for the org switcher
  static_worker: ""            # enrolled worker display name, e.g. "Deb Test 8/12"
  static_task_type: "Relearn Task Unit"     # pre-created task type on the static opp
  static_task_type_2: ""       # optional second type - enables the bulk-delete path
```

- [ ] **Step 3.3: Check the stale `learn_app`/`deliver_app` keys before removing**

Run: `grep -rn "learn_app\"\|deliver_app\"\|\['learn_app'\]\|\['deliver_app'\]" playwright_web/ tests/ pages/ 2>/dev/null` (also grep the repo-root Selenium suite: `grep -rn "learn_app\b" pages/ tests/ --include=*.py | head -20`)
Expected: the Playwright suite does not read `OLP_1.learn_app` / `OLP_1.deliver_app` (it hardcodes the "[08/12]" masters, now in `flows/olp_setup.py`). **If the legacy Selenium suite reads them, leave them in place** and only add a comment `# stale for playwright suite - masters are hardcoded in flows/olp_setup.py`. Only delete if nothing reads them.

- [ ] **Step 3.4: Commit**

```bash
git add playwright_web/locators/web_locators.yaml test_data/web_test_data.yaml
git commit -m "Add tasking locators and TASKING test data block"
```

---

## Task 4: BasePage TomSelect helper + ConnectTaskTypesPage

**Files:**
- Modify: `playwright_web/pages/base_page.py` (append one method)
- Create: `playwright_web/pages/connect_task_types_page.py`

- [ ] **Step 4.1: Append to `BasePage`** (`playwright_web/pages/base_page.py`), following the existing `_step` logging convention:

```python
    def select_tomselect_by_label(self, select_id, label, scope=None):
        """Pick an option in a TomSelect-enhanced <select> by driving its UI.

        TomSelect hides the native select and renders a .ts-wrapper sibling;
        plain select_option() would set the value without updating the widget.
        scope: optional container selector to disambiguate duplicated ids.
        """
        self._step(f"Select '{label}' in TomSelect #{select_id}")
        root = self.page.locator(scope) if scope else self.page
        root.locator(f"#{select_id} ~ .ts-wrapper .ts-control").first.click()
        self.page.locator(f".ts-dropdown .option:has-text('{label}')").first.click()
        self.page.wait_for_timeout(300)
```

- [ ] **Step 4.2: Create `playwright_web/pages/connect_task_types_page.py`:**

```python
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

    # -- navigation -------------------------------------------------------

    def open_from_dashboard_menu(self):
        """From the opportunity dashboard: kebab menu -> Configure Task Types."""
        self._step("Open kebab menu on opportunity dashboard")
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

    # -- assertions --------------------------------------------------------

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

    def verify_row_shows_slug(self, name, slug):
        row = self.page.locator(self.ROW_BY_NAME.format(name=name)).first
        assert slug in row.inner_text(), f"Row for '{name}' does not show linked task unit '{slug}'"
        self._step(f"Row '{name}' shows linked task unit '{slug}'")

    def verify_row_archived(self, name):
        row = self.page.locator(self.ROW_BY_NAME.format(name=name)).first
        row.wait_for(state="visible")
        text = row.inner_text()
        assert any(ch.isdigit() for ch in text.split(name)[-1]), (
            f"Row '{name}' shows no archived date after archiving: {text!r}"
        )
        self._step(f"Task type '{name}' shows archived date")

    # -- actions -----------------------------------------------------------

    def open_add_modal(self):
        self.click(self.ADD_TASK_TYPE_BTN)
        self.page.locator(self.CREATE_MODAL).first.wait_for(state="visible")

    def add_task_type(self, unit_label, case_property):
        """Create a task type; returns the auto-filled name."""
        self.open_add_modal()
        self._step(f"Select task unit '{unit_label}'")
        self.select_by_visible_text(self.TASK_UNIT_SELECT, unit_label)
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
        return [o.strip() for o in options]

    def _open_edit_modal(self, name):
        self._step(f"Open edit modal for task type '{name}'")
        self.click(self.ROW_EDIT_BTN_BY_NAME.format(name=name))
        self.page.locator(f"#{'edit-task-form-el'}").wait_for(state="attached", timeout=15000)
        self.page.locator(self.EDIT_NAME_INPUT).first.wait_for(state="visible")

    def edit_task_type_name(self, name, new_name, new_description):
        self._open_edit_modal(name)
        self.page.locator(self.EDIT_NAME_INPUT).first.fill(new_name)
        self.page.locator(self.EDIT_DESCRIPTION_INPUT).first.fill(new_description)
        self._step(f"Save task type rename to '{new_name}'")
        self.click(self.EDIT_SAVE_BTN)
        self.page.wait_for_load_state("load")

    def archive_task_type(self, name):
        self._open_edit_modal(name)
        self._step(f"Archive task type '{name}'")
        checkbox = self.page.locator(self.ARCHIVE_CHECKBOX).first
        if not checkbox.is_checked():
            checkbox.check()
        self.click(self.EDIT_SAVE_BTN)
        self.page.wait_for_load_state("load")

    # -- dashboard tile ------------------------------------------------------

    def is_tasks_tile_visible(self):
        visible = self.page.locator(self.TASKS_ASSIGNED_TILE).count() > 0
        self._step(f"'Tasks Assigned to Connect Workers' tile visible: {visible}")
        return visible
```

Note: `LocatorLoader.get` turns `edit-task-form-el` style bare ids into `#...` selectors, and the `select_by_visible_text` on the native task-unit select fires the `change` event Alpine listens to (Playwright's `select_option` dispatches `change`); the auto-fill assertion in `add_task_type` verifies it worked.

- [ ] **Step 4.3: Commit**

```bash
git add playwright_web/pages/base_page.py playwright_web/pages/connect_task_types_page.py
git commit -m "Add TomSelect helper and task types config page object"
```

---

## Task 5: J1 — test_task_type_config.py

**Files:**
- Create: `playwright_web/tests/test_task_type_config.py`

Covers TC-TTC-001..006, TC-TAS-005 (archived type absent from Create Task dropdown, checked on the fresh opp), TC-IMP-003 light (tile absent before type exists / present after — only when `switch_enabled`).

- [ ] **Step 5.1: Write the test:**

```python
import pytest

from flows.olp_setup import full_olp_setup
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_task_types_page import ConnectTaskTypesPage


def test_task_type_config_journey(page, test_data, config, settings):
    """J1 - TC-TTC-001..006, TC-TAS-005, TC-IMP-003(light).

    Runs against a FRESH opportunity so the relearn task unit slug is always
    available (slugs are unique per app; the per-run app copy resets that).
    """
    tasking = test_data.get("TASKING")
    setup = full_olp_setup(page, config, settings, test_data)
    connect_page = setup.connect_page

    connect_home = ConnectHomePage(connect_page)
    opp_list = ConnectOpportunitiesPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)
    task_list = ConnectAssignedTasksPage(connect_page)

    # Land on the new opportunity's dashboard
    connect_home.click_organizations_in_sidebar()
    opp_list.click_opportunity_in_opportunity(setup.opportunity_name)
    connect_page.wait_for_url("**/opportunity/**")

    # TC-IMP-003 (part A): no task types yet -> tile absent
    if tasking.get("switch_enabled"):
        assert not task_types.is_tasks_tile_visible(), "Tasks tile visible before any task type exists"

    org_slug, opp_id = task_types.opportunity_ids_from_current_url()

    # TC-TTC-001: reach config page via the kebab menu
    task_types.open_from_dashboard_menu()
    task_types.verify_page_loaded(expected_app_name=setup.delivery_app_name)
    task_types.verify_no_task_types_yet()

    # TC-TTC-002 + TC-TTC-003: create from the registered task unit, slug intact
    created_name = task_types.add_task_type(tasking["task_unit_name"], tasking["case_property"])
    assert created_name == tasking["task_unit_name"]
    task_types.verify_row_present(created_name)
    task_types.verify_row_shows_slug(created_name, tasking["task_unit_slug"])

    # TC-TTC-004: used unit no longer offered
    labels = task_types.available_task_unit_labels()
    assert tasking["task_unit_name"] not in labels, f"Used task unit still offered: {labels}"

    # TC-TTC-005: edit name/description
    edited_name = tasking["edited_type_name"]
    task_types.edit_task_type_name(created_name, edited_name, "Edited by automation")
    task_types.verify_row_present(edited_name)

    # Positive half of TC-TAS-005: active type IS offered in Create Task modal
    task_list.goto_task_list(config.get("connect_url"), org_slug, opp_id)
    task_list.verify_page_loaded()
    assert edited_name in task_list.create_modal_task_type_labels()

    # TC-IMP-003 (part B): active type exists -> tile present
    if tasking.get("switch_enabled"):
        connect_page.goto(f"{config.get('connect_url')}/a/{org_slug}/opportunity/{opp_id}/")
        connect_page.wait_for_load_state("load")
        connect_page.wait_for_timeout(3000)  # stats tile arrives via htmx
        assert task_types.is_tasks_tile_visible(), "Tasks tile missing with an active task type"

    # TC-TTC-006: archive
    task_types.goto_task_types(config.get("connect_url"), org_slug, opp_id)
    task_types.archive_task_type(edited_name)
    task_types.verify_row_archived(edited_name)

    # TC-TAS-005: archived type no longer offered in Create Task modal
    task_list.goto_task_list(config.get("connect_url"), org_slug, opp_id)
    assert edited_name not in task_list.create_modal_task_type_labels(), "Archived type still assignable"
```

(`goto_task_list`, `verify_page_loaded`, `create_modal_task_type_labels` are defined in Task 6's page object — Tasks 5 and 6 must be implemented together before this test runs; run order below reflects that.)

- [ ] **Step 5.2: Commit** (after Task 6 exists and the run in Task 7 passes — see Task 7 step 7.2)

---

## Task 6: ConnectAssignedTasksPage + ConnectWorkersPage

**Files:**
- Create: `playwright_web/pages/connect_assigned_tasks_page.py`
- Create: `playwright_web/pages/connect_workers_page.py`

- [ ] **Step 6.1: Create `playwright_web/pages/connect_assigned_tasks_page.py`:**

```python
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
    FILTER_FORM = locators.get("connect_assigned_tasks_page", "filter_form")
    FILTER_STATUS_SELECT = locators.get("connect_assigned_tasks_page", "filter_status_select")
    FILTER_TASK_TYPE_SELECT = locators.get("connect_assigned_tasks_page", "filter_task_type_select")
    FILTER_APPLY_BTN = locators.get("connect_assigned_tasks_page", "filter_apply_btn")
    FILTER_CLOSE_BTN = locators.get("connect_assigned_tasks_page", "filter_close_btn")

    # -- navigation / structure ---------------------------------------------

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

    def verify_columns(self, expect_checkbox=True, expect_edit=True):
        headers = [h.strip() for h in self.page.locator(self.COLUMN_HEADERS).all_inner_texts()]
        self._step(f"Table columns: {headers}")
        for col in EXPECTED_COLUMNS:
            assert col in headers, f"Missing column '{col}' in {headers}"
        assert "Task ID" not in headers, "Task ID column should have been removed (PR #1375)"
        return headers

    # -- create -----------------------------------------------------------

    def open_create_modal(self):
        self._step("Open Create Task modal")
        self.click(self.CREATE_TASK_BTN)
        # modal is a <template x-if> - form only exists after the click
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

    def create_task(self, task_type, worker, due_in_days=7):
        self.open_create_modal()
        self.select_tomselect_by_label("id_task", task_type, scope=self.CREATE_TASK_FORM)
        self.select_tomselect_by_label("id_access", worker, scope=self.CREATE_TASK_FORM)
        due = (date.today() + timedelta(days=due_in_days)).isoformat()
        self._step(f"Set due date {due}")
        self.page.locator(self.CREATE_TASK_FORM).locator("#id_due_date").fill(due)
        self._step(f"Save task '{task_type}' for '{worker}'")
        self.click(self.CREATE_TASK_SAVE_BTN)
        self.page.wait_for_load_state("load")
        return due

    def attempt_duplicate_task(self, task_type, worker, due_in_days=7):
        """Submit a duplicate assignment; returns the validation error text."""
        self.open_create_modal()
        self.select_tomselect_by_label("id_task", task_type, scope=self.CREATE_TASK_FORM)
        self.select_tomselect_by_label("id_access", worker, scope=self.CREATE_TASK_FORM)
        due = (date.today() + timedelta(days=due_in_days)).isoformat()
        self.page.locator(self.CREATE_TASK_FORM).locator("#id_due_date").fill(due)
        self.click(self.CREATE_TASK_SAVE_BTN)
        error = self.page.locator(self.FORM_ERROR_TEXT).first
        error.wait_for(state="visible", timeout=15000)
        text = error.inner_text().strip()
        self._step(f"Duplicate assignment rejected with: {text}")
        self.cancel_create_modal()
        return text

    # -- row assertions ------------------------------------------------------

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
            from datetime import date as _date
            due = _date.fromisoformat(due_date_iso)
            candidates = {due.strftime("%b %d, %Y"), due.strftime("%d %b %Y"),
                          due.strftime("%m/%d/%Y"), due.strftime("%Y-%m-%d"),
                          due.strftime("%b. %d, %Y")}
            assert any(fmt in text for fmt in candidates), (
                f"Row does not show due date {due_date_iso} in any known format: {text!r}"
            )
        self._step(f"Task row verified for '{worker}': {status}, {task_type}")

    def row_exists(self, worker):
        return self.page.locator(self.ROW_BY_WORKER.format(worker=worker)).count() > 0

    # -- edit --------------------------------------------------------------

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

    # -- delete -------------------------------------------------------------

    def delete_tasks_for_workers(self, workers):
        for worker in workers:
            self._step(f"Select task row for '{worker}'")
            self.page.locator(self.ROW_CHECKBOX_BY_WORKER.format(worker=worker)).first.check()
        self._step("Click Delete Task(s)")
        self.click(self.DELETE_TASKS_BTN)
        self.page.locator(self.CONFIRM_MODAL_TITLE).first.wait_for(state="visible")
        self._step("Confirm deletion")
        self.click(self.CONFIRM_DELETE_BTN)
        self.page.wait_for_load_state("load")

    # -- filters -------------------------------------------------------------

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
        badges = self.page.locator(
            "//div[@id='task-list-table']//span[contains(@class,'bg-amber-100') or contains(@class,'bg-green-100')]"
        ).all_inner_texts()
        self._step(f"Visible status badges: {badges}")
        return [b.strip() for b in badges]

    # -- permissions -----------------------------------------------------------

    def manage_controls_visible(self):
        create_visible = self.page.locator(self.CREATE_TASK_BTN).count() > 0
        delete_visible = self.page.locator(self.DELETE_TASKS_BTN).count() > 0
        checkbox_visible = self.page.locator("//div[@id='task-list-table']//input[@name='row_select']").count() > 0
        self._step(f"Manage controls - create: {create_visible}, delete: {delete_visible}, checkboxes: {checkbox_visible}")
        return create_visible, delete_visible, checkbox_visible

    def edit_buttons_visible(self):
        visible = self.page.locator("//div[@id='task-list-table']//button[.//i[contains(@class,'fa-pen-to-square')]]").count() > 0
        self._step(f"Edit buttons visible: {visible}")
        return visible
```

- [ ] **Step 6.2: Create `playwright_web/pages/connect_workers_page.py`:**

```python
from utils.helpers import LocatorLoader

from pages.base_page import BasePage

locators = LocatorLoader()


class ConnectWorkersPage(BasePage):
    TASKS_TAB = locators.get("connect_workers_page", "tasks_tab")
    TAB_CONTENT = locators.get("connect_workers_page", "tab_content")
    DRILLDOWN_TASKS_TAB = locators.get("connect_workers_page", "drilldown_tasks_tab")
    TASK_DETAILS_PANEL = locators.get("connect_workers_page", "task_details_panel")

    def goto_workers_tasks_tab(self, base_url, org_slug, opp_id):
        """The Workers page Tasks tab (grouped per-worker accordion table)."""
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
        row = self.page.locator("//table//tr[contains(@class,'group') or @hx-get][td]").first
        row.wait_for(state="visible", timeout=20000)
        row.click()
        panel = self.page.locator(self.TASK_DETAILS_PANEL).first
        self.page.wait_for_timeout(2000)  # htmx load
        text = panel.inner_text()
        assert "select a task" not in text.lower(), "Details panel did not load after row click"
        self._step("Task details panel loaded")
        return text
```

- [ ] **Step 6.3: Commit**

```bash
git add playwright_web/pages/connect_assigned_tasks_page.py playwright_web/pages/connect_workers_page.py playwright_web/tests/test_task_type_config.py
git commit -m "Add assigned tasks and workers page objects plus J1 config journey test"
```

---

## Task 7: Run + stabilize J1

- [ ] **Step 7.1: Run J1 against staging**

Run: `cd C:\dqccc-tasking\playwright_web; python -m pytest tests/test_task_type_config.py -v`
Expected: PASS in ~4 min. First run will likely surface selector drift (kebab icon, table cell layout, message formats). Fix locators in `web_locators.yaml` — not by adding sleeps. Two known risk points and their fallbacks:
  - Kebab toggle: if the `fa-bars` xpath misses, inspect the failure screenshot in the html report; the menu link itself (`Configure Task Types`) is stable — worst case navigate by URL via `goto_task_types` and keep menu-entry verification as `assert link count > 0` after clicking the toggle found via `page.get_by_role`.
  - Due-date/archived date cell formats: adjust the format candidates in `verify_task_row` / digit heuristic in `verify_row_archived` to what the page actually renders (note it in the commit message).

- [ ] **Step 7.2: Re-run until green, then commit fixes**

```bash
git add -A playwright_web/
git commit -m "Stabilize J1 task type config journey against staging"
```

---

## Task 8: J2/J3/J4 tests (self-skipping until static opp configured)

**Files:**
- Create: `playwright_web/tests/test_task_assignment_lifecycle.py`
- Create: `playwright_web/tests/test_task_views_filters.py`
- Create: `playwright_web/tests/test_task_permissions.py`

All three share a skip guard and a login helper — put both in a small module to keep DRY.

- [ ] **Step 8.1: Create the shared guard in `playwright_web/flows/tasking_static.py`:**

```python
"""Shared entry for journey tests that need the designated static tasking
opportunity (enrolled workers). They skip until TASKING.static_opp is filled in."""

import pytest

from flows.olp_setup import open_connect_as_org
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage


def require_static_opp(test_data):
    tasking = test_data.get("TASKING")
    required = ["static_opp", "static_org", "static_worker", "static_task_type"]
    missing = [key for key in required if not tasking.get(key)]
    if missing:
        pytest.skip(
            "Static tasking opportunity not configured in test_data (missing: "
            + ", ".join(missing)
            + ") - see Tasking_Workflow_Automation_Test_Plan.xlsx Prerequisites"
        )
    return tasking


def login_to_connect(page, config, settings, organization):
    """CCHQ login + Connect OAuth + org selection (no app copies)."""
    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()
    return open_connect_as_org(page, config, organization=organization)
```

- [ ] **Step 8.2: Create `playwright_web/tests/test_task_assignment_lifecycle.py`** (J2 — TC-TAS-001/002/004+/006/007, TC-TLV-001, TC-TDL-001/002):

```python
from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage


def test_task_assignment_lifecycle_journey(page, test_data, config, settings):
    """J2 - assign -> verify -> duplicate blocked -> edit due date -> delete."""
    tasking = require_static_opp(test_data)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()

    # TC-TLV-001: structure + no Task ID column
    tasks.verify_columns()
    total_before = tasks.metric("Total Tasks")
    open_before = tasks.metric("Open Tasks")

    # TC-TAS-004 (positive): the enrolled worker is offered; TC-TAS-001: assign
    due = tasks.create_task(task_type, worker, due_in_days=7)
    tasks.verify_success_message("Task created successfully")
    tasks.verify_task_row(worker, task_type, due_date_iso=due, status="To Do")

    # TC-TAS-007: metrics moved
    assert tasks.metric("Total Tasks") == total_before + 1
    assert tasks.metric("Open Tasks") == open_before + 1

    # TC-TAS-002: duplicate blocked
    error = tasks.attempt_duplicate_task(task_type, worker)
    assert "already assigned" in error.lower()

    # TC-TAS-006: edit due date
    tasks.edit_due_date(worker, due_in_days=14, reason="Automation reschedule")
    tasks.verify_success_message("Task updated successfully")

    # TC-TDL-001 (or TC-TDL-002 when a second type is configured)
    second_type = tasking.get("static_task_type_2")
    if second_type:
        tasks.create_task(second_type, worker, due_in_days=7)
        tasks.verify_success_message("Task created successfully")
        tasks.delete_tasks_for_workers([worker, worker])
    else:
        tasks.delete_tasks_for_workers([worker])
    assert tasks.metric("Total Tasks") == total_before, "Totals did not return to baseline after delete"
    assert not tasks.row_exists(worker) or tasks.metric("Open Tasks") == open_before
```

Note on `static_opp_id`: J2 navigates by id, so add `static_opp_id: ""` to the TASKING block in Task 3 (numeric id from the opportunity URL) and include it in `require_static_opp`'s required list. Delete-with-two-rows-same-worker: `delete_tasks_for_workers([worker, worker])` would double-check the same first checkbox — implement by checking ALL checkboxes in rows matching the worker instead (`.all()` loop) when the list has duplicates; handle inside `delete_tasks_for_workers`:

```python
    def delete_tasks_for_workers(self, workers):
        for worker in set(workers):
            boxes = self.page.locator(self.ROW_CHECKBOX_BY_WORKER.format(worker=worker)).all()
            for box in boxes:
                if box.is_enabled():
                    box.check()
        self._step("Click Delete Task(s)")
        self.click(self.DELETE_TASKS_BTN)
        self.page.locator(self.CONFIRM_MODAL_TITLE).first.wait_for(state="visible")
        self.click(self.CONFIRM_DELETE_BTN)
        self.page.wait_for_load_state("load")
```

(Use this version in Task 6 directly.)

- [ ] **Step 8.3: Create `playwright_web/tests/test_task_views_filters.py`** (J3 — TC-TLV-002/003/004/005(basic)/006):

```python
from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_task_types_page import ConnectTaskTypesPage
from pages.connect_workers_page import ConnectWorkersPage


def test_task_views_and_filters_journey(page, test_data, config, settings):
    """J3 - creates its own task, checks every view that renders it, deletes it."""
    tasking = require_static_opp(test_data)
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)
    workers = ConnectWorkersPage(connect_page)
    task_types = ConnectTaskTypesPage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    tasks.goto_task_list(base_url, org, opp)
    tasks.verify_page_loaded()
    tasks.create_task(task_type, worker, due_in_days=7)
    tasks.verify_success_message("Task created successfully")

    try:
        # TC-TLV-002: two representative filters
        tasks.apply_status_filter("To Do")
        badges = tasks.visible_status_badges()
        assert badges and all(b == "To Do" for b in badges), f"Non-To-Do rows after filter: {badges}"
        tasks.clear_filters()

        # TC-TLV-003: workers page Tasks tab shows the grouped row
        workers.goto_workers_tasks_tab(base_url, org, opp)
        workers.verify_worker_has_task(worker, task_type)

        # TC-TLV-004/005 (basic): drill-down tasks list + details panel loads
        # (Name/Description assertions deferred pending TC-IMP-002 bug verification)
        workers.goto_worker_tasks_page(base_url, org, opp)
        details_text = workers.open_first_task_details()
        assert "Due" in details_text or "Status" in details_text

        # TC-TLV-006: dashboard tile (only when switch confirmed on)
        if tasking.get("switch_enabled"):
            connect_page.goto(f"{base_url}/a/{org}/opportunity/{opp}/")
            connect_page.wait_for_load_state("load")
            connect_page.wait_for_timeout(3000)
            assert task_types.is_tasks_tile_visible()
    finally:
        # cleanup so reruns start clean even on mid-test failure
        tasks.goto_task_list(base_url, org, opp)
        if tasks.row_exists(worker):
            tasks.delete_tasks_for_workers([worker])
```

- [ ] **Step 8.4: Create `playwright_web/tests/test_task_permissions.py`** (J4 — TC-PRM-001/002/003):

```python
import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect, require_static_opp
from pages.connect_assigned_tasks_page import ConnectAssignedTasksPage
from pages.connect_home_page import ConnectHomePage


def test_task_permissions_journey(page, test_data, config, settings):
    """J4 - PM org admin sees manage controls; NM org member gets edit-only; config 404s."""
    tasking = require_static_opp(test_data)
    if not tasking.get("static_nm_org") or not tasking.get("static_nm_org_name"):
        pytest.skip("TASKING.static_nm_org / static_nm_org_name not configured")
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    tasks = ConnectAssignedTasksPage(connect_page)
    connect_home = ConnectHomePage(connect_page)

    base_url = config.get("connect_url")
    org, opp = tasking["static_org"], tasking["static_opp_id"]
    worker = tasking["static_worker"]
    task_type = tasking["static_task_type"]

    # PM org: full manage controls (TC-PRM-001) - needs one pending task for Edit column
    tasks.goto_task_list(base_url, org, opp)
    tasks.create_task(task_type, worker, due_in_days=7)
    tasks.verify_success_message("Task created successfully")
    create_visible, delete_visible, checkboxes_visible = tasks.manage_controls_visible()
    assert create_visible and delete_visible and checkboxes_visible
    assert tasks.edit_buttons_visible()

    try:
        # NM org: view + edit-only (TC-PRM-002)
        connect_home.select_organization_from_list(tasking["static_nm_org_name"])
        tasks.goto_task_list(base_url, tasking["static_nm_org"], opp)
        tasks.verify_page_loaded()
        create_visible, delete_visible, checkboxes_visible = tasks.manage_controls_visible()
        assert not create_visible and not delete_visible and not checkboxes_visible
        assert tasks.edit_buttons_visible(), "NM member should still get due-date Edit (PR #1381)"

        # TC-PRM-003: task type config 404s for NM org
        connect_page.goto(f"{base_url}/a/{tasking['static_nm_org']}/opportunity/{opp}/task_types/")
        connect_page.wait_for_load_state("load")
        body = connect_page.inner_text("body")
        assert "not available" in body.lower() or "404" in body, f"Expected 404 page, got: {body[:200]}"
    finally:
        # cleanup: back to PM org, delete the task
        connect_home.select_organization_from_list(PM_ORG)
        tasks.goto_task_list(base_url, org, opp)
        if tasks.row_exists(worker):
            tasks.delete_tasks_for_workers([worker])
```

- [ ] **Step 8.5: Run all three — expect SKIP (static opp not yet designated)**

Run: `python -m pytest tests/test_task_assignment_lifecycle.py tests/test_task_views_filters.py tests/test_task_permissions.py -v`
Expected: 3 SKIPPED with the "Static tasking opportunity not configured" message.

- [ ] **Step 8.6: Commit**

```bash
git add playwright_web/flows/tasking_static.py playwright_web/tests/test_task_assignment_lifecycle.py playwright_web/tests/test_task_views_filters.py playwright_web/tests/test_task_permissions.py
git commit -m "Add J2-J4 tasking journey tests, self-skipping until static opp is designated"
```

---

## Task 9: Full-suite regression + push

- [ ] **Step 9.1: Run the whole Playwright suite**

Run: `cd C:\dqccc-tasking\playwright_web; python -m pytest -v`
Expected: existing unit tests PASS, `test_olp_01_02_03` PASS, `test_olp_04` PASS, J1 PASS, J2–J4 SKIP. No failures.

- [ ] **Step 9.2: Push the branch** (no PR yet — that's the user's call)

```bash
git push -u origin feature/tasking-web-automation
```

---

## Self-review notes

- Spec coverage: J1 covers TTC-001..006 + TAS-005 + IMP-003-light; J2 covers TAS-001/002/004(positive)/006/007 + TLV-001 + TDL-001/002; J3 covers TLV-002(2 filters)/003/004/005(basic)/006; J4 covers PRM-001..003; IMP-004 is Task 2's regression gate + Task 9. Deferred/manual cases per the workbook's Automation Target column are intentionally absent.
- `static_opp_id` added to TASKING data block (Task 3) — required by J2–J4 URL building; `require_static_opp` checks it.
- `delete_tasks_for_workers` — use the `.all()`/`set()` version from Task 8.2 in the Task 6 page object (single definition).
- Live-run risk is concentrated in Task 7 (selector drift) — locator fixes belong in YAML, never sleeps in tests.
