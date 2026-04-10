# AI Test Case Generator

Turn plain-English test descriptions into ready-to-review Python test files — no coding required.

---

## What is this?

This folder contains an AI-powered agent that reads test steps written in simple English
and converts them into properly structured `pytest` test modules for the dimagi-qa-ccc project.

You write what the test should do. The AI writes the code.

---

## Folder overview

```
ai_testcases/
│
├── README.md                        ← you are here
├── FAQ.md                           ← detailed answers to common questions
│
├── generate_test.py                 ← the AI agent script (do not edit)
│
├── sample_web_test.txt              ← blank template for web tests
├── sample_mobile_test.txt           ← blank template for mobile tests
│
├── example_web_opportunity.txt      ← real example: web opportunity test
└── example_mobile_opportunity.txt   ← real example: mobile opportunity test

tests/
├── web_tests/
│   └── test_<your_file_name>.py    ← generated automatically for web tests
└── mobile_tests/
    └── test_<your_file_name>.py    ← generated automatically for mobile tests
```

---

## How to create a test — step by step

### Step 1 — Copy a sample file

Copy one of the sample files and rename it to describe your test.
Do **not** start your filename with `sample_` — those are skipped by the generator.

```
sample_web_test.txt          →  verify_login_flow.txt
sample_mobile_test.txt       →  tc_worker_signup.txt
```

---

### Step 2 — Fill in the header block

Open your new file and fill in each line at the top:

```
Test Name: Verify User Can Log In to CommCare HQ
Test Type: web
Feature: Authentication
Story: User Login Flow
Tags: AUTH_1, AUTH_2
Description:
  This test verifies that a valid program manager can log in to
  CommCare HQ and land on the home page.
```

| Field | What to write |
|-------|--------------|
| **Test Name** | A short sentence describing what the test proves |
| **Test Type** | `web`, `mobile`, or `hybrid` (uses both browser + app) |
| **Feature** | The product area being tested (e.g. `Payments`, `Opportunity`, `Authentication`) |
| **Story** | The user journey being tested |
| **Tags** | The manual test case IDs this automates (e.g. `OLP_1`, `TC_3`, `AUTH_5`) |
| **Description** | 1–3 sentences of context for the report |

---

### Step 3 — Write the test steps

Below the header, write numbered steps in plain English.
Each step should describe **one** action or verification.

```
Steps:

1. Log in to CommCare HQ using the credentials from settings
2. Verify the home page title shows "Welcome"
3. Navigate to the Connect page in a new browser tab
4. Select the organisation "PM_Automation_01" from the list
5. Click "Add Opportunity"
6. Enter the opportunity name from test data OLP_10
7. Click Save
8. Verify the opportunity name appears in the list
```

**Writing tips:**

- Start action steps with a verb: *Click*, *Enter*, *Select*, *Navigate*, *Tap*, *Scroll*
- Start check steps with *Verify* or *Assert*: `Verify the error message reads "Invalid code"`
- When data comes from the test data files, say so: `from test data TC_5`
- One action per step — do not combine multiple things on one line
- Be specific about what you expect to see, not just that something appears

**Good example:**
```
5. Enter the phone number "7426050" with country code "+7426" from test data TC_5
6. Verify the backup code screen is shown with the username from test data TC_5
```

**Too vague:**
```
5. Enter phone details
6. Check the next screen
```

---

### Step 3b — Multiple test cases in one file (optional)

You can put several test cases into a single `.txt` file.
Separate them with `[TEST CASE N]` markers — the generator produces
one Python test function per block, all in the same output file.

```
[TEST CASE 1]
Test Name: Verify Login to CommCare HQ
Test Type: web
Feature: Authentication
Story: Program Manager Login
Tags: AUTH_1
Description:
  Verifies a program manager can log in and see the dashboard.

Steps:
1. Open CommCare HQ using the environment URL
2. Enter username and password from settings
3. Click Sign In
4. Verify the home page title shows "Welcome"


[TEST CASE 2]
Test Name: Verify Navigate to Connect Page
Test Type: web
Feature: Authentication
Story: Navigate from CommCare HQ to Connect
Tags: AUTH_2
Description:
  Verifies the user can reach the Connect page after login.

Steps:
1. Log in to CommCare HQ using credentials from settings
2. Open the Connect page in a new browser tab
3. Verify the Connect URL is correct
```

The output will be one `.py` file containing `test_verify_login_to_commcare_hq` and
`test_verify_navigate_to_connect_page` as separate functions.

**Rules for multi-test files:**
- Start each block with `[TEST CASE N]` (e.g. `[TEST CASE 1]`, `[TEST CASE 2]`)
- Every block needs its own `Test Name`, `Test Type`, `Feature`, `Story`, `Tags`, and `Steps`
- All test cases in one file should be the same `Test Type` (all web, or all mobile)
- The output directory is decided by the first `Test Type` in the file
- See `example_multi_web.txt` in this folder for a complete working example

---

### Step 4 — Add a test data block (optional)

If your test needs specific data values, add a commented-out block at the bottom
of your `.txt` file showing what to add to the YAML files.
The generator will include this as a comment in the output so a developer can wire it up.

```
# ---------------------------------------------------------------
# Test Data — add these entries to test_data/web_test_data.yaml
# ---------------------------------------------------------------
# OLP_10:
#   opportunity_name: "Automation Opportunity March"
#   currency: "USD (US Dollar)"
#   passing_score: "50"
```

---

### Step 5 — Generate the test

You have two ways to generate. Choose whichever suits you.

---

**Option A — Run locally on your machine**

This is the fastest way to see the result immediately. You need Python installed.

**One-time setup:**

```bash
# 1. Install the OpenAI package
pip install openai

# 2. Make sure your API key is in settings.cfg at the project root:
#    OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxx
#    (This is already done if your team lead set it up)
```

**Generate from a specific file:**

```bash
python ai_testcases/generate_test.py ai_testcases/verify_login_flow.txt
```

Expected output:
```
[PROCESSING] verify_login_flow.txt
  Calling OpenAI API for: verify_login_flow.txt ...
  [OK] Generated → tests/web_tests/test_verify_login_flow.py
```

**Generate from all `.txt` files in the folder at once** (sample files are skipped):

```bash
python ai_testcases/generate_test.py
```

**Send output to a specific folder:**

```bash
python ai_testcases/generate_test.py ai_testcases/verify_login_flow.txt --output tests/web_tests/
```

The generated `.py` file is written immediately — no commit or push needed to see it.

---

**Option B — Let GitHub Actions generate it for you (no local setup needed)**

Just commit your `.txt` file and push it to any branch except `main`.
The CI workflow runs automatically and commits the generated `.py` file back to your branch
within a couple of minutes. No local setup needed.

```
git add ai_testcases/verify_login_flow.txt
git commit -m "add test description for login flow"
git push
```

Then check the **Actions** tab on GitHub — within ~2 minutes the generated test appears
in `tests/web_tests/test_verify_login_flow.py` on your branch as an auto-commit.

---

**Which option should I use?**

| Situation | Use |
|-----------|-----|
| You want to see the result immediately | Option A (local) |
| You don't have Python set up locally | Option B (CI) |
| You want to iterate quickly on the `.txt` file | Option A (local) |
| You're a non-coder who only uses GitHub | Option B (CI) |

---

### Step 6 — Review the generated file

The agent outputs the path of the generated file:

```
[PROCESSING] verify_login_flow.txt
  Calling OpenAI API ...
  [OK] Generated → tests/web_tests/test_verify_login_flow.py
```

Open the generated file. It will contain:

- All required imports
- Allure report decorators (`@allure.feature`, `@allure.story`, `@allure.tag`, `@allure.description`)
- A pytest marker (`@pytest.mark.web` or `@pytest.mark.mobile`)
- Each step wrapped in `with allure.step("..."):`
- Assertions where you wrote *Verify* or *Assert*
- `# TODO` comments where the agent couldn't find a matching page method
- A comment block at the bottom with any test data YAML to add

Share the file with a developer. They will:
1. Fill in any `# TODO` items
2. Add the test data to the correct YAML file
3. Do a quick smoke run to confirm it works

---

## Complete example

Here is a full `.txt` input and the kind of output it produces.

**Input file: `verify_login.txt`**

```
Test Name: Verify CommCare HQ Login
Test Type: web
Feature: Authentication
Story: Program Manager Login
Tags: AUTH_1
Description:
  Verifies a program manager can log in to CommCare HQ
  and see the home dashboard.

Steps:
1. Open CommCare HQ using the environment URL
2. Enter username from settings credentials
3. Enter password from settings credentials
4. Click Sign In
5. Verify home page title shows "Welcome"
```

**Output file: `tests/web_tests/test_verify_login.py`**

```python
"""
Test: Verify CommCare HQ Login
Covers manual test cases: AUTH_1
"""
import allure
import pytest
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage


@allure.feature("Authentication")
@allure.story("Program Manager Login")
@allure.tag("AUTH_1")
@allure.description(
    "Verifies a program manager can log in to CommCare HQ and see the home dashboard."
)
@pytest.mark.web
def test_verify_login(web_driver, test_data, config, settings):

    login_page = LoginPage(web_driver)
    home_page  = CCHQHomePage(web_driver)

    with allure.step("Open CommCare HQ and log in"):
        login_page.valid_login_cchq(config, settings)

    with allure.step("Verify home page title shows 'Welcome'"):
        home_page.verify_home_page_title("Welcome")
```

---

## File naming rules

| Your `.txt` file | Generated test file |
|-----------------|---------------------|
| `verify_login.txt` | `tests/web_tests/test_verify_login.py` |
| `tc_worker_signup.txt` | `tests/mobile_tests/test_tc_worker_signup.py` |
| `test_budget_flow.txt` | `tests/web_tests/test_budget_flow.py` |

- The `test_` prefix is added automatically if your filename doesn't start with it.
- Web tests go to `tests/web_tests/`, mobile tests go to `tests/mobile_tests/`.

---

## API key setup (local use only)

For local generation the agent reads your OpenAI key from `settings.cfg` at the project root.
Open that file and replace the placeholder:

```
OPENAI_API_KEY=your-openai-api-key-here
```

For CI the key is already stored in GitHub Secrets — nothing extra to configure.

---

## More help

See `FAQ.md` in this folder for detailed answers to common questions including
what the agent can and cannot do, how accurate the output is, and how to handle errors.
