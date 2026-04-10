#!/usr/bin/env python3
"""
AI Test Case Generator for dimagi-qa-ccc
=========================================
Converts plain English test steps from .txt files into pytest test modules.

Usage:
    # Generate from a specific .txt file:
    python ai_testcases/generate_test.py ai_testcases/my_test.txt

    # Process all .txt files in ai_testcases/ (skipping samples):
    python ai_testcases/generate_test.py

    # Specify a custom output directory:
    python ai_testcases/generate_test.py ai_testcases/my_test.txt --output tests/web_tests/

Requirements:
    pip install openai
    Set OPENAI_API_KEY either as an environment variable  OR
    add the line  OPENAI_API_KEY=sk-...  to settings.cfg at the project root.
"""

import os
import sys
import re
import argparse
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] The 'openai' package is not installed.")
    print("        Run:  pip install openai")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_TESTCASES_DIR = Path(__file__).resolve().parent


def _load_api_key() -> str:
    """
    Resolve the OpenAI API key using this priority order:
      1. OPENAI_API_KEY environment variable
      2. OPENAI_API_KEY=<value> line inside settings.cfg at the project root
    """
    # 1. Environment variable
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key

    # 2. settings.cfg (plain key=value, no section headers required)
    cfg_path = PROJECT_ROOT / "settings.cfg"
    if cfg_path.exists():
        for line in cfg_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY"):
                _, _, value = line.partition("=")
                value = value.strip()
                if value:
                    return value

    return ""

# ---------------------------------------------------------------------------
# Project context injected into every Claude prompt so it can produce
# idiomatic code that matches the existing test framework exactly.
# ---------------------------------------------------------------------------
PROJECT_CONTEXT = """
## Project: dimagi-qa-ccc  (CommCare Connect QA Automation)

### Tech Stack
- Python pytest with Selenium (web) and Appium (mobile)
- Page Object Model pattern
- YAML-based locators and test data
- Allure + pytest-html reporting

### Directory Layout
tests/
  mobile_tests/   ← mobile test files  (e.g. test_tc_01.py)
  web_tests/      ← web test files     (e.g. test_olp_01_02_03.py)
pages/
  mobile_pages/   ← mobile page objects (inherit BasePage)
  web_pages/      ← web page objects   (inherit BaseWebPage)
locators/
  mobile_locators.yaml
  web_locators.yaml
test_data/
  mobile_workers.yaml
  web_test_data.yaml
utils/
  helpers.py      ← ConfigLoader, SettingsLoader, LocatorLoader, TestDataLoader
  utility.py      ← simulate_fingerprint, open_notification, etc.

### Pytest Fixtures  (conftest.py)
- mobile_driver  → Appium driver; only created when test has @pytest.mark.mobile
- web_driver     → Selenium Chrome driver; only created when @pytest.mark.web
- test_data      → TestDataLoader().get("TC_ID") → dict
- config         → ConfigLoader(env); config.get("cchq_url"), config.get("connect_url")
- settings       → SettingsLoader(); settings.get(section, key, env_var, default)

### Markers
@pytest.mark.mobile   → runs with mobile_driver
@pytest.mark.web      → runs with web_driver
@pytest.mark.smoke    → smoke tests
@pytest.mark.bugasura("TES11") → links to Bugasura IDs

### Allure Decorators (always include)
@allure.feature("FEATURE_NAME")
@allure.story("Story description")
@allure.tag("TC_1", "TC_2")
@allure.description("Multi-line description of what is covered")
with allure.step("Step description"):
    ...

### Web Base Page  (pages/web_pages/base_web_page.py)
class BaseWebPage:
    def __init__(self, driver): self.driver = driver; self.wait = WebDriverWait(driver, 30)
    def click_element(self, locator): ...
    def type_element(self, locator, text): ...
    def wait_for_element(self, locator): ...
    def get_text(self, locator): ...
    def is_displayed(self, locator, timeout=10): ...
    def select_by_visible_text(self, dropdown_locator, text): ...
    def scroll_to_element(self, locator): ...
    def js_click(self, locator, timeout=10): ...
    def open_url_in_new_tab(self, url): ...
    def switch_to_latest_tab(self): ...
    def wait_for_page_load(self): ...

### Mobile Base Page  (pages/mobile_pages/base_page.py)
class BasePage:
    def __init__(self, driver): self.driver = driver; self.wait = WebDriverWait(driver, 60)
    def click_element(self, locator): ...
    def type_element(self, locator, text): ...
    def wait_for_element(self, locator): ...
    def get_text(self, locator): ...
    def is_displayed(self, locator, timeout=10): ...
    def scroll_down(self): ...
    def scroll_to_text(self, text, max_swipes=30): ...
    def tap_element(self, locator): ...

### Locator Loading
# At the top of a page object file:
from utils.helpers import LocatorLoader
locators = LocatorLoader("locators/web_locators.yaml", platform="web")
# or
locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

# In the class body:
MY_BUTTON = locators.get("page_section", "element_key")
# XPath if value starts with "//" or "(", otherwise ID

### Test Data Loading
from utils.helpers import TestDataLoader
# In test function:
data = test_data.get("TC_1")   # dict with all keys from YAML

### Existing Web Page Objects (importable)
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage
from pages.web_pages.connect_home_web_page import ConnectHomePage
from pages.web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage
from pages.web_pages.cchq_application_web_page import CCHQApplicationPage

### Existing Mobile Page Objects (importable)
from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from pages.mobile_pages.opportunity_page import OpportunityPage

### Canonical Web Test Template
```python
import allure
import pytest
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage

@allure.feature("FEATURE")
@allure.story("Story")
@allure.tag("TC_ID")
@allure.description("Description of what the test covers.")
@pytest.mark.web
def test_example(web_driver, test_data, config, settings):
    data = test_data.get("TC_ID")
    login_page = LoginPage(web_driver)
    home_page  = CCHQHomePage(web_driver)

    with allure.step("Login to CommCare HQ"):
        login_page.valid_login_cchq(config, settings)

    with allure.step("Verify home page"):
        home_page.verify_home_page_title("Welcome")
```

### Canonical Mobile Test Template
```python
import allure
import pytest
from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.personal_id_page import PersonalIDPage

@allure.feature("FEATURE")
@allure.story("Story")
@allure.tag("TC_ID")
@allure.description("Description.")
@pytest.mark.mobile
def test_example(mobile_driver, test_data):
    data = test_data.get("TC_1")
    home = HomePage(mobile_driver)
    pid  = PersonalIDPage(mobile_driver)

    with allure.step("Open side menu and click sign in"):
        home.open_side_menu()
        home.click_signup()

    with allure.step("Start signup with phone number"):
        pid.start_signup(data["country_code"], data["phone_number"])
```
"""

# ---------------------------------------------------------------------------
# The instruction Claude receives for generating the test file
# ---------------------------------------------------------------------------
GENERATION_SYSTEM_PROMPT = f"""
You are a senior QA automation engineer working on the dimagi-qa-ccc project.
Your job is to convert plain-English test steps (written by non-developers) into
a complete, runnable pytest test module that follows the project conventions exactly.

{PROJECT_CONTEXT}

### Output rules
1. Output ONLY the Python file content — no markdown fences, no prose, no explanation.
2. The file must be self-contained and importable by pytest with no modifications.
3. Use only imports that exist in the project (listed above). If a step requires
   a page object or method that doesn't clearly exist, add a TODO comment instead
   of inventing an import.
4. Always include all four Allure decorators on EVERY test function: @allure.feature,
   @allure.story, @allure.tag, @allure.description.
5. Wrap every logical action in  `with allure.step("..."):`.
6. Use assertions where the user specifies a verification/check step.
7. Match the test type (web / mobile / hybrid) declared in the input.
8. If the test type is "hybrid", include both @pytest.mark.mobile and @pytest.mark.web
   and accept both mobile_driver and web_driver fixtures.
9. Add a file-level docstring summarising what the file covers (list all test case names).
10. If specific test data keys are referenced in the steps, use test_data.get("TC_ID")
    and access dict keys. Add a YAML snippet at the bottom as a comment block showing
    the test data that should be added to the appropriate YAML file.

### Multiple test cases in one file
11. If the input contains multiple test cases separated by [TEST CASE N] markers,
    generate ONE Python test function per test case block, all in the same file.
    - All functions share the same import block at the top of the file.
    - Deduplicate imports — do not repeat the same import for every function.
    - Each function gets its own full set of four Allure decorators.
    - Name each function after its "Test Name" field converted to snake_case,
      prefixed with test_ (e.g. "Verify Login Flow" → test_verify_login_flow).
    - If test cases share setup steps (e.g. login), extract a shared helper function
      called by each test rather than duplicating the code.
"""


def read_txt_file(path: Path) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def count_test_cases(txt_content: str) -> int:
    """Return the number of [TEST CASE N] blocks found in the file."""
    return len(re.findall(r"^\[TEST CASE\s+\d+\]", txt_content, re.MULTILINE | re.IGNORECASE))


def infer_output_path(txt_content: str, txt_path: Path) -> Path:
    """Determine where to save the generated test file.

    Uses the first Test Type found in the file to pick the output directory,
    so multi-test files work correctly when types are mixed.
    """
    test_type_match = re.search(r"(?i)^test\s+type\s*:\s*(\w+)", txt_content, re.MULTILINE)
    test_type = test_type_match.group(1).lower() if test_type_match else "web"

    stem = txt_path.stem
    if not stem.startswith("test_"):
        stem = "test_" + stem

    if test_type == "mobile":
        return PROJECT_ROOT / "tests" / "mobile_tests" / f"{stem}.py"
    else:
        return PROJECT_ROOT / "tests" / "web_tests" / f"{stem}.py"


def generate_test(txt_path: Path, output_path: Path = None) -> Path:
    """
    Call the OpenAI API to convert plain-English steps → pytest module.
    Supports both single-test and multi-test (multiple [TEST CASE N] blocks) files.

    Parameters
    ----------
    txt_path    : path to the input .txt file
    output_path : where to write the generated .py file (auto-inferred if None)

    Returns
    -------
    Path to the generated test file
    """
    api_key = _load_api_key()
    if not api_key:
        print("[ERROR] OpenAI API key not found.")
        print("        Either:")
        print("          a) Set the environment variable:  OPENAI_API_KEY=sk-...")
        print("          b) Add this line to settings.cfg: OPENAI_API_KEY=sk-...")
        sys.exit(1)

    txt_content = read_txt_file(txt_path)

    if output_path is None:
        output_path = infer_output_path(txt_content, txt_path)

    n_cases = count_test_cases(txt_content)
    multi_note = (
        f"\nThis file contains {n_cases} test cases separated by [TEST CASE N] markers. "
        "Generate one test function per block in a single Python file.\n"
        if n_cases > 1 else ""
    )

    user_message = f"""
Convert the following plain-English test description into a complete pytest test module
for the dimagi-qa-ccc project. Follow all conventions described in the system prompt.
{multi_note}
--- BEGIN TEST DESCRIPTION ---
{txt_content}
--- END TEST DESCRIPTION ---

Output file should be saved as: {output_path.name}
"""

    case_label = f"{n_cases} test cases" if n_cases > 1 else "1 test case"
    print(f"  Calling OpenAI API for: {txt_path.name} ({case_label}) …")

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o",
        max_tokens=4096,
        messages=[
            {"role": "system", "content": GENERATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    generated_code = response.choices[0].message.content.strip()

    # Strip accidental markdown fences if the model wraps output
    if generated_code.startswith("```"):
        lines = generated_code.splitlines()
        # Remove first line (```python or ```) and last line (```)
        generated_code = "\n".join(lines[1:-1]).strip()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(generated_code, encoding="utf-8")

    return output_path


def process_all(ai_dir: Path) -> None:
    """Process every .txt file in ai_dir, skipping sample_ prefixed files."""
    txt_files = sorted(ai_dir.glob("*.txt"))
    skippable = {"sample_web_test.txt", "sample_mobile_test.txt"}

    targets = [f for f in txt_files if f.name not in skippable]

    if not targets:
        print("[INFO] No .txt files found to process (sample files are skipped).")
        print("       Drop your own .txt file into the ai_testcases/ folder and re-run.")
        return

    for txt_path in targets:
        print(f"\n[PROCESSING] {txt_path.name}")
        try:
            out = generate_test(txt_path)
            print(f"  [OK] Generated → {out.relative_to(PROJECT_ROOT)}")
        except Exception as exc:
            print(f"  [FAIL] {exc}")


def main():
    parser = argparse.ArgumentParser(
        description="AI Test Case Generator — converts .txt test steps to pytest modules."
    )
    parser.add_argument(
        "txt_file",
        nargs="?",
        help="Path to a specific .txt file. Omit to process all files in ai_testcases/.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output directory or full file path for the generated test (optional).",
    )
    args = parser.parse_args()

    if args.txt_file:
        txt_path = Path(args.txt_file).resolve()
        if not txt_path.exists():
            print(f"[ERROR] File not found: {txt_path}")
            sys.exit(1)

        output_path = None
        if args.output:
            out = Path(args.output)
            if out.suffix == ".py":
                output_path = out.resolve()
            else:
                # Treat as directory
                stem = txt_path.stem
                if not stem.startswith("test_"):
                    stem = "test_" + stem
                output_path = (out / f"{stem}.py").resolve()

        print(f"\n[PROCESSING] {txt_path.name}")
        out = generate_test(txt_path, output_path)
        print(f"  [OK] Generated → {out.relative_to(PROJECT_ROOT)}")
    else:
        process_all(AI_TESTCASES_DIR)


if __name__ == "__main__":
    main()
