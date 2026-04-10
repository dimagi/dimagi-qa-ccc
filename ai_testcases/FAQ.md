# AI Test Case Generator — FAQ

Answers to the most common questions about the AI agent, what it does, and what it does not do.

---

## What the agent does

---

### What exactly does the AI agent do?

It reads a `.txt` file you write (containing plain-English test steps) and converts it into a
properly structured Python pytest test file.

The generated file follows all project conventions:
- Correct imports for page objects and utilities
- Allure report decorators on the test function
- Each step wrapped in `with allure.step("..."):`
- Assertions where you wrote "Verify" or "Assert"
- The correct pytest markers (`@pytest.mark.web` or `@pytest.mark.mobile`)

---

### What does a generated test file look like?

It looks exactly like the hand-written tests already in the `tests/` folder.
Here is a short example:

```python
import allure
import pytest
from pages.web_pages.cchq_login_web_page import LoginPage
from pages.web_pages.cchq_home_web_page import CCHQHomePage

@allure.feature("Authentication")
@allure.story("Program Manager Login")
@allure.tag("AUTH_1")
@allure.description("Verifies a program manager can log in and see the dashboard.")
@pytest.mark.web
def test_verify_login(web_driver, test_data, config, settings):

    login_page = LoginPage(web_driver)
    home_page  = CCHQHomePage(web_driver)

    with allure.step("Log in to CommCare HQ"):
        login_page.valid_login_cchq(config, settings)

    with allure.step("Verify home page title shows 'Welcome'"):
        home_page.verify_home_page_title("Welcome")
```

---

### Does the agent access the browser, the app, or any live system?

No. The agent only reads the `.txt` file you wrote and generates Python code.
It does not open a browser, connect to an app, or talk to CommCare HQ / Connect.
All of that happens later when a developer runs the generated test.

---

### Does it run the test to check if it works?

No. The agent generates the code but does not execute it.
A developer needs to review the output, fill in any `# TODO` items, and do a trial run.

---

### Where does the generated file go?

| Test type in your `.txt` | Output location |
|--------------------------|----------------|
| `web` | `tests/web_tests/test_<your_filename>.py` |
| `mobile` | `tests/mobile_tests/test_<your_filename>.py` |
| `hybrid` | `tests/mobile_tests/test_<your_filename>.py` |

The `test_` prefix is added to your filename automatically if it is missing.

---

### What does "hybrid" test type mean?

A hybrid test uses both a web browser (CommCare HQ / Connect website) and the mobile app
in the same test. For example: a test that creates an opportunity on the web, then verifies
the invite appears on the mobile app.

Write `Test Type: hybrid` in your `.txt` file and describe steps for both platforms.

---

## What the agent does NOT do

---

### Can the agent create new page objects?

No. The agent only creates the test file.

If a step requires a page object method that does not exist yet, the agent adds a
`# TODO` comment in the generated file:

```python
with allure.step("Click the Withdraw button"):
    # TODO: no existing method found for this action — developer must implement
    # connect_opp_page.click_withdraw_button()
```

A developer then creates the method in the relevant page object file.

---

### Can the agent add locators?

No. Adding locators to `locators/mobile_locators.yaml` or `locators/web_locators.yaml`
requires inspecting the actual app UI. The agent does not have access to the app.
The `# TODO` comments in the generated file will indicate where locators are needed.

---

### Can the agent update test data YAML files?

No, but it tells you exactly what to add.
At the bottom of the generated file there is a commented block like:

```python
# ---------------------------------------------------------------
# Add to test_data/web_test_data.yaml:
# OLP_10:
#   opportunity_name: "Automation Opportunity March"
#   currency: "USD (US Dollar)"
# ---------------------------------------------------------------
```

Copy that block, remove the `#` characters, and paste it into the correct YAML file.

---

### Can the agent run tests automatically in CI?

The agent generates test files in CI when you push a `.txt` file.
It does NOT run those tests — the existing CI workflow (`dimagi_pytest.yaml`) handles that
separately when you merge to `main`.

---

### Will the generated test always be 100% correct?

No. The agent is a smart first draft, not a guarantee.
It follows the project patterns closely but it can:
- Pick the wrong page object method if the step description is vague
- Add a `# TODO` where it is uncertain
- Use a method name that is slightly different from the real one

Always have a developer review the output before merging.

---

## Using the agent

---

### Do I need to know Python or coding to use this?

No. You only need to write plain English in a `.txt` file.
The agent and the developer handle everything else.

---

### How specific do my steps need to be?

More specific = better generated code.

| Too vague | Better |
|-----------|--------|
| Enter phone details | Enter the phone number "7426050" with country code "+7426" from test data TC_5 |
| Check the screen | Verify the backup code entry screen is shown with the username from test data TC_5 |
| Click the button | Click the "Accept" button on the opportunity details screen |

---

### What if my test needs data from the test data files?

Reference the test data by its ID in your step:

```
6. Enter the opportunity name from test data OLP_10
```

Then add a commented YAML block at the bottom of your `.txt` file showing the data.
The agent will include this in the generated file as a reminder for the developer.

---

### Can I put multiple test cases in one file?

Yes. Use `[TEST CASE N]` markers to separate them:

```
[TEST CASE 1]
Test Name: Verify Login
Test Type: web
...
Steps:
1. Open CommCare HQ
2. Enter credentials and sign in
3. Verify home page shows "Welcome"


[TEST CASE 2]
Test Name: Verify Navigate to Connect
Test Type: web
...
Steps:
1. Log in to CommCare HQ
2. Open Connect page in new tab
3. Verify Connect URL is correct
```

The agent generates one Python test function per block, all in the same output `.py` file.
If the test cases share setup steps (like login), the agent extracts a shared helper function
to avoid duplicating code.

See `example_multi_web.txt` for a complete working example.

---

### Can I describe a test that covers more than one manual test case?

Yes — that is encouraged. Put all the manual test case IDs in the `Tags:` line:

```
Tags: OLP_1, OLP_2, OLP_3
```

The agent will reference all of them in the Allure report decorators and the docstring.

---

### Can I generate multiple tests at once?

Yes. Place several `.txt` files in the `ai_testcases/` folder and either:
- Push them all at once (CI processes each one)
- Run `python ai_testcases/generate_test.py` locally (processes all non-sample files)

---

### How do I update a test I already generated?

Edit the original `.txt` file with the updated steps, then re-run the generator.
The generator will overwrite the existing `.py` file with the new version.

Note: if a developer has already manually edited the `.py` file, those edits will be lost.
Coordinate with your developer before regenerating.

---

### What files should I never delete or rename in this folder?

| File | Why |
|------|-----|
| `generate_test.py` | The agent itself — deleting it breaks everything |
| `sample_web_test.txt` | Template for others to copy |
| `sample_mobile_test.txt` | Template for others to copy |

Your own `.txt` files are safe to rename or delete anytime.

---

## CI / GitHub Actions

---

### How does CI generation work?

When you push a `.txt` file to any branch (except `main`), GitHub Actions:
1. Detects the changed `.txt` file
2. Runs the AI generator using the `OPENAI_API_KEY` stored in GitHub Secrets
3. Commits the generated `.py` file back to your branch automatically

You will see a commit appear on your branch from `github-actions[bot]` with the message:
`auto: generate test modules from ai_testcases/ [skip ci]`

---

### How long does CI generation take?

Usually 1–3 minutes from the time you push.

---

### What does `[skip ci]` mean on the auto-commit?

It tells GitHub Actions not to run the generator again for that commit.
Without it the generator would re-trigger itself in an infinite loop.

---

### Do I need to set up the OpenAI key for CI?

The key is already stored in GitHub Secrets as `OPENAI_API_KEY`.
Nothing extra is needed — CI picks it up automatically.

---

### The CI generation failed. What do I check?

1. **GitHub Actions tab** — open the failed run and read the error message.
2. **Common causes:**
   - The `OPENAI_API_KEY` secret expired or was not set → ask your team lead
   - The `.txt` file has a formatting problem → check the header block matches the template
   - A network error → re-push the same commit to retry

---

## API key and security

---

### Where is the OpenAI API key stored?

| Location | Used for |
|----------|---------|
| `settings.cfg` (local, git-ignored) | Local generation on your machine |
| GitHub Secrets (`OPENAI_API_KEY`) | CI generation on GitHub Actions |

The key is never committed to the repository.

---

### Is my test description sent to OpenAI?

Yes — the content of your `.txt` file is sent to the OpenAI API (GPT-4o) to generate the code.
Do not include real usernames, passwords, or sensitive personal data in your `.txt` files.
Use placeholder references like "from test data TC_5" instead.

---

### Can someone outside the team see my test descriptions?

No. The OpenAI API processes your input but does not make it public.
Refer to the OpenAI data usage policy for full details.

---

## Troubleshooting

---

### The generator printed `[FAIL]` for my file. What do I do?

Check the error message printed below `[FAIL]`. Common causes:

| Error | Fix |
|-------|-----|
| `OPENAI_API_KEY not found` | Add the key to `settings.cfg` or set the env variable |
| `File not found` | Check the file path you passed as an argument |
| `openai not installed` | Run `pip install openai` |
| `RateLimitError` from OpenAI | Wait a minute and try again |

---

### The generated test imports a page object that doesn't exist.

The agent works from a known list of existing page objects. If you described an action
on a page that doesn't have a page object yet, it will either:
- Make a reasonable guess and add a `# TODO`
- Import from an existing similar page object

In either case, a developer must review and correct the import.

---

### I don't see a generated file after pushing to GitHub.

1. Go to the **Actions** tab on GitHub and check if the `AI Test Case Generator` workflow ran.
2. If it did not run, check that your `.txt` file is inside `ai_testcases/` (not a subfolder).
3. If you are on the `main` branch, the workflow will not run — use a feature branch.
4. If it ran and failed, read the error in the workflow logs.
