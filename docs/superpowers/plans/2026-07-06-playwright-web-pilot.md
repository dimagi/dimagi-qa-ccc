# Playwright Web Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a new Python + pytest-playwright project (`playwright_web/`) inside `dimagi-qa-ccc`, from scratch, and port 2 web tests (`test_olp_01_02_03`, `test_olp_04`) from the existing Selenium suite, proving the pattern before the remaining 8 web tests are ported later.

**Architecture:** Page Object Model, same shape as the existing Selenium suite (`locators/web_locators.yaml` → `LocatorLoader` → page classes → tests), but reimplemented idiomatically for Playwright: locators are plain selector strings (not `(By, value)` tuples), and most manual `WebDriverWait`/retry code is dropped because Playwright auto-waits for actionability. `config/env.yaml`, `settings.cfg`, and `test_data/web_test_data.yaml` are reused from the repo root by relative path — not duplicated. `conftest.py` lives at `playwright_web/conftest.py` (not inside `tests/`), mirroring the existing repo's own `conftest.py`-at-root pattern, which is what makes `from pages.xxx import X` and `from utils.helpers import Y` resolve without extra `pythonpath` configuration (pytest inserts the directory containing the topmost `conftest.py` onto `sys.path`).

**Tech Stack:** Python, pytest, pytest-playwright, Playwright (Chromium), PyYAML.

**Reference source (read-only, for porting logic):**
- `tests/web_tests/test_olp_01_02_03.py`, `tests/web_tests/test_olp_04.py`
- `pages/web_pages/base_web_page.py`, `cchq_login_web_page.py`, `cchq_home_web_page.py`, `cchq_application_web_page.py`, `connect_home_web_page.py`, `connect_opportunities_web_page.py`, `connect_opportunity_dashboard_web_page.py`
- `utils/helpers.py`, `locators/web_locators.yaml`, `config/env.yaml`, `settings-sample.cfg`, `test_data/web_test_data.yaml`

**Note on test design for this plan:** Tasks 2–4 (locators, config/test-data loaders, base-page pure logic) are pure Python with no browser dependency, so they get real TDD (failing test → implement → passing test). Tasks 5–10 (page objects) wrap live browser interactions against a real web app — there's no meaningful way to unit-test a selector against a mocked DOM, so (matching how the original Selenium suite itself was validated) these are checked with a fast import/syntax sanity check per task, and substantively verified end-to-end when the full test runs in Tasks 12–13 against the real `stage` environment.

---

### Task 1: Scaffold the project

**Files:**
- Create: `playwright_web/requirements.txt`
- Create: `playwright_web/pytest.ini`
- Create: `playwright_web/README.md`
- Create: `playwright_web/pages/` (empty dir)
- Create: `playwright_web/locators/` (empty dir)
- Create: `playwright_web/utils/` (empty dir)
- Create: `playwright_web/tests/` (empty dir)

- [ ] **Step 1: Create the directory structure**

```bash
mkdir -p playwright_web/pages playwright_web/locators playwright_web/utils playwright_web/tests
```

- [ ] **Step 2: Create `playwright_web/requirements.txt`**

```
playwright
pytest-playwright
PyYAML>=6.0
openai>=1.0.0
```

- [ ] **Step 3: Create `playwright_web/pytest.ini`**

```ini
[pytest]
addopts = -v -s --headed
testpaths = tests
```

- [ ] **Step 4: Create `playwright_web/README.md`**

```markdown
# Playwright Web Pilot

Python + pytest-playwright port of 2 tests from the Selenium web suite
(`test_olp_01_02_03`, `test_olp_04`), proving the framework pattern before
the rest of `tests/web_tests/` is ported.

## Setup

From the `playwright_web/` directory:

    pip install -r requirements.txt
    playwright install chromium

Copy `../settings-sample.cfg` to `../settings.cfg` (repo root) and fill in
`hq_username`/`hq_password` under `[creds]` if you haven't already for the
Selenium suite — both suites share the same file.

## Run

    pytest --env=stage
    pytest --env=prod

Runs Chromium headed by default (see `pytest.ini`).
```

- [ ] **Step 5: Install dependencies and the Chromium browser binary**

Run:
```bash
cd playwright_web
pip install -r requirements.txt
playwright install chromium
```

- [ ] **Step 6: Verify pytest picks up the config with no tests yet**

Run: `pytest --collect-only -q` (from inside `playwright_web/`)
Expected: `no tests ran` (or `no tests collected`) with no import/config errors. Exit code 5 ("no tests collected") is expected and fine at this stage.

- [ ] **Step 7: Commit**

```bash
git add playwright_web/requirements.txt playwright_web/pytest.ini playwright_web/README.md
git commit -m "Scaffold playwright_web project structure"
```

---

### Task 2: Locators file + `LocatorLoader`

**Files:**
- Create: `playwright_web/locators/web_locators.yaml`
- Create: `playwright_web/utils/__init__.py` (empty)
- Create: `playwright_web/utils/helpers.py`
- Test: `playwright_web/tests/test_helpers.py`

- [ ] **Step 1: Copy the existing locators file verbatim**

Copy `locators/web_locators.yaml` (repo root) to `playwright_web/locators/web_locators.yaml`, unchanged. The YAML *values* don't need to change — only how they're consumed changes (Task 2 Step 3 adds the translation logic). This keeps the new file diffable against the original and ready for when the remaining 8 tests are ported later.

```bash
cp locators/web_locators.yaml playwright_web/locators/web_locators.yaml
```

- [ ] **Step 2: Create `playwright_web/utils/__init__.py`**

Empty file.

- [ ] **Step 3: Write the failing test for `LocatorLoader`**

Create `playwright_web/tests/test_helpers.py`:

```python
from utils.helpers import LocatorLoader


def test_locator_loader_converts_xpath():
    loader = LocatorLoader()
    result = loader.get("cchq_home_page", "welcome_title")
    assert result == "xpath=//h1[@class='mb-3 mt-5']"


def test_locator_loader_converts_id():
    loader = LocatorLoader()
    result = loader.get("cchq_login_page", "cookie_accept_button")
    assert result == "#hs-eu-confirmation-button"


def test_locator_loader_preserves_format_placeholders():
    loader = LocatorLoader()
    result = loader.get("cchq_home_page", "app_link")
    assert result == "xpath=(//li/a[contains(., '{name}')])[1]"
    assert result.format(name="Learn App") == "xpath=(//li/a[contains(., 'Learn App')])[1]"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_helpers.py -v` (from `playwright_web/`)
Expected: FAIL with `ModuleNotFoundError: No module named 'utils'` (or `ImportError`) since `utils/helpers.py` doesn't exist yet.

- [ ] **Step 4: Write `playwright_web/utils/helpers.py`** (LocatorLoader only for now — Task 3 adds the rest to this same file)

```python
from pathlib import Path

import yaml

PLAYWRIGHT_ROOT = Path(__file__).resolve().parents[1]


class LocatorLoader:
    def __init__(self, file_path="locators/web_locators.yaml"):
        with open(PLAYWRIGHT_ROOT / file_path, "r") as f:
            self.data = yaml.safe_load(f)

    def get(self, page, element):
        locator_value = self.data[page][element]
        if locator_value.startswith("//") or locator_value.startswith("("):
            return f"xpath={locator_value}"
        return f"#{locator_value}"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_helpers.py -v`
Expected: 3 passed

- [ ] **Step 6: Commit**

```bash
git add playwright_web/locators/web_locators.yaml playwright_web/utils/__init__.py playwright_web/utils/helpers.py playwright_web/tests/test_helpers.py
git commit -m "Add LocatorLoader and copy web_locators.yaml for Playwright pilot"
```

---

### Task 3: `ConfigLoader`, `SettingsLoader`, `TestDataLoader`

**Files:**
- Modify: `playwright_web/utils/helpers.py`
- Test: `playwright_web/tests/test_helpers.py`

- [ ] **Step 1: Write the failing tests**

Append to `playwright_web/tests/test_helpers.py`:

```python
from utils.helpers import ConfigLoader, SettingsLoader, TestDataLoader


def test_config_loader_defaults_to_prod():
    config = ConfigLoader(env=None)
    assert config.env == "prod"
    assert config.get("cchq_url") == "https://www.commcarehq.org/a/connectqa-automation-prod/login/"


def test_config_loader_stage_env():
    config = ConfigLoader(env="stage")
    assert config.get("connect_url") == "https://connect-staging.dimagi.com"


def test_settings_loader_env_var_takes_precedence(monkeypatch):
    monkeypatch.setenv("TEST_ENV_VAR", "from-env")
    settings = SettingsLoader()
    assert settings.get(section="creds", key="hq_username", env_var="TEST_ENV_VAR") == "from-env"


def test_settings_loader_returns_default_when_missing():
    settings = SettingsLoader()
    assert settings.get(section="nope", key="nope", default="fallback") == "fallback"


def test_test_data_loader_loads_olp_1():
    data = TestDataLoader()
    olp1 = data.get("OLP_1")
    assert olp1["opportunity_name"] == "Demo Opportunity"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_helpers.py -v`
Expected: FAIL with `ImportError: cannot import name 'ConfigLoader'` (and similarly for `SettingsLoader`, `TestDataLoader`)

- [ ] **Step 3: Add the loaders to `playwright_web/utils/helpers.py`**

Add to the top of the file and append these classes:

```python
import configparser
import os

REPO_ROOT = Path(__file__).resolve().parents[2]


class ConfigLoader:
    def __init__(self, env):
        with open(REPO_ROOT / "config" / "env.yaml", "r") as f:
            data = yaml.safe_load(f)
        self.env = env or data["default"]
        self.config = data[self.env]

    def get(self, key):
        return self.config.get(key)


class SettingsLoader:
    def __init__(self):
        self.config = configparser.ConfigParser()
        cfg_path = REPO_ROOT / "settings.cfg"
        if cfg_path.exists():
            try:
                self.config.read(cfg_path)
            except configparser.Error:
                pass

    def get(self, section, key, env_var=None, required=False, default=None):
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value
        if self.config.has_option(section, key):
            return self.config.get(section, key)
        if default is not None:
            return default
        if required:
            raise RuntimeError(f"Missing setting: env_var={env_var} or [{section}].{key}")
        return None


class TestDataLoader:
    def __init__(self, file_path="test_data/web_test_data.yaml"):
        with open(REPO_ROOT / file_path, "r") as f:
            self.data = yaml.safe_load(f) or {}

    def get(self, tc_id):
        if tc_id not in self.data:
            raise KeyError(f"No test data found for {tc_id}")
        return self.data[tc_id]
```

Note: `REPO_ROOT` (`dimagi-qa-ccc/`) is used for the files being *reused* (`config/env.yaml`, `settings.cfg`, `test_data/web_test_data.yaml`); `PLAYWRIGHT_ROOT` (from Task 2) is used only for `locators/web_locators.yaml`, which is a new, Playwright-specific copy.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_helpers.py -v`
Expected: 8 passed

- [ ] **Step 5: Commit**

```bash
git add playwright_web/utils/helpers.py playwright_web/tests/test_helpers.py
git commit -m "Add ConfigLoader, SettingsLoader, TestDataLoader to playwright_web"
```

---

### Task 4: `BasePage`

**Files:**
- Create: `playwright_web/pages/__init__.py` (empty)
- Create: `playwright_web/pages/base_page.py`
- Test: `playwright_web/tests/test_base_page.py`

- [ ] **Step 1: Create `playwright_web/pages/__init__.py`**

Empty file.

- [ ] **Step 2: Write the failing test for the one pure-logic method (`generate_date_range`)**

Create `playwright_web/tests/test_base_page.py`:

```python
from datetime import datetime, timedelta

from pages.base_page import BasePage


def test_generate_date_range_returns_dd_mm_yyyy_format():
    base = BasePage(page=None)
    start, end = base.generate_date_range(7)

    today = datetime.today()
    expected_start = (today + timedelta(days=2)).strftime("%d-%m-%Y")
    expected_end = (today + timedelta(days=2) + timedelta(days=7)).strftime("%d-%m-%Y")

    assert start == expected_start
    assert end == expected_end
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/test_base_page.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'pages'`

- [ ] **Step 4: Write `playwright_web/pages/base_page.py`**

```python
import os
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

_AI_HEALING_ENABLED = os.getenv("AI_HEALING_ENABLED", "false").lower() == "true"


class BasePage:
    def __init__(self, page):
        self.page = page

    def click(self, selector, force=False):
        try:
            self.page.locator(selector).click(force=force)
        except PlaywrightTimeoutError:
            if _AI_HEALING_ENABLED:
                healed = self._ai_heal(selector)
                self.page.locator(healed).click(force=force)
            else:
                raise

    def type(self, selector, text):
        try:
            self.page.locator(selector).fill(text)
        except PlaywrightTimeoutError:
            if _AI_HEALING_ENABLED:
                healed = self._ai_heal(selector)
                self.page.locator(healed).fill(text)
            else:
                raise

    def get_text(self, selector):
        return self.page.locator(selector).inner_text()

    def is_displayed(self, selector, timeout=5000):
        try:
            self.page.locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def select_by_visible_text(self, selector, text):
        self.page.locator(selector).select_option(label=text)

    def scroll_into_view(self, selector):
        self.page.locator(selector).scroll_into_view_if_needed()

    def click_link_by_text(self, link_text):
        self.page.get_by_role("link", name=link_text, exact=False).first.click()

    def enter_date(self, selector, date_value):
        # Input is DD-MM-YYYY; HTML date inputs need YYYY-MM-DD.
        parts = date_value.split("-")
        if len(parts) == 3 and len(parts[2]) == 4:
            formatted = f"{parts[2]}-{parts[1]}-{parts[0]}"
        else:
            formatted = date_value

        self.page.locator(selector).evaluate(
            "(el, value) => { el.value = value; el.dispatchEvent(new Event('change')); }",
            formatted,
        )
        actual_value = self.page.locator(selector).input_value()
        assert actual_value == formatted, (
            f"Failed to set date. Expected '{formatted}', but got '{actual_value}'"
        )

    def generate_date_range(self, days_to_add):
        today = datetime.today()
        start = today + timedelta(days=2)
        end = start + timedelta(days=days_to_add)
        return start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")

    def _ai_heal(self, selector):
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(f"Element not found and AI healing has no API key: {selector}")

        page_src = self.page.content()[:6000]
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "In this HTML page source, find an element that matches "
                    f"the intent of CSS/XPath selector {selector}. "
                    "Reply with ONLY a valid XPath string (starting with //) or CSS selector, nothing else.\n\n"
                    f"{page_src}"
                ),
            }],
        )
        healed = response.choices[0].message.content.strip()
        if not healed:
            raise RuntimeError(f"AI healing returned unusable result for: {selector}")
        if healed.startswith("//") or healed.startswith("("):
            healed = f"xpath={healed}"
        print(f"[AI HEAL] Original: {selector} -> Healed: {healed}")
        return healed
```

Note on `generate_date_range`: the original `BaseWebPage.generate_date_range` had two output formats (`opt=1` MM-DD-YYYY, `opt=2` DD-MM-YYYY). Only the DD-MM-YYYY path is actually used by the real call sites in `connect_opportunities_web_page.py` (the MM-DD-YYYY attempts are dead/commented-out code that would in fact mis-parse in `enter_date`, which always assumes DD-MM-YYYY input). This port keeps only the working DD-MM-YYYY behavior.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_base_page.py -v`
Expected: 1 passed

- [ ] **Step 6: Commit**

```bash
git add playwright_web/pages/__init__.py playwright_web/pages/base_page.py playwright_web/tests/test_base_page.py
git commit -m "Add BasePage for playwright_web"
```

---

### Task 5: `LoginPage` (CCHQ login + Connect navigation)

**Files:**
- Create: `playwright_web/pages/cchq_login_page.py`

- [ ] **Step 1: Write `playwright_web/pages/cchq_login_page.py`**

```python
from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class LoginPage(BasePage):
    USERNAME_ELE = locators.get("cchq_login_page", "username_field")
    PASSWORD_ELE = locators.get("cchq_login_page", "password_field")
    COOKIE_ACCEPT_BUTTON = locators.get("cchq_login_page", "cookie_accept_button")
    IFRAME_GUIDE_POPUP = locators.get("cchq_login_page", "iframe_guide_popup")
    GUIDE_POPUP = locators.get("cchq_login_page", "guide_popup")
    SKIP_ONBOARDING = locators.get("cchq_home_page", "skip_onboarding")

    def enter_username_and_password(self, username, password):
        try:
            self.click(self.COOKIE_ACCEPT_BUTTON)
        except Exception:
            print("No Cookies alert present")
        self.type(self.USERNAME_ELE, username)
        self.page.locator(self.PASSWORD_ELE).fill(password)
        self.page.locator(self.PASSWORD_ELE).press("Enter")
        self.page.wait_for_timeout(3000)

    def valid_login_cchq(self, config, settings):
        try:
            cchq_url = config.get("cchq_url")
            self.page.goto(cchq_url)
            self.page.wait_for_load_state("load")
            self.enter_username_and_password(
                settings.get(section="creds", key="hq_username", env_var="hq_username"),
                settings.get(section="creds", key="hq_password", env_var="hq_password"),
            )
            self.page.wait_for_timeout(3000)
        except Exception:
            print("User is already logged in")

    def navigate_to_connect_page(self, config):
        connect_url = config.get("connect_url")
        new_page = self.page.context.new_page()
        new_page.goto(connect_url)
        assert connect_url in new_page.url
        return new_page

    def dismiss_guide_popup(self):
        try:
            frame = self.page.frame_locator(self.IFRAME_GUIDE_POPUP)
            popup = frame.locator(self.GUIDE_POPUP)
            popup.wait_for(state="visible", timeout=8000)
            frame.locator(self.SKIP_ONBOARDING).click()
            print("Skipped onboarding popup")
        except Exception:
            print("No onboarding popup occurred")
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.cchq_login_page import LoginPage; print('ok')"` (from `playwright_web/`)
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/cchq_login_page.py
git commit -m "Add LoginPage to playwright_web"
```

---

### Task 6: `CCHQHomePage`

**Files:**
- Create: `playwright_web/pages/cchq_home_page.py`

- [ ] **Step 1: Write `playwright_web/pages/cchq_home_page.py`**

```python
from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class CCHQHomePage(BasePage):
    TITLE_ELE = locators.get("cchq_home_page", "welcome_title")
    APPLICATIONS_TAB = locators.get("cchq_home_page", "applications_tab")

    def verify_home_page_title(self, title):
        text = self.get_text(self.TITLE_ELE)
        assert title in text

    def select_app_under_applications_tab(self, app):
        self.click(self.APPLICATIONS_TAB)
        self.page.get_by_role("link", name=app, exact=False).first.click()
        self.page.wait_for_load_state("load")
        assert "/apps/view" in self.page.url

    def verify_app_present_under_applications_tab(self, app):
        self.click(self.APPLICATIONS_TAB, force=True)
        link = self.page.get_by_role("link", name=app, exact=False).first
        link.scroll_into_view_if_needed()
        assert link.is_visible(), f"{app} not found under applications tab"
        print(f"{app} present under applications tab")
        self.click(self.APPLICATIONS_TAB, force=True)
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.cchq_home_page import CCHQHomePage; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/cchq_home_page.py
git commit -m "Add CCHQHomePage to playwright_web"
```

---

### Task 7: `CCHQApplicationPage`

**Files:**
- Create: `playwright_web/pages/cchq_application_page.py`

- [ ] **Step 1: Write `playwright_web/pages/cchq_application_page.py`**

```python
from datetime import datetime

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class CCHQApplicationPage(BasePage):
    SIDEBAR_SETTINGS_ICON = locators.get("cchq_application_page", "sidebar_settings_icon")
    SETTINGS_TAB_BY_NAME = locators.get("cchq_application_page", "settings_tab_by_name")
    COPY_APP_TO_PROJECT_DROPDOWN = locators.get("cchq_application_page", "copy_app_to_project_dropdown")
    NAME_INPUT = locators.get("cchq_application_page", "name_input")
    COPY_BUTTON = locators.get("cchq_application_page", "copy_button")
    MAKE_NEW_VERSION_BUTTON = locators.get("cchq_application_page", "make_new_version_button")
    RELEASED_BUTTON = locators.get("cchq_application_page", "released_button")

    def click_sidebar_settings_icon(self):
        self.click(self.SIDEBAR_SETTINGS_ICON)
        self.page.wait_for_load_state("load")
        assert "/settings/" in self.page.url

    def click_tab_by_name_in_application_settings(self, tab_name):
        tab_selector = self.SETTINGS_TAB_BY_NAME.format(tab_name=tab_name)
        self.click(tab_selector)
        tab = self.page.locator(tab_selector)
        assert "active" in (tab.get_attribute("class") or "")

    def select_copy_app_to_project_dropdown(self, value):
        self.select_by_visible_text(self.COPY_APP_TO_PROJECT_DROPDOWN, value)

    def _enter_app_name(self, prefix):
        timestamp = datetime.now().strftime("[%d/%m/%Y : %H:%M]")
        full_name = f"{prefix} {timestamp}"
        self.page.locator(self.NAME_INPUT).fill(full_name)
        self.page.locator(self.NAME_INPUT).press("Tab")
        self.page.wait_for_timeout(5000)
        return full_name

    def click_copy_button(self):
        self.scroll_into_view(self.COPY_BUTTON)
        self.page.locator(self.COPY_BUTTON).click(force=True)
        self.page.wait_for_load_state("load")
        assert "/apps/view" in self.page.url
        self.page.wait_for_timeout(5000)

    def click_make_new_version_button(self):
        self.click(self.MAKE_NEW_VERSION_BUTTON)
        self.click(self.RELEASED_BUTTON)

    def create_copy_of_learn_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        project = "connectqa-automation-prod" if "www" in self.page.url else "connectqa-automation"
        self.select_copy_app_to_project_dropdown(project)
        learn_app_full_name = self._enter_app_name("Learn App")
        self.click_copy_button()
        self.click_make_new_version_button()
        return learn_app_full_name

    def create_copy_of_delivery_app(self):
        self.click_sidebar_settings_icon()
        self.click_tab_by_name_in_application_settings("Actions")
        project = "connectqa-automation-prod" if "www" in self.page.url else "connectqa-automation"
        self.select_copy_app_to_project_dropdown(project)
        delivery_app_full_name = self._enter_app_name("Delivery App")
        self.click_copy_button()
        self.click_make_new_version_button()
        return delivery_app_full_name
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.cchq_application_page import CCHQApplicationPage; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/cchq_application_page.py
git commit -m "Add CCHQApplicationPage to playwright_web"
```

---

### Task 8: `ConnectHomePage`

**Files:**
- Create: `playwright_web/pages/connect_home_page.py`

- [ ] **Step 1: Write `playwright_web/pages/connect_home_page.py`**

```python
from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class ConnectHomePage(BasePage):
    LOGIN_LINK = locators.get("connect_home_page", "login_link")
    LOGIN_WITH_CC_HQ = locators.get("connect_home_page", "login_with_cc_hq")
    AUTHORIZE_BUTTON = locators.get("connect_home_page", "authorize_button")
    OPPORTUNITIES_NAVBAR_LINK = locators.get("connect_home_page", "opportunities_navbar_item")
    ORGANIZATION_CONTAINER = locators.get("connect_home_page", "organization_container")
    ORGANIZATION_DROPDOWN = locators.get("connect_home_page", "organization_dropdown")
    ORGANIZATION_NAME = locators.get("connect_home_page", "organization_name")

    def click_organizations_in_sidebar(self):
        self.click(self.OPPORTUNITIES_NAVBAR_LINK)
        self.page.wait_for_url("**/opportunity/**")

    def signin_to_connect_page_using_cchq(self):
        try:
            self.click(self.LOGIN_LINK)
            self.page.wait_for_timeout(2000)
            self.click(self.LOGIN_WITH_CC_HQ)
            self.click(self.AUTHORIZE_BUTTON)
        except Exception:
            print("User already signed in")
        finally:
            self.click_organizations_in_sidebar()

    def is_org_selected(self, organization_name):
        self.page.wait_for_timeout(1000)
        return organization_name in self.get_text(self.ORGANIZATION_NAME)

    def select_organization_from_list(self, organization_name):
        if self.is_org_selected(organization_name):
            print(f"{organization_name} organization is already selected")
            return
        self.click(self.ORGANIZATION_DROPDOWN)
        container = self.page.locator(self.ORGANIZATION_CONTAINER)
        item = container.locator(f"xpath=.//li[.//p[normalize-space()='{organization_name}']]")
        item.wait_for(state="visible")
        item.click()
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.connect_home_page import ConnectHomePage; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/connect_home_page.py
git commit -m "Add ConnectHomePage to playwright_web"
```

---

### Task 9: `ConnectOpportunitiesPage`

**Files:**
- Create: `playwright_web/pages/connect_opportunities_page.py`

- [ ] **Step 1: Write `playwright_web/pages/connect_opportunities_page.py`**

```python
from datetime import datetime

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class ConnectOpportunitiesPage(BasePage):
    ADD_OPPORTUNITY_BUTTON = locators.get("connect_opportunities_page", "add_opportunity_btn")
    OPP_NAME_INPUT = locators.get("connect_opportunities_page", "name_input")
    OPP_CURRENCY_INPUT = locators.get("connect_opportunities_page", "currency_input")
    OPP_COUNTRY_INPUT = locators.get("connect_opportunities_page", "country_input")
    OPP_SHORT_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "short_description_input")
    OPP_HQ_SERVER_DROPDOWN = locators.get("connect_opportunities_page", "hq_server_dropdown")
    OPP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "description_input")
    OPP_API_KEY_DROPDOWN = locators.get("connect_opportunities_page", "api_key_dropdown")
    OPP_LEARN_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_domain_dropdown")
    OPP_DELIVER_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_domain_dropdown")
    OPP_LEARN_APP_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_dropdown")
    OPP_DELIVER_APP_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_dropdown")
    OPP_LEARN_APP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "learn_app_description")
    OPP_LEARN_APP_PASSING_SCORE_INPUT = locators.get("connect_opportunities_page", "learn_app_passing_score_input")
    SUBMIT_BUTTON = locators.get("connect_opportunities_page", "submit_button")

    ADD_PAYMENT_UNIT_BUTTON = locators.get("connect_opportunities_page", "add_payment_btn")
    AMOUNT_INPUT = locators.get("connect_opportunities_page", "amount_input")
    MAX_TOTAL_INPUT = locators.get("connect_opportunities_page", "max_total_input")
    MAX_DAILY_INPUT = locators.get("connect_opportunities_page", "max_daily_input")
    START_DATE_INPUT = locators.get("connect_opportunities_page", "start_date_input")
    END_DATE_INPUT = locators.get("connect_opportunities_page", "end_date_input")
    REQUIRED_DELIVER_UNITS_SECTION = locators.get("connect_opportunities_page", "required_delivery_section")
    PAYMENT_UNITS_TABLE = locators.get("connect_opportunities_page", "payment_units_table")
    MAX_CONNECT_WORKERS_INPUT = locators.get("connect_opportunities_page", "max_connect_workers")
    SETUP_BUDGET_BUTTON = locators.get("connect_opportunities_page", "setup_budget_btn")
    TOTAL_BUDGET_INPUT = locators.get("connect_opportunities_page", "total_budget_input")
    PAGE_SIZE = locators.get("connect_opportunities_page", "page_size")

    def __init__(self, page):
        super().__init__(page)
        self.opp_full_name = None

    def click_add_opportunity_btn(self):
        self.click(self.ADD_OPPORTUNITY_BUTTON)

    def enter_name_in_opportunity(self, value):
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        self.opp_full_name = f"{value}_{timestamp}"
        self.page.locator(self.OPP_NAME_INPUT).fill(self.opp_full_name)
        return self.opp_full_name

    def select_currency_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_CURRENCY_INPUT, value)

    def select_country_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_COUNTRY_INPUT, value)

    def enter_short_description_in_opportunity(self, value):
        self.page.locator(self.OPP_SHORT_DESCRIPTION_INPUT).fill(value)

    def enter_description_in_opportunity(self, value):
        self.page.locator(self.OPP_DESCRIPTION_INPUT).fill(value)

    def select_hq_server_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_HQ_SERVER_DROPDOWN, value)
        self.page.wait_for_timeout(3000)

    def select_api_key_in_opportunity(self, value):
        self.page.wait_for_timeout(8000)
        self.select_by_visible_text(self.OPP_API_KEY_DROPDOWN, value)

    def select_learn_app_domain_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DOMAIN_DROPDOWN, value)

    def select_deliver_app_domain_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN, value)

    def select_learn_app_in_opportunity(self, value):
        self.page.wait_for_timeout(10000)
        self.scroll_into_view(self.OPP_LEARN_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DROPDOWN, value)

    def select_deliver_app_in_opportunity(self, value):
        self.page.wait_for_timeout(10000)
        self.scroll_into_view(self.OPP_DELIVER_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DROPDOWN, value)

    def enter_learn_app_description_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.page.locator(self.OPP_LEARN_APP_DESCRIPTION_INPUT).fill(value)

    def enter_passing_score_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.page.locator(self.OPP_LEARN_APP_PASSING_SCORE_INPUT).fill(value)

    def click_submit_btn(self):
        self.scroll_into_view(self.SUBMIT_BUTTON)
        self.click(self.SUBMIT_BUTTON, force=True)

    def click_add_payment_unit_button(self):
        self.click(self.ADD_PAYMENT_UNIT_BUTTON)
        self.page.wait_for_url("**/payment_units/create**")

    def enter_amount_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.AMOUNT_INPUT).fill(value)

    def enter_max_daily_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.MAX_DAILY_INPUT).fill(value)

    def enter_max_total_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.MAX_TOTAL_INPUT).fill(value)

    def enter_start_date_in_payment_unit_of_opportunity(self, value):
        self.scroll_into_view(self.START_DATE_INPUT)
        self.enter_date(self.START_DATE_INPUT, value)

    def enter_end_date_in_payment_unit_of_opportunity(self, value):
        self.scroll_into_view(self.END_DATE_INPUT)
        self.enter_date(self.END_DATE_INPUT, value)

    def select_required_deliver_units_checkbox(self, required_text):
        section = self.page.locator(self.REQUIRED_DELIVER_UNITS_SECTION)
        label = section.locator(f"xpath=.//label[contains(normalize-space(.), '{required_text}')]")
        checkbox = label.locator("input")
        if not checkbox.is_checked():
            label.click()

    def verify_payment_unit_present(self, payment_unit_name):
        table = self.page.locator(self.PAYMENT_UNITS_TABLE)
        rows = table.locator("xpath=.//tbody/tr[not(contains(@class,'detail-row'))]")
        for i in range(rows.count()):
            unit_name_cell = rows.nth(i).locator("xpath=./td[2]")
            if unit_name_cell.inner_text().strip() == payment_unit_name:
                return
        raise AssertionError(f"Payment Unit '{payment_unit_name}' not found in UI table")

    def click_setup_budget_button(self):
        self.click(self.SETUP_BUDGET_BUTTON)
        self.page.wait_for_url("**/finalize/**")

    def enter_max_connect_workers_in_budget(self, value):
        self.page.locator(self.MAX_CONNECT_WORKERS_INPUT).fill(value)

    def verify_total_budget_value(self, value):
        self.page.wait_for_timeout(1000)
        actual_value = self.page.locator(self.TOTAL_BUDGET_INPUT).input_value()
        assert actual_value == value, f"Expected total budget value to be '{value}', but got '{actual_value}'"

    def fill_opportunity_form(self, data, learn_app, delivery_app, env):
        env_suffix = f"_{env}" if env == "staging" else ""
        opp_name = self.enter_name_in_opportunity(data["opportunity_name"])
        self.select_currency_in_opportunity(data["currency"])
        self.select_country_in_opportunity(data["country"])
        self.enter_short_description_in_opportunity(data["short_description"])
        self.enter_description_in_opportunity(data["description"])
        self.select_hq_server_in_opportunity(data[f"hq_server{env_suffix}"])
        self.select_api_key_in_opportunity(data[f"api_key{env_suffix}"])
        self.select_learn_app_domain_in_opportunity(data[f"learn_app_domain{env_suffix}"])
        self.select_deliver_app_domain_in_opportunity(data[f"deliver_app_domain{env_suffix}"])
        self.select_learn_app_in_opportunity(learn_app)
        self.select_deliver_app_in_opportunity(delivery_app)
        self.enter_learn_app_description_in_opportunity(data["learn_app_description"])
        self.enter_passing_score_in_opportunity(data["passing_score"])
        self.click_submit_btn()
        return opp_name

    def create_opportunity_in_connect_page(self, data, learn_app, delivery_app, env):
        self.click_add_opportunity_btn()
        self.page.wait_for_timeout(5000)
        try:
            opp_name = self.fill_opportunity_form(data, learn_app, delivery_app, env)
        except Exception:
            self.page.reload()
            self.page.wait_for_timeout(30000)
            opp_name = self.fill_opportunity_form(data, learn_app, delivery_app, env)
        self.page.wait_for_timeout(3000)
        return opp_name

    def create_payment_unit_in_connect_page(self, data):
        self.click_add_payment_unit_button()
        self.enter_name_in_opportunity(data["payment_unit_name"])
        self.enter_amount_in_payment_unit_of_opportunity(data["amount"])
        self.enter_description_in_opportunity(data["description"])
        self.enter_max_total_in_payment_unit_of_opportunity(data["max_total"])
        self.enter_max_daily_in_payment_unit_of_opportunity(data["max_daily"])
        start, end = self.generate_date_range(7)
        self.enter_start_date_in_payment_unit_of_opportunity(start)
        self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.select_required_deliver_units_checkbox(data["required_deliver_units"])
        self.click_submit_btn()
        self.page.wait_for_timeout(3000)
        self.verify_payment_unit_present(self.opp_full_name)

    def setup_budget_in_connect_page(self, data):
        self.click_setup_budget_button()
        start, end = self.generate_date_range(7)
        self.enter_start_date_in_payment_unit_of_opportunity(start)
        self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.enter_max_connect_workers_in_budget(data["no_of_connect_workers"])
        self.verify_total_budget_value(data["total_budget_value"])
        self.click_submit_btn()
        self.page.wait_for_timeout(3000)

    def click_opportunity_in_opportunity(self, value):
        self.page.wait_for_timeout(5000)
        try:
            self.select_by_visible_text(self.PAGE_SIZE, "100")
            self.page.wait_for_timeout(10000)
        except Exception:
            print("Dropdown not present")
        self.click_link_by_text(value)
        self.page.wait_for_timeout(3000)
```

Note: `opp_full_name` moves from a class attribute (as in the original `BaseWebPage.SUBMIT_BUTTON`-style class body) to an instance attribute set in `__init__`, since it's per-test state, not shared/class-level state — a correctness fix opportunistically included since we're already rewriting this class.

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.connect_opportunities_page import ConnectOpportunitiesPage; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/connect_opportunities_page.py
git commit -m "Add ConnectOpportunitiesPage to playwright_web"
```

---

### Task 10: `OpportunityDashboardPage`

**Files:**
- Create: `playwright_web/pages/connect_opportunity_dashboard_page.py`

- [ ] **Step 1: Write `playwright_web/pages/connect_opportunity_dashboard_page.py`**

Only what `test_olp_04` needs — the original class has additional methods (`navigate_to_connect_workers`, `click_hamburger_icon`, etc.) used by out-of-scope tests; those are ported later when those tests are ported.

```python
from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class OpportunityDashboardPage(BasePage):
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page", "dashboard_card")

    def verify_dashboard_card_details_present(self, title, subtitle, count_section=True):
        selector = self.DASHBOARD_CARD.format(title=title, subtitle=subtitle)
        self.scroll_into_view(selector)
        card = self.page.locator(selector)
        card.wait_for(state="visible")
        if count_section:
            count = card.locator("xpath=.//h3[contains(@class,'text-2xl')]").inner_text().strip()
            assert count != "", f"{title} {subtitle} count is empty"
            print(f"{title} {subtitle} in Opportunity Dashboard --> {count}")

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.click_link_by_text(data["opportunity_name"])
        self.verify_dashboard_card_details_present("Connect Workers", "", count_section=False)
        self.verify_dashboard_card_details_present("Tasks Assigned to Connect Workers", "")
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("View Progress Map", "", count_section=False)
        self.verify_dashboard_card_details_present("Audit Opportunity", "", count_section=False)
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")
```

- [ ] **Step 2: Sanity-check the module imports cleanly**

Run: `python -c "from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage; print('ok')"`
Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/pages/connect_opportunity_dashboard_page.py
git commit -m "Add OpportunityDashboardPage to playwright_web"
```

---

### Task 11: `conftest.py` fixtures

**Files:**
- Create: `playwright_web/conftest.py`

- [ ] **Step 1: Write `playwright_web/conftest.py`**

Placed at the `playwright_web/` root (not inside `tests/`), mirroring the existing repo's own `conftest.py`-at-root layout — this is what makes `from pages.xxx import X` / `from utils.helpers import Y` resolve without extra path configuration. `page`, `browser`, and `context` fixtures come from the `pytest-playwright` plugin automatically (installed in Task 1); only the project-specific fixtures are defined here.

```python
import pytest

from utils.helpers import ConfigLoader, SettingsLoader, TestDataLoader


def pytest_addoption(parser):
    parser.addoption(
        "--env",
        action="store",
        default=None,
        help="Environment to run tests against: prod or stage",
    )


@pytest.fixture(scope="session")
def config(request):
    return ConfigLoader(request.config.getoption("--env"))


@pytest.fixture(scope="session")
def settings():
    return SettingsLoader()


@pytest.fixture(scope="session")
def test_data():
    return TestDataLoader()
```

- [ ] **Step 2: Verify fixtures load without error**

Run: `pytest --fixtures -q` (from `playwright_web/`)
Expected: output includes `config`, `settings`, `test_data`, `page`, `browser`, `context` in the fixture list, no errors.

- [ ] **Step 3: Commit**

```bash
git add playwright_web/conftest.py
git commit -m "Add conftest.py fixtures to playwright_web"
```

---

### Task 12: Port `test_olp_01_02_03`

**Files:**
- Create: `playwright_web/tests/test_olp_01_02_03.py`

- [ ] **Step 1: Write `playwright_web/tests/test_olp_01_02_03.py`**

```python
from pages.cchq_application_page import CCHQApplicationPage
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage


def test_olp_01_02_03_setup_budget_in_connect(page, test_data, config, settings):
    olp1_data = test_data.get("OLP_1")
    olp2_data = test_data.get("OLP_2")
    olp3_data = test_data.get("OLP_3")

    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)
    cchq_application_page = CCHQApplicationPage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")
    cchq_login_page.dismiss_guide_popup()

    cchq_home_page.select_app_under_applications_tab("[08/12] Learn App")
    learn_app_name = cchq_application_page.create_copy_of_learn_app()
    cchq_home_page.verify_app_present_under_applications_tab(learn_app_name)

    cchq_home_page.select_app_under_applications_tab("[08/12] Delivey App")
    delivery_app_name = cchq_application_page.create_copy_of_delivery_app()
    cchq_home_page.verify_app_present_under_applications_tab(delivery_app_name)

    connect_page = cchq_login_page.navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)

    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list("PM_Automation_01")

    env = "staging" if "staging" in config.get("cchq_url") else "prod"
    connect_opp_page.create_opportunity_in_connect_page(olp1_data, learn_app_name, delivery_app_name, env)
    connect_opp_page.create_payment_unit_in_connect_page(olp2_data)
    connect_opp_page.setup_budget_in_connect_page(olp3_data)
```

- [ ] **Step 2: Run against `stage` and verify it passes**

Precondition: `settings.cfg` exists at the repo root (`dimagi-qa-ccc/settings.cfg`, copied from `settings-sample.cfg`) with valid `[creds]` `hq_username`/`hq_password`.

Run: `pytest tests/test_olp_01_02_03.py --env=stage -v` (from `playwright_web/`)
Expected: `1 passed`. A new opportunity, payment unit, and budget are created in the `stage` Connect environment under org `PM_Automation_01` — same outcome the Selenium version produces today.

- [ ] **Step 3: Commit**

```bash
git add playwright_web/tests/test_olp_01_02_03.py
git commit -m "Port test_olp_01_02_03 to playwright_web"
```

---

### Task 13: Port `test_olp_04`

**Files:**
- Create: `playwright_web/tests/test_olp_04.py`

- [ ] **Step 1: Write `playwright_web/tests/test_olp_04.py`**

```python
from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunities_page import ConnectOpportunitiesPage
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage


def test_olp_04_verify_opportunity_details_in_dashboard(page, test_data, config, settings):
    olp4_data = test_data.get("OLP_4")

    cchq_login_page = LoginPage(page)
    cchq_home_page = CCHQHomePage(page)

    cchq_login_page.valid_login_cchq(config, settings)
    cchq_home_page.verify_home_page_title("Welcome")

    connect_page = cchq_login_page.navigate_to_connect_page(config)
    connect_home_page = ConnectHomePage(connect_page)
    connect_opp_page = ConnectOpportunitiesPage(connect_page)
    opp_dashboard_page = OpportunityDashboardPage(connect_page)

    connect_home_page.signin_to_connect_page_using_cchq()
    connect_home_page.select_organization_from_list("PM_Automation_01")

    connect_opp_page.click_opportunity_in_opportunity(olp4_data["opportunity_name"])
    opp_dashboard_page.navigate_to_opportunity_and_verify_all_fields_present_in_connect(olp4_data)
```

- [ ] **Step 2: Run against `stage` and verify it passes**

Precondition: same as the original Selenium `test_olp_04` — an opportunity named `"Demo Opportunity"` (per `test_data/web_test_data.yaml` → `OLP_4.opportunity_name`) must already exist under org `PM_Automation_01` in the `stage` environment.

Run: `pytest tests/test_olp_04.py --env=stage -v` (from `playwright_web/`)
Expected: `1 passed`

- [ ] **Step 3: Commit**

```bash
git add playwright_web/tests/test_olp_04.py
git commit -m "Port test_olp_04 to playwright_web"
```

---

### Task 14: Full pilot run

**Files:** None (verification-only task)

- [ ] **Step 1: Run the full pilot suite together**

Run: `pytest --env=stage -v` (from `playwright_web/`)
Expected: `2 passed` (`test_olp_01_02_03`, `test_olp_04`), plus the unit tests from Tasks 2–4 (`test_helpers.py`, `test_base_page.py`) also passing in the same run — `11 passed` total.

- [ ] **Step 2: Confirm no regressions in the existing Selenium suite**

Run: `pytest -v tests/web_tests/test_olp_01_02_03.py tests/web_tests/test_olp_04.py` (from repo root `dimagi-qa-ccc/`)
Expected: both still pass, confirming `playwright_web/` is fully additive and hasn't touched anything under `tests/web_tests/`, `pages/web_pages/`, `locators/web_locators.yaml`, or `utils/helpers.py` at the repo root.

- [ ] **Step 3: Final commit**

```bash
git status
```
Expected: clean (everything from Tasks 1–13 already committed). If anything is outstanding, commit it now with an appropriate message.
