# Maestro Mobile Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stand up a `maestro_mobile/` project inside `dimagi-qa-ccc` and port the two pilot mobile tests (`test_tc_01`, `test_tc_02`) from the existing Appium/Pytest suite into Maestro YAML flows, verified against a local Android Studio emulator.

**Architecture:** Declarative Maestro flow files replace the Page-Object-Model Appium classes. The shared login/signup steps (up through entering the username) live in one reusable sub-flow (`shared_login_signup.yaml`) invoked via `runFlow` from each of the two pilot flows, mirroring how `PersonalIDPage.start_signup()`/`enter_name()` are shared today. Test data mirrors the shape of `test_data/mobile_workers.yaml`. A thin Python runner (`scripts/run_tests.py`) reads that data and invokes `maestro test` with `-e` overrides, matching the design spec's phase-1 (local) execution model — BrowserStack (phase 2) is explicitly out of scope for this plan.

**Tech Stack:** Maestro CLI, YAML flow files, Python 3 (runner script only, uses PyYAML), Android Studio emulator + ADB, `app-cccStaging-release.apk`.

**Source of truth for behavior:** `tests/mobile_tests/test_tc_01.py`, `test_tc_02.py`, `pages/mobile_pages/personal_id_page.py`, `pages/mobile_pages/home_page.py`, `locators/mobile_locators.yaml`, `test_data/mobile_workers.yaml`.

**Known simplifications vs. the Appium suite** (confirmed acceptable — the custom staging APK skips the fingerprint screen entirely, `BasePage.BIOMETRIC_ENABLED` defaults to `false`):
- Fingerprint/biometric steps (`click_configure_fingerprint`, `handle_fingerprint_auth`, `demo_user_confirm`) are dropped entirely — they're gated behind the same disabled flag in the existing Python suite, so this is not a behavior change for this APK.
- The network-error retry loop in `PersonalIDPage.start_signup()` is not ported; the flow just waits for the progress bar to clear once. If flaky network conditions show up during verification, this is the first thing to revisit.

**Two locators in `mobile_locators.yaml` have no resource-id** (they're structural XPath: `home_page.navigation_drawer_btn`, `home_page.more_option_btn`) — Maestro doesn't support XPath. Task 2 and Task 3 each include an explicit **Maestro Studio discovery step** to pin down the real selector against the live app before the flow can be verified. Best-guess placeholders (`point:` percentage taps) are included so there's a concrete starting point, but they are expected to be replaced during verification, not treated as final.

---

### Task 1: Scaffold the `maestro_mobile/` project

**Files:**
- Create: `maestro_mobile/test_data/mobile_test_data.yaml`
- Create: `maestro_mobile/scripts/run_tests.py`
- Create: `maestro_mobile/README.md`

- [ ] **Step 1: Create the test data file**

```yaml
# maestro_mobile/test_data/mobile_test_data.yaml
TC_1:
  country_code: "+7426"
  phone_number: "7426000"
  username: "Deb Test 8/12"
  backup_code: "742600"

TC_2:
  country_code: "+7426"
  phone_number: "7426005"
  username: "Deb Test 161202"
  backup_code: "742605"
```

- [ ] **Step 2: Create the runner script**

```python
# maestro_mobile/scripts/run_tests.py
import argparse
import subprocess
import sys
from pathlib import Path

import yaml

FLOWS_DIR = Path(__file__).parent.parent / "flows"
TEST_DATA_FILE = Path(__file__).parent.parent / "test_data" / "mobile_test_data.yaml"

FLOW_BY_CASE = {
    "TC_1": "login_signup_success.yaml",
    "TC_2": "login_account_locked.yaml",
}


def load_test_data(case_key):
    with open(TEST_DATA_FILE) as f:
        data = yaml.safe_load(f)
    return data[case_key]


def run_flow(case_key):
    data = load_test_data(case_key)
    flow_file = FLOWS_DIR / FLOW_BY_CASE[case_key]

    cmd = [
        "maestro", "test", str(flow_file),
        "-e", f"COUNTRY_CODE={data['country_code']}",
        "-e", f"PHONE_NUMBER={data['phone_number']}",
        "-e", f"USERNAME={data['username']}",
        "-e", f"BACKUP_CODE={data['backup_code']}",
    ]
    result = subprocess.run(cmd)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run Connect Maestro mobile flows locally")
    parser.add_argument("case", choices=sorted(FLOW_BY_CASE), help="Test case key to run, e.g. TC_1")
    args = parser.parse_args()

    sys.exit(run_flow(args.case))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Create the README**

```markdown
# Maestro Mobile Tests

Pilot Maestro port of the Appium mobile suite in `tests/mobile_tests/`. Covers `test_tc_01` and `test_tc_02` only — see `docs/superpowers/specs/2026-07-06-maestro-mobile-migration-pilot-design.md` for the full migration plan.

## Prerequisites
- Maestro CLI installed (`curl -Ls "https://get.maestro.mobile.dev" | bash`)
- Android Studio emulator running, or a physical device connected over ADB
- `app-cccStaging-release.apk` installed on that target: `adb install ../../commcare-android/app/app-cccStaging-release.apk`

## Running a flow directly
maestro test flows/login_signup_success.yaml

## Running via the data-driven runner
python scripts/run_tests.py TC_1
python scripts/run_tests.py TC_2

## Debugging
maestro studio   # interactive element inspector against the running emulator/device
```

- [ ] **Step 4: Verify the runner script's argparse wiring**

Run: `python maestro_mobile/scripts/run_tests.py --help`
Expected: prints usage showing `{TC_1,TC_2}` as the allowed `case` values, no traceback.

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/test_data/mobile_test_data.yaml maestro_mobile/scripts/run_tests.py maestro_mobile/README.md
git commit -m "scaffold maestro_mobile project structure"
```

---

### Task 2: Build and verify `shared_login_signup.yaml`

**Files:**
- Create: `maestro_mobile/flows/shared_login_signup.yaml`

This sub-flow covers side-menu → sign-in/register → phone/country-code/terms entry → continue → username entry. It's invoked via `runFlow` from both pilot flows and expects `COUNTRY_CODE`, `PHONE_NUMBER`, and `USERNAME` to already be set in the calling flow's `env`.

- [ ] **Step 1: Discover the navigation-drawer (hamburger) selector**

The Appium locator (`home_page.navigation_drawer_btn`) is a structural XPath with no resource-id, which Maestro can't use directly. With the emulator running and the app on its home/landing screen:

```bash
maestro studio
```

Tap the hamburger/menu icon in the toolbar. Maestro Studio will show you the real selector (an `id:`, `text:`, or bounding box). Record it — it replaces the `point:` guess in Step 2 below.

- [ ] **Step 2: Write the flow with a best-guess selector**

```yaml
# maestro_mobile/flows/shared_login_signup.yaml
- tapOn:
    point: "5%,8%"   # navigation drawer icon — replace with the selector found in Step 1
- assertVisible:
    text: "About CommCare"
- tapOn:
    id: "org.commcare.dalvik:id/nav_drawer_sign_in_button"
- assertVisible:
    id: "org.commcare.dalvik:id/connect_primary_phone_input"
- tapOn:
    id: "org.commcare.dalvik:id/countryCode"
- inputText: "${COUNTRY_CODE}"
- tapOn:
    id: "org.commcare.dalvik:id/connect_primary_phone_input"
- inputText: "${PHONE_NUMBER}"
- tapOn:
    id: "org.commcare.dalvik:id/connect_consent_check"
- tapOn:
    text: "CONTINUE"
- extendedWaitUntil:
    notVisible:
      id: "org.commcare.dalvik:id/progress_bar"
    timeout: 15000
- tapOn:
    id: "org.commcare.dalvik:id/nameTextValue"
- inputText: "${USERNAME}"
- tapOn:
    text: "CONTINUE"
```

- [ ] **Step 3: Run it standalone against the emulator**

Since a bare sub-flow has no `appId`/`launchApp`, wrap it for a standalone run — create a throwaway `maestro_mobile/flows/_manual_check.yaml` alongside it:

```yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426000"
  USERNAME: "Deb Test 8/12"
---
- launchApp:
    clearState: true
- runFlow: shared_login_signup.yaml
- assertVisible:
    id: "org.commcare.dalvik:id/welcome_back"
```

Run: `maestro test maestro_mobile/flows/_manual_check.yaml`
Expected: PASS, reaching the "Welcome back" backup-code screen.

- [ ] **Step 4: Fix and re-run until it passes**

If Step 3 fails, the most likely culprits, in order: the navigation-drawer selector from Step 1 didn't actually open the drawer (re-check with `maestro studio`), or a screen transition needs an explicit wait (add `extendedWaitUntil` on the next screen's element). Re-run Step 3 after each fix.

- [ ] **Step 5: Delete the throwaway check file and commit**

```bash
rm maestro_mobile/flows/_manual_check.yaml
git add maestro_mobile/flows/shared_login_signup.yaml
git commit -m "add shared Maestro login/signup sub-flow"
```

---

### Task 3: Build and verify `login_signup_success.yaml` (tc_01)

**Files:**
- Create: `maestro_mobile/flows/login_signup_success.yaml`

Covers: shared login/signup, wrong-backup-code negative check, correct backup code, home screen username check, side-menu options, "Go To Connect" button, sign-out.

- [ ] **Step 1: Discover the toolbar overflow (three-dot) menu selector**

Same problem as the nav drawer: `home_page.more_option_btn` is structural XPath. With the app on the home screen after sign-in (you can get there manually for this inspection, or re-run Task 2's manual check and stop before sign-out), run `maestro studio` and tap the three-dot overflow icon (top-right of the toolbar). Record the real selector.

- [ ] **Step 2: Write the flow**

```yaml
# maestro_mobile/flows/login_signup_success.yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426000"
  USERNAME: "Deb Test 8/12"
  BACKUP_CODE: "742600"
---
- launchApp:
    clearState: true
- runFlow: shared_login_signup.yaml
- assertVisible:
    id: "org.commcare.dalvik:id/welcome_back"
    text: "Welcome back ${USERNAME}"
- tapOn:
    id: "org.commcare.dalvik:id/connect_backup_code_input"
- inputText: "123456"
- tapOn:
    text: "CONTINUE"
- assertVisible:
    text: "You have entered the wrong Backup Code"
- tapOn:
    text: "OK"
- tapOn:
    id: "org.commcare.dalvik:id/connect_backup_code_input"
- inputText: "${BACKUP_CODE}"
- tapOn:
    text: "CONTINUE"
- tapOn:
    text: "OK"
- assertVisible:
    id: "org.commcare.dalvik:id/header_user_name"
    text: "${USERNAME}"
- tapOn:
    point: "5%,8%"   # navigation drawer icon — same selector confirmed in Task 2
- assertVisible:
    text: "Opportunities"
- assertVisible:
    text: "CommCare Apps"
- assertVisible:
    text: "Messaging"
- assertVisible:
    text: "Work History"
- assertVisible:
    text: "Notifications"
- assertVisible:
    text: "About CommCare"
- assertVisible:
    text: "GO TO CONNECT MENU"
- tapOn:
    point: "90%,8%"   # toolbar overflow icon — replace with the selector found in Step 1
- tapOn:
    point: "90%,8%"   # tapped twice: the Appium version (home_page.py sign_out) does the same, likely working around the same first-tap-registers-late timing issue
- tapOn:
    text: "Forget PersonalID user"
- tapOn:
    point: "5%,8%"   # navigation drawer icon
- assertVisible:
    id: "org.commcare.dalvik:id/nav_drawer_sign_in_button"
```

- [ ] **Step 3: Run against the emulator**

Run: `maestro test maestro_mobile/flows/login_signup_success.yaml`
Expected: PASS end-to-end — reaches home screen, verifies all 6 side-menu items and the "Go To Connect" button, signs out, and confirms the sign-in/register option is visible again.

- [ ] **Step 4: Fix and re-run until it passes**

Common failure points to check first if it fails: the overflow-menu selector from Step 1, and whether `assertVisible` on the side-menu text items needs a preceding scroll (the Appium version doesn't scroll, so this shouldn't be necessary, but confirm against the real screen).

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/flows/login_signup_success.yaml
git commit -m "add and verify login_signup_success Maestro flow (tc_01)"
```

---

### Task 4: Build and verify `login_account_locked.yaml` (tc_02)

**Files:**
- Create: `maestro_mobile/flows/login_account_locked.yaml`

Covers: shared login/signup, then asserts the "Account Locked" popup instead of reaching the backup-code screen.

- [ ] **Step 1: Write the flow**

```yaml
# maestro_mobile/flows/login_account_locked.yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426005"
  USERNAME: "Deb Test 161202"
---
- launchApp:
    clearState: true
- runFlow: shared_login_signup.yaml
- assertVisible:
    id: "org.commcare.dalvik:id/connect_message_message"
    text: "Your account has been locked. Please contact support"
- tapOn:
    text: "OK"
```

- [ ] **Step 2: Run against the emulator**

Run: `maestro test maestro_mobile/flows/login_account_locked.yaml`
Expected: PASS — reaches the account-locked popup and dismisses it.

- [ ] **Step 3: Fix and re-run until it passes**

If the shared sub-flow instead reaches the "Welcome back" backup-code screen (i.e. TC_2's phone number `7426005` isn't actually configured as a locked account in the current test-data backend), that's a test-data/environment problem, not a flow-authoring one — flag it rather than working around it in the flow.

- [ ] **Step 4: Commit**

```bash
git add maestro_mobile/flows/login_account_locked.yaml
git commit -m "add and verify login_account_locked Maestro flow (tc_02)"
```

---

### Task 5: Update the runner script for the confirmed selectors and do a final data-driven pass

**Files:**
- Modify: `maestro_mobile/README.md`

- [ ] **Step 1: Run both flows through the data-driven runner end to end**

```bash
python maestro_mobile/scripts/run_tests.py TC_1
python maestro_mobile/scripts/run_tests.py TC_2
```

Expected: both exit code 0.

- [ ] **Step 2: Note the confirmed selectors in the README**

Add a short "Confirmed selectors" section to `maestro_mobile/README.md` documenting the real navigation-drawer and overflow-menu selectors found in Tasks 2–3, so the next 7 tests (out of scope for this plan) don't have to rediscover them.

- [ ] **Step 3: Commit**

```bash
git add maestro_mobile/README.md
git commit -m "document confirmed Maestro selectors for future flow authoring"
```

---

## Out of scope for this plan (per the design spec)
- Remaining 7 mobile test files (tc_03, 05–10)
- BrowserStack execution (`config/browserstack.yml`, phase 2)
- GitHub Actions CI wiring, Slack/email notifications
- Allure/JUnit reporting beyond BrowserStack's own dashboard
