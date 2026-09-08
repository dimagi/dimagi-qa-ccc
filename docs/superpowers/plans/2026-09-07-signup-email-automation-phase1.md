# PersonalID Signup + Email Addition — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automate SE_01–SE_12 — the PersonalID registration journey through the new email
addition step — as Maestro flows, and generalise the runner so later phases can reuse it.

**Architecture:** Two new test flows sit on a new `shared_registration.yaml` sub-flow that
drives a *fresh* account from the drawer to the backup code screen. `run_tests.py` stops
hardcoding four env vars and instead passes through whatever the test-data entry declares,
generating a unique phone number and email per run. Email OTP retrieval is isolated behind
one function so the mechanism can be swapped without touching any flow.

**Tech Stack:** Maestro 2.6.1 (YAML flows), Python 3.13 (runner + helpers), pytest for the
helper unit tests, Android emulator `Medium_Phone_API_36.0` over ADB.

**Spec:** `docs/superpowers/specs/2026-09-07-personalid-email-and-manage-profile-automation-design.md`

---

## Critical context for the implementer

Read this before Task 1. Getting any of it wrong produces failures that look like app bugs.

**The build is special.** `app/app-cccStaging-release.apk` is a `cccStaging` + `qaAutomation`
build of 2.65 (`CCC_HOST = connect-staging.dimagi.com`). `BuildConfig.IS_QA_AUTOMATION` is
true, which changes three things versus a normal build:

1. `PersonalIdUnlocker` skips biometric unlock entirely — no fingerprint simulation needed.
2. `PersonalIdPhoneFragment.onConfigurationSuccess` navigates **straight to the Name screen**,
   skipping biometric config *and* the phone OTP screen.
3. `PersonalIdPhotoCaptureFragment` auto-generates a placeholder photo and enables Save.

So the registration path is **phone → name → backup code → email → photo**, not the documented
six-step path.

**Phone numbers must start `+7426`.** ConnectID sets `is_demo_user = phone.startswith("+7426")`
(`users/const.py: TEST_NUMBER_PREFIX`), and demo users get `is_phone_validated = True` at
session creation. That matters because `send_email_otp` and `verify_email_otp` both return
**403 `PHONE_NOT_VALIDATED`** for a `ConfigurationSession` whose phone was never validated —
and this build never shows the phone OTP screen. A non-demo number would sail through signup
and then fail at the email step with an opaque error.

**Registration needs an unused number.** `PersonalIdBackupCodeFragment` sets
`isRecovery = sessionData.accountExists == true`, and recovery routes the email step to
recovery-success instead of photo capture. Reusing a number silently converts a registration
test into a recovery test. Every registration run needs a fresh `+7426` number.

**Emails must be unique too** — a reused address hits "This email is already linked to another
account." Plus-addressing off one mailbox is the intended mechanism.

**Server switch.** The `email_otp_verification` waffle **Switch** must be active on
connect-staging or the email step never appears and every case in this plan fails at SE_01.
It is global per environment, managed in the ConnectID Django admin.

**Maestro gotchas** (already recorded in `maestro_mobile/README.md`, repeated because they bite):
- `text:` selectors are **full matches**. Wrap partials as `.*phrase.*`.
- A Google autofill sheet steals keystrokes on first focus of any text field. The established
  pattern is: `tapOn` field → `tapOn {text: "Cancel", optional: true}` → `tapOn` field again →
  `inputText`.

**Observed on the emulator, 2026-09-07 — these are not theoretical:**

- **Every API-backed step fails intermittently** with an inline
  "No network connection. Please check your internet and try again.", even though the network is
  fully validated. It succeeds on a retry. This affects the phone Continue, the name Continue,
  and every later submit. A one-shot `tapOn` fails more often than it passes, so **each such step
  needs a retry**, e.g. `retry` with `maxRetries`, or an `extendedWaitUntil` on the *next* screen
  wrapped in a repeat. The legacy `PersonalIdPage.start_signup` already loops on this exact error,
  which corroborates it.
- **The Play Services phone-number hint sheet has no "Cancel" text** — only an icon
  (`com.google.android.gms:id/cancel`). The documented `tapOn: {text: "Cancel"}` does **not**
  match this variant. Setting `autofill_service` to null does **not** suppress it either; the app
  requests the hint picker explicitly. It must be dismissed by tapping the icon.
- **`uiautomator dump` needs `MSYS_NO_PATHCONV=1` in Git Bash**, not just the double-slash trick
  the README documents for `adb pull`. Without it the dump silently writes to
  `C:/Program Files/Git/sdcard/...` and you read a stale file while believing it is current.
- **The emulator can die mid-run.** Check `adb devices` before trusting a result; a dead device
  produces `no devices/emulators found` on every step while a stale dump file still parses fine.

**The collision guard — registration vs recovery.** An existing account takes the recovery path,
which on this build is reached through the *same* phone → Name sequence and is easy to mistake for
signup. Recovery is identifiable on the backup code screen by: toolbar title "Confirm Backup Code",
plus `welcome_back`, `welcome_back_layout` and `user_photo` present, and a single code entry rather
than a set/confirm pair. Every registration flow must assert it is **not** on that screen, so a
number collision fails loudly instead of silently exercising recovery.

---

## File structure

| File | Responsibility |
|---|---|
| `maestro_mobile/flows/shared_registration.yaml` | **Create.** Sub-flow: fresh account from drawer → backup code set. Registration only. |
| `maestro_mobile/flows/signup_email_add.yaml` | **Create.** SE_01–SE_05: email step presence, validation, skip. |
| `maestro_mobile/flows/signup_email_verify.yaml` | **Create.** SE_06–SE_09, SE_11, SE_12: verify screen, negatives. |
| `maestro_mobile/flows/signup_email_verified.yaml` | **Create.** SE_10: the OTP happy path. Separate so it can be excluded when OTP retrieval is unavailable. |
| `maestro_mobile/flows/login_signup_success.yaml` | **Modify.** Fix the stale "Forget PersonalID user" string. |
| `maestro_mobile/scripts/run_tests.py` | **Modify.** Generic env passthrough; generated data; OTP injection. |
| `maestro_mobile/scripts/test_data_gen.py` | **Create.** Unique `+7426` phone and plus-addressed email generation. |
| `maestro_mobile/scripts/email_otp.py` | **Create.** Single-function OTP retrieval contract + IMAP implementation. |
| `maestro_mobile/scripts/tests/test_test_data_gen.py` | **Create.** Unit tests for generation. |
| `maestro_mobile/scripts/tests/test_email_otp.py` | **Create.** Unit tests for OTP parsing. |
| `maestro_mobile/pytest.ini` | **Create.** Isolated pytest config so helper tests don't load the Appium root conftest. |
| `maestro_mobile/test_data/mobile_test_data.yaml` | **Modify.** Entries for the new cases. |
| `maestro_mobile/scripts/run_on_browserstack.py` | **Modify.** Add new flows to `execute`. |
| `maestro_mobile/README.md` | **Modify.** Document the qaAutomation build and the `+7426` rule. |

---

## Task 1: Establish ground truth on the qaAutomation build

The registration path above is derived from source, not observed. Before writing twelve cases
against it, confirm the real screen sequence. Do not skip this — every later task depends on it.

**Files:**
- Modify: `maestro_mobile/flows/login_signup_success.yaml`

- [ ] **Step 1: Start the emulator**

```bash
emulator -avd Medium_Phone_API_36.0 -gpu swiftshader_indirect &
```

Wait for it, then confirm:

```bash
adb wait-for-device && adb devices
```

Expected: one device listed as `device` (not `offline`).

- [ ] **Step 2: Install the staging build**

```bash
adb install -r -g app/app-cccStaging-release.apk
```

Expected: `Success`. The `-g` grants runtime permissions up front, avoiding permission dialogs.

- [ ] **Step 3: Confirm the installed build is the right one**

```bash
adb shell dumpsys package org.commcare.dalvik | grep versionName
```

Expected: `versionName=2.65`. If it says 2.63.4, the wrong APK is installed — stop and fix.

- [ ] **Step 4: Drive a fresh registration by hand and record the screens**

Launch the app, open the drawer, tap sign in, and register with country code `+7426` and a
phone number you have not used before (e.g. `7426901`). At each screen run:

```bash
adb shell uiautomator dump /sdcard/window_dump.xml && adb pull //sdcard/window_dump.xml
```

(Note the double leading slash — Git Bash mangles a single one.)

Record, in order: every screen reached, its resource IDs, and its visible text. You are
confirming three things:
- the Name screen follows the phone screen directly (no biometric, no phone OTP)
- the Email screen follows the backup code screen
- the exact resource IDs on the Email screen match the spec's §7 appendix

- [ ] **Step 5: Write down any deviation**

If the observed sequence differs from `phone → name → backup code → email → photo`, **stop and
report it** before continuing. Later tasks assume this path; a mismatch means the spec's §2.2
needs revising first.

- [ ] **Step 6: Fix the stale string in the existing flow**

In `maestro_mobile/flows/login_signup_success.yaml`, replace:

```yaml
- tapOn:
    text: "Forget PersonalID user"
```

with:

```yaml
- tapOn:
    text: "Forget PersonalID Account"
```

The string `personalid_forget_user` no longer exists in 2.65; the Login 3-dot menu now reuses
`personalid_profile_forget_account`.

- [ ] **Step 7: Verify the existing suite still passes**

```bash
python maestro_mobile/scripts/run_tests.py TC_1
```

Expected: PASS. If it fails on a step other than the Forget menu, capture the failure
screenshot from Maestro's output directory and report it before continuing.

- [ ] **Step 8: Commit**

```bash
git add maestro_mobile/flows/login_signup_success.yaml
git commit -m "fix: update Forget PersonalID menu string for 2.65"
```

---

## Task 2: Extract the registration sub-flow

**Files:**
- Create: `maestro_mobile/flows/shared_registration.yaml`

- [ ] **Step 1: Write the sub-flow**

Create `maestro_mobile/flows/shared_registration.yaml`. Adjust the step sequence to match what
Task 1 actually observed if it differed.

```yaml
appId: org.commcare.dalvik
---
# Registration for a BRAND NEW account, up to and including setting the backup code.
# Requires a +7426 phone number with no existing account - see the plan's context notes.
# On the qaAutomation build there is no biometric step and no phone OTP screen.
- launchApp:
    clearState: true
- tapOn:
    text: "Open navigation drawer"
- assertVisible:
    text: "About CommCare"
- tapOn:
    id: "org.commcare.dalvik:id/nav_drawer_sign_in_button"
- assertVisible:
    id: "org.commcare.dalvik:id/connect_primary_phone_input"
- tapOn:
    id: "org.commcare.dalvik:id/countryCode"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/countryCode"
- eraseText
- inputText: "${COUNTRY_CODE}"
- tapOn:
    id: "org.commcare.dalvik:id/connect_primary_phone_input"
- tapOn:
    text: "Cancel"
    optional: true
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
    timeout: 20000
# qaAutomation build lands directly on the Name screen.
- assertVisible:
    id: "org.commcare.dalvik:id/nameTextValue"
- tapOn:
    id: "org.commcare.dalvik:id/nameTextValue"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/nameTextValue"
- inputText: "${USERNAME}"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    text: "CONTINUE"
- extendedWaitUntil:
    notVisible:
      id: "org.commcare.dalvik:id/progress_bar"
    timeout: 20000
# Backup code screen: set the code twice.
- assertVisible:
    id: "org.commcare.dalvik:id/connect_backup_code_input"
- tapOn:
    id: "org.commcare.dalvik:id/connect_backup_code_input"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/connect_backup_code_input"
- inputText: "${BACKUP_CODE}"
- tapOn:
    text: "CONTINUE"
- extendedWaitUntil:
    notVisible:
      id: "org.commcare.dalvik:id/progress_bar"
    timeout: 20000
```

- [ ] **Step 2: Verify the sub-flow lands on the Email screen**

Create a scratch flow `maestro_mobile/flows/scratch_reg_check.yaml`:

```yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426911"
  USERNAME: "QA Reg Check"
  BACKUP_CODE: "742691"
---
- runFlow: shared_registration.yaml
- assertVisible:
    text: "Add your email (optional)"
```

Run it:

```bash
maestro test maestro_mobile/flows/scratch_reg_check.yaml
```

Expected: PASS. A failure here means either the backup code screen has a second
confirm field this flow doesn't fill, or the `email_otp_verification` switch is off. Check the
switch first — that is the more likely cause and it fails silently.

- [ ] **Step 3: Delete the scratch flow**

```bash
rm maestro_mobile/flows/scratch_reg_check.yaml
```

- [ ] **Step 4: Commit**

```bash
git add maestro_mobile/flows/shared_registration.yaml
git commit -m "test: add shared registration sub-flow for fresh PersonalID accounts"
```

---

## Task 3: SE_01–SE_05 — the email step and skipping it

**Files:**
- Create: `maestro_mobile/flows/signup_email_add.yaml`

- [ ] **Step 1: Write the flow**

```yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426920"
  USERNAME: "QA Email Add"
  BACKUP_CODE: "742692"
  INVALID_EMAIL: "not-an-email"
  VALID_EMAIL: "qa.connect@example.com"
---
- runFlow: shared_registration.yaml

# SE_01: the Email step is shown with its title and rationale.
- assertVisible:
    text: "Add your email (optional)"
- assertVisible:
    text: ".*Your email helps you recover your account.*"
- assertVisible:
    id: "org.commcare.dalvik:id/personalid_email_skip_button"

# SE_02: Continue is disabled until a valid address is entered.
- assertVisible:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
    enabled: false

# SE_03: an invalid address surfaces the format error.
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- inputText: "${INVALID_EMAIL}"
- tapOn:
    text: "Cancel"
    optional: true
- assertVisible:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
    enabled: false

# SE_02 (positive half): a valid address enables Continue.
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- eraseText
- inputText: "${VALID_EMAIL}"
- assertVisible:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
    enabled: true

# SE_04: Skip raises the confirm dialog; "No" returns to the Email step.
- tapOn:
    id: "org.commcare.dalvik:id/personalid_email_skip_button"
- assertVisible:
    text: "Skip email?"
- assertVisible:
    text: "Are you sure you want to skip?"
- tapOn:
    text: "No"
- assertVisible:
    text: "Add your email (optional)"

# SE_05: confirming the skip continues to photo capture.
- tapOn:
    id: "org.commcare.dalvik:id/personalid_email_skip_button"
- assertVisible:
    text: "Skip email?"
- tapOn:
    text: "Yes"
- extendedWaitUntil:
    visible:
      text: ".*Take Photo.*"
    timeout: 20000
```

Note on SE_03: the app validates format as you type and gates the Continue button, so the
assertion is on the button state. If Task 1's dump showed
`org.commcare.dalvik:id/personalid_email_error` populated with
"Please enter a valid email address." on blur, add an `assertVisible` for that text too.

- [ ] **Step 2: Run it**

```bash
maestro test maestro_mobile/flows/signup_email_add.yaml
```

Expected: PASS.

- [ ] **Step 3: If it fails on the enabled/disabled assertions**

Maestro's `enabled:` matcher relies on the view reporting its enabled state. If the Continue
button is implemented as always-enabled-but-inert, the assertion fails. Confirm with:

```bash
adb shell uiautomator dump /sdcard/window_dump.xml && adb pull //sdcard/window_dump.xml
grep -o 'resource-id="[^"]*personalid_email_continue_button"[^>]*' window_dump.xml
```

Check the `enabled` attribute. If it is always `true`, replace those assertions with a
behavioural check: tap Continue with an invalid address and assert the Email screen is still
visible.

- [ ] **Step 4: Commit**

```bash
git add maestro_mobile/flows/signup_email_add.yaml
git commit -m "test: add SE_01-SE_05 signup email step coverage"
```

---

## Task 4: SE_06–SE_09, SE_11, SE_12 — the verify screen and its negatives

**Files:**
- Create: `maestro_mobile/flows/signup_email_verify.yaml`

- [ ] **Step 1: Write the flow**

```yaml
appId: org.commcare.dalvik
env:
  COUNTRY_CODE: "+7426"
  PHONE_NUMBER: "7426930"
  USERNAME: "QA Email Verify"
  BACKUP_CODE: "742693"
  VALID_EMAIL: "qa.connect+verify@example.com"
  WRONG_OTP: "123456"
---
- runFlow: shared_registration.yaml

# SE_06: a valid address opens the Verify Email screen showing that address.
- assertVisible:
    text: "Add your email (optional)"
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- inputText: "${VALID_EMAIL}"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
- extendedWaitUntil:
    visible:
      id: "org.commcare.dalvik:id/otp_code_view"
    timeout: 20000
- assertVisible:
    text: ".*${VALID_EMAIL}.*"

# SE_07: resend is behind a countdown, not immediately available.
- assertVisible:
    id: "org.commcare.dalvik:id/personalid_resend_countdown_text"
- assertNotVisible:
    id: "org.commcare.dalvik:id/personalid_email_resend_button"

# SE_08: a wrong code is rejected.
- tapOn:
    id: "org.commcare.dalvik:id/otp_code_view"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/otp_code_view"
- inputText: "${WRONG_OTP}"
- extendedWaitUntil:
    visible:
      text: ".*wrong 6-digit passcode.*"
    timeout: 20000
```

The code field auto-submits on the sixth digit (`setCodeCompleteListener`), so there is no
Verify tap after `inputText`.

- [ ] **Step 2: Run it and observe the failure ceiling**

```bash
maestro test maestro_mobile/flows/signup_email_verify.yaml
```

Expected: PASS through SE_08.

- [ ] **Step 3: Determine the attempt limits empirically**

SE_09 ("Verification unsuccessful" → "Proceed without email") and SE_12 ("Maximum verification
attempts reached") both fire after some number of failures, and the thresholds are enforced
server-side. Do not guess them. Append wrong-code attempts one at a time, re-running after
each, and record which attempt triggers which dialog:

```yaml
# repeat block - add one at a time until the dialog appears
- tapOn:
    id: "org.commcare.dalvik:id/otp_code_view"
- eraseText
- inputText: "${WRONG_OTP}"
- extendedWaitUntil:
    visible:
      text: ".*wrong 6-digit passcode.*"
    timeout: 20000
```

- [ ] **Step 4: Append SE_09 and SE_12 using the observed counts**

Once known, append — using the real attempt count rather than the placeholder comment:

```yaml
# SE_09: after the observed number of failures, the failure dialog appears.
- assertVisible:
    text: "Verification unsuccessful"
- assertVisible:
    text: "Try again"
- assertVisible:
    text: "Proceed without email"
- tapOn:
    text: "Proceed without email"
- extendedWaitUntil:
    visible:
      text: ".*Take Photo.*"
    timeout: 20000
```

If SE_12's "Maximum verification attempts reached. Please try again later." proves to be
reachable only after a cooldown or a server-side lockout that persists across accounts, move
SE_12 into its own flow so it cannot poison the rest of the run, and note the constraint in
the flow's header comment.

- [ ] **Step 5: Add SE_11 as its own flow-tail**

SE_11 needs an address already bound to another account. Add to the end of
`signup_email_add.yaml` instead — it already reaches the Email screen with an account that is
about to be discarded. Append there:

```yaml
# SE_11: an address already on another account is rejected.
# TAKEN_EMAIL must be an address that completed verification on a different account.
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- eraseText
- inputText: "${TAKEN_EMAIL}"
- tapOn:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
- extendedWaitUntil:
    visible:
      text: ".*already linked to another account.*"
    timeout: 20000
```

and add `TAKEN_EMAIL` to that flow's `env` block.

- [ ] **Step 6: Commit**

```bash
git add maestro_mobile/flows/signup_email_verify.yaml maestro_mobile/flows/signup_email_add.yaml
git commit -m "test: add SE_06-SE_09, SE_11, SE_12 email verification coverage"
```

---

## Task 5: Unique test data generation

**Files:**
- Create: `maestro_mobile/scripts/test_data_gen.py`
- Create: `maestro_mobile/scripts/tests/test_test_data_gen.py`
- Create: `maestro_mobile/pytest.ini`

- [ ] **Step 1: Create an isolated pytest config**

The repo root `conftest.py` builds Appium drivers, so helper tests must not inherit it.
Create `maestro_mobile/pytest.ini`:

```ini
[pytest]
addopts = -v
testpaths = scripts/tests
```

- [ ] **Step 2: Write the failing tests**

Create `maestro_mobile/scripts/tests/test_test_data_gen.py`:

```python
import re

from scripts.test_data_gen import fresh_email, fresh_phone_number


def test_fresh_phone_number_is_seven_digits():
    number = fresh_phone_number()
    assert re.fullmatch(r"\d{7}", number)


def test_fresh_phone_number_uses_the_automation_block():
    assert fresh_phone_number().startswith("129")


def test_fresh_phone_number_is_unique_across_calls():
    numbers = {fresh_phone_number() for _ in range(5)}
    assert len(numbers) == 5


def test_fresh_phone_number_avoids_reserved_numbers():
    reserved = {"7426000", "7426005"}
    numbers = {fresh_phone_number() for _ in range(20)}
    assert not (numbers & reserved)


def test_fresh_email_uses_plus_addressing():
    address = fresh_email("qa.connect@dimagi.com")
    local, domain = address.split("@")
    assert domain == "dimagi.com"
    assert local.startswith("qa.connect+")


def test_fresh_email_is_unique_across_calls():
    addresses = {fresh_email("qa.connect@dimagi.com") for _ in range(5)}
    assert len(addresses) == 5


def test_fresh_email_rejects_address_without_at_sign():
    try:
        fresh_email("not-an-address")
    except ValueError:
        return
    raise AssertionError("expected ValueError for an address with no @")
```

- [ ] **Step 3: Run the tests to verify they fail**

```bash
python -m pytest maestro_mobile/scripts/tests/test_test_data_gen.py -c maestro_mobile/pytest.ini --rootdir maestro_mobile
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.test_data_gen'`.

- [ ] **Step 4: Write the implementation**

Create `maestro_mobile/scripts/test_data_gen.py`:

```python
"""Generation of unique, demo-safe test data for PersonalID registration flows.

Numbering scheme (decided 2026-09-07): subscriber numbers are the fixed
automation block AUTOMATION_BLOCK followed by four clock-derived digits, dialled
under country code +7426.

Two separate reasons for the shape:

* The +7426 country code makes the user a demo user on ConnectID, which bypasses
  SMS and marks the session phone-validated. The qaAutomation build never shows
  the phone OTP screen, so without this the email OTP endpoints return 403
  PHONE_NOT_VALIDATED.
* The 129 block makes every account this suite creates identifiable at a glance,
  so they can be audited or bulk-deactivated later. Accounts are not recycled
  today; ConnectID's phone-number uniqueness is conditional on is_active=True, so
  a future cleanup job can free these numbers via
  recover/initiate_deactivation + recover/confirm_deactivation without any change
  to this scheme.

Registration additionally requires a number with no existing account: an existing
account sends PersonalIdBackupCodeFragment down the recovery path instead. The
flows guard against that visually - see the collision guard note in the plan.
"""

import itertools
import time

AUTOMATION_BLOCK = "129"

# Numbers already committed to mobile_test_data.yaml for the recovery cases.
RESERVED_PHONE_NUMBERS = frozenset({"7426000", "7426005"})

_counter = itertools.count()


def fresh_phone_number():
    """A 7-digit subscriber number in the automation block, unique per call.

    Combined with country code +7426 this is always a demo user.
    """
    while True:
        # Four digits from the clock plus an in-process counter, so numbers
        # differ both within a run and between runs.
        tail = f"{(int(time.time()) + next(_counter)) % 10000:04d}"
        number = f"{AUTOMATION_BLOCK}{tail}"
        if number not in RESERVED_PHONE_NUMBERS:
            return number


def fresh_email(base_address):
    """A plus-addressed variant of base_address, unique per call.

    'qa.connect@dimagi.com' becomes 'qa.connect+1757260000@dimagi.com', which
    routes to the same mailbox but is a distinct address to PersonalID.
    """
    if "@" not in base_address:
        raise ValueError(f"not a valid email address: {base_address!r}")
    local, _, domain = base_address.partition("@")
    local = local.partition("+")[0]
    return f"{local}+{_unique_suffix()}@{domain}"
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
python -m pytest maestro_mobile/scripts/tests/test_test_data_gen.py -c maestro_mobile/pytest.ini --rootdir maestro_mobile
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add maestro_mobile/scripts/test_data_gen.py maestro_mobile/scripts/tests/test_test_data_gen.py maestro_mobile/pytest.ini
git commit -m "feat: generate unique demo-safe phone numbers and emails for registration flows"
```

---

## Task 6: Generalise the runner

`run_tests.py` currently hardcodes four `-e` flags, so a new flow cannot introduce a new
variable. Make it pass through whatever the test-data entry declares, and inject generated
values where the entry asks for them.

**Files:**
- Modify: `maestro_mobile/scripts/run_tests.py`
- Modify: `maestro_mobile/test_data/mobile_test_data.yaml`

- [ ] **Step 1: Add the new test-data entries**

Append to `maestro_mobile/test_data/mobile_test_data.yaml`:

```yaml
SE_ADD:
  flow: signup_email_add.yaml
  country_code: "+7426"
  phone_number: "__GENERATE__"
  username: "QA Email Add"
  backup_code: "742692"
  invalid_email: "not-an-email"
  valid_email: "__GENERATE_EMAIL__"
  taken_email: "REPLACE_WITH_A_VERIFIED_ADDRESS_ON_ANOTHER_ACCOUNT"

SE_VERIFY:
  flow: signup_email_verify.yaml
  country_code: "+7426"
  phone_number: "__GENERATE__"
  username: "QA Email Verify"
  backup_code: "742693"
  valid_email: "__GENERATE_EMAIL__"
  wrong_otp: "123456"
```

`taken_email` is the one value that cannot be generated — it must be an address that has
actually completed verification on a different account. Fill it in once such an account exists.

- [ ] **Step 2: Rewrite the runner**

Replace the body of `maestro_mobile/scripts/run_tests.py` with:

```python
import argparse
import shutil
import subprocess
import sys
from configparser import ConfigParser
from pathlib import Path

import yaml

from test_data_gen import fresh_email, fresh_phone_number

FLOWS_DIR = Path(__file__).parent.parent / "flows"
TEST_DATA_FILE = Path(__file__).parent.parent / "test_data" / "mobile_test_data.yaml"
SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.cfg"

GENERATE_PHONE = "__GENERATE__"
GENERATE_EMAIL = "__GENERATE_EMAIL__"

# Legacy entries that predate the "flow" key.
LEGACY_FLOW_BY_CASE = {
    "TC_1": "login_signup_success.yaml",
    "TC_2": "login_account_locked.yaml",
}


def load_test_data(case_key):
    with open(TEST_DATA_FILE) as f:
        data = yaml.safe_load(f)
    if case_key not in data:
        sys.exit(f"Unknown case '{case_key}'. Known cases: {', '.join(sorted(data))}")
    return data[case_key]


def base_email_address():
    """The mailbox that plus-addressed test emails route to."""
    config = ConfigParser()
    config.read(SETTINGS_FILE)
    if not config.has_option("email", "address"):
        sys.exit(
            "No [email] address in settings.cfg. Add:\n\n"
            "[email]\naddress = your.qa.mailbox@example.com\n"
        )
    return config.get("email", "address")


def resolve_values(data):
    """Turn a test-data entry into the env vars a flow receives.

    'flow' selects the file and is not passed through. Every other key becomes
    an uppercase env var, with the generation placeholders expanded.
    """
    resolved = {}
    for key, value in data.items():
        if key == "flow":
            continue
        if value == GENERATE_PHONE:
            value = fresh_phone_number()
        elif value == GENERATE_EMAIL:
            value = fresh_email(base_email_address())
        resolved[key.upper()] = str(value)
    return resolved


def run_flow(case_key):
    data = load_test_data(case_key)
    flow_name = data.get("flow") or LEGACY_FLOW_BY_CASE.get(case_key)
    if not flow_name:
        sys.exit(f"Case '{case_key}' has no 'flow' key and is not a known legacy case.")

    flow_file = FLOWS_DIR / flow_name
    if not flow_file.exists():
        sys.exit(f"Flow file not found: {flow_file}")

    maestro_path = shutil.which("maestro")
    if not maestro_path:
        sys.exit("maestro CLI not found on PATH. See maestro_mobile/README.md for install instructions.")

    values = resolve_values(data)
    cmd = [maestro_path, "test", str(flow_file)]
    for name, value in values.items():
        cmd += ["-e", f"{name}={value}"]

    print(f"Running {flow_name} with: " + ", ".join(f"{k}={v}" for k, v in values.items()))
    return subprocess.run(cmd).returncode


def main():
    parser = argparse.ArgumentParser(description="Run Connect Maestro mobile flows locally")
    parser.add_argument("case", help="Test case key from mobile_test_data.yaml, e.g. TC_1 or SE_ADD")
    args = parser.parse_args()
    sys.exit(run_flow(args.case))


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Verify the legacy cases still work**

```bash
python maestro_mobile/scripts/run_tests.py TC_1
```

Expected: PASS, with a line reading
`Running login_signup_success.yaml with: COUNTRY_CODE=+7426, PHONE_NUMBER=7426000, ...`

- [ ] **Step 4: Verify a generated case works**

```bash
python maestro_mobile/scripts/run_tests.py SE_ADD
```

Expected: PASS, with `PHONE_NUMBER` and `VALID_EMAIL` differing on every run.

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/scripts/run_tests.py maestro_mobile/test_data/mobile_test_data.yaml
git commit -m "feat: generic env passthrough and generated data in the Maestro runner"
```

---

## Task 7: Email OTP retrieval

Isolated behind one function so the mechanism can be replaced without touching a flow. The
IMAP implementation below is the default; if the team already has a retrieval mechanism,
replace the body of `fetch_otp` and leave everything else alone.

**Files:**
- Create: `maestro_mobile/scripts/email_otp.py`
- Create: `maestro_mobile/scripts/tests/test_email_otp.py`

- [ ] **Step 1: Write the failing tests**

Create `maestro_mobile/scripts/tests/test_email_otp.py`:

```python
from scripts.email_otp import extract_otp


def test_extract_otp_finds_a_six_digit_code():
    assert extract_otp("Your PersonalID code is 481920. It expires shortly.") == "481920"


def test_extract_otp_ignores_longer_digit_runs():
    assert extract_otp("Ref 1234567890 code 481920 end") == "481920"


def test_extract_otp_returns_none_when_absent():
    assert extract_otp("No code in this message at all") is None


def test_extract_otp_returns_none_for_empty_body():
    assert extract_otp("") is None
```

- [ ] **Step 2: Run the tests to verify they fail**

```bash
python -m pytest maestro_mobile/scripts/tests/test_email_otp.py -c maestro_mobile/pytest.ini --rootdir maestro_mobile
```

Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.email_otp'`.

- [ ] **Step 3: Write the implementation**

Create `maestro_mobile/scripts/email_otp.py`:

```python
"""Retrieval of the 6-digit PersonalID email verification code.

The whole mechanism is deliberately confined to fetch_otp() so it can be swapped
without touching any Maestro flow. Credentials are read from settings.cfg and are
never passed on a command line.
"""

import email
import imaplib
import re
import time
from configparser import ConfigParser
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.cfg"

# Six digits not adjacent to other digits, so reference numbers are not mistaken for codes.
OTP_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")


def extract_otp(body):
    """The 6-digit code in an email body, or None if there isn't one."""
    if not body:
        return None
    match = OTP_PATTERN.search(body)
    return match.group(1) if match else None


def _imap_settings():
    config = ConfigParser()
    config.read(SETTINGS_FILE)
    if not config.has_section("email"):
        raise RuntimeError(
            "No [email] section in settings.cfg. Add:\n\n"
            "[email]\n"
            "address = your.qa.mailbox@example.com\n"
            "imap_host = imap.gmail.com\n"
            "imap_user = your.qa.mailbox@example.com\n"
            "imap_password = your-app-password\n"
        )
    section = config["email"]
    return (
        section.get("imap_host", "imap.gmail.com"),
        section["imap_user"],
        section["imap_password"],
    )


def _latest_body_for(recipient, host, user, password):
    connection = imaplib.IMAP4_SSL(host)
    try:
        connection.login(user, password)
        connection.select("INBOX")
        status, data = connection.search(None, "TO", f'"{recipient}"')
        if status != "OK" or not data[0]:
            return None
        latest_id = data[0].split()[-1]
        status, message_data = connection.fetch(latest_id, "(RFC822)")
        if status != "OK":
            return None
        message = email.message_from_bytes(message_data[0][1])
        if message.is_multipart():
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    return part.get_payload(decode=True).decode(errors="replace")
            return None
        return message.get_payload(decode=True).decode(errors="replace")
    finally:
        try:
            connection.logout()
        except imaplib.IMAP4.error:
            pass


def fetch_otp(recipient, timeout=120, poll_interval=5):
    """Poll the QA mailbox until a code addressed to recipient arrives.

    Raises TimeoutError if none arrives within timeout seconds.
    """
    host, user, password = _imap_settings()
    deadline = time.time() + timeout
    while time.time() < deadline:
        body = _latest_body_for(recipient, host, user, password)
        code = extract_otp(body)
        if code:
            return code
        time.sleep(poll_interval)
    raise TimeoutError(f"No email OTP for {recipient} within {timeout}s")
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python -m pytest maestro_mobile/scripts/tests/test_email_otp.py -c maestro_mobile/pytest.ini --rootdir maestro_mobile
```

Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/scripts/email_otp.py maestro_mobile/scripts/tests/test_email_otp.py
git commit -m "feat: email OTP retrieval behind a single swappable function"
```

---

## Task 8: SE_10 — the OTP happy path

Maestro cannot call back into Python mid-flow, and the code only exists once the app has
submitted the address. So SE_10 is **two flows** with the fetch between them: the request flow
registers and submits the address, the runner then polls the mailbox, and the verify flow
enters the code into the app the request flow left running.

The verify flow must **not** use `launchApp`/`clearState` — it continues the same session.

**Files:**
- Create: `maestro_mobile/flows/signup_email_request.yaml`
- Create: `maestro_mobile/flows/signup_email_verified.yaml`
- Modify: `maestro_mobile/scripts/run_tests.py`
- Modify: `maestro_mobile/test_data/mobile_test_data.yaml`

- [ ] **Step 1a: Write the request flow**

Create `maestro_mobile/flows/signup_email_request.yaml`:

```yaml
appId: org.commcare.dalvik
---
# SE_10, part 1: register a fresh account and submit the email address.
# Leaves the app sitting on the Verify Email screen for signup_email_verified.yaml.
# Run via run_tests.py SE_VERIFIED - never standalone.
- runFlow: shared_registration.yaml
- assertVisible:
    text: "Add your email (optional)"
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/email_text_value"
- inputText: "${VALID_EMAIL}"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/personalid_email_continue_button"
- extendedWaitUntil:
    visible:
      id: "org.commcare.dalvik:id/otp_code_view"
    timeout: 20000
```

- [ ] **Step 1b: Write the verify flow**

Create `maestro_mobile/flows/signup_email_verified.yaml`:

```yaml
appId: org.commcare.dalvik
---
# SE_10, part 2: enter the code fetched by run_tests.py.
# Continues the session left by signup_email_request.yaml - no launchApp, no clearState.
- assertVisible:
    id: "org.commcare.dalvik:id/otp_code_view"
- tapOn:
    id: "org.commcare.dalvik:id/otp_code_view"
- tapOn:
    text: "Cancel"
    optional: true
- tapOn:
    id: "org.commcare.dalvik:id/otp_code_view"
- inputText: "${EMAIL_OTP}"
- extendedWaitUntil:
    visible:
      text: "Email Added"
    timeout: 30000
- assertVisible:
    text: "Your email has been added successfully."
- tapOn:
    text: "OK"
- extendedWaitUntil:
    visible:
      text: ".*Take Photo.*"
    timeout: 20000
```

- [ ] **Step 2: Add the test-data entry**

Append to `maestro_mobile/test_data/mobile_test_data.yaml`:

```yaml
SE_VERIFIED:
  flow: signup_email_verified.yaml
  needs_email_otp: true
  country_code: "+7426"
  phone_number: "__GENERATE__"
  username: "QA Email Verified"
  backup_code: "742694"
  valid_email: "__GENERATE_EMAIL__"
```

- [ ] **Step 3: Teach the runner to sequence the two flows**

In `maestro_mobile/scripts/run_tests.py`, add the import beneath the existing one:

```python
from email_otp import fetch_otp
```

Add the request-flow constant beneath `GENERATE_EMAIL`:

```python
EMAIL_REQUEST_FLOW = "signup_email_request.yaml"
```

In `resolve_values`, change the loop's guard from:

```python
        if key == "flow":
            continue
```

to:

```python
        if key in ("flow", "needs_email_otp"):
            continue
```

Extract the command construction out of `run_flow` into a helper, placed above it:

```python
def _run_maestro(maestro_path, flow_file, values):
    cmd = [maestro_path, "test", str(flow_file)]
    for name, value in values.items():
        cmd += ["-e", f"{name}={value}"]
    print(f"Running {flow_file.name} with: " + ", ".join(f"{k}={v}" for k, v in values.items()))
    return subprocess.run(cmd).returncode
```

Then replace the tail of `run_flow` — everything from `values = resolve_values(data)` to the
end of the function — with:

```python
    values = resolve_values(data)

    if data.get("needs_email_otp"):
        # The code does not exist until the app submits the address, so run the
        # request flow first, fetch, then continue the same session.
        returncode = _run_maestro(maestro_path, FLOWS_DIR / EMAIL_REQUEST_FLOW, values)
        if returncode != 0:
            return returncode
        recipient = values["VALID_EMAIL"]
        print(f"Waiting for the email OTP sent to {recipient}...")
        values["EMAIL_OTP"] = fetch_otp(recipient)
        print("Got the code.")

    return _run_maestro(maestro_path, flow_file, values)
```

- [ ] **Step 4: Run it**

```bash
python maestro_mobile/scripts/run_tests.py SE_VERIFIED
```

Expected: the request flow passes, the runner prints the wait message, then the verify flow
passes and the app reaches photo capture.

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/flows/signup_email_request.yaml maestro_mobile/flows/signup_email_verified.yaml maestro_mobile/scripts/run_tests.py maestro_mobile/test_data/mobile_test_data.yaml
git commit -m "test: add SE_10 email verification happy path with OTP injection"
```

---

## Task 9: Register the flows and document the build

**Files:**
- Modify: `maestro_mobile/scripts/run_on_browserstack.py`
- Modify: `maestro_mobile/README.md`

- [ ] **Step 1: Add the new flows to the BrowserStack execute list**

In `maestro_mobile/scripts/run_on_browserstack.py`, find the `execute` list and add
`signup_email_add.yaml` and `signup_email_verify.yaml`.

Do **not** add `shared_registration.yaml`, `signup_email_request.yaml`, or
`signup_email_verified.yaml`. The first is a sub-flow and would fail standalone; the latter two
depend on the local runner to inject `EMAIL_OTP` and to sequence them, which BrowserStack
cannot do.

Paths in `execute` are relative to the zip's root folder contents, so they carry no `flows/`
prefix — the README already records this.

- [ ] **Step 2: Document the build and the phone-number rule**

Add to `maestro_mobile/README.md` under a new "## The qaAutomation build" heading:

```markdown
## The qaAutomation build

`app/app-cccStaging-release.apk` is a `cccStaging` + `qaAutomation` build
(`CCC_HOST = connect-staging.dimagi.com`, `BuildConfig.IS_QA_AUTOMATION = true`). Three
behaviours differ from a normal build:

- biometric unlock is skipped (`PersonalIdUnlocker`)
- the phone OTP screen is skipped — the phone screen goes straight to Name
- photo capture auto-generates a placeholder image

So registration runs **phone -> name -> backup code -> email -> photo**.

### Phone numbers must start +7426

ConnectID treats `+7426` numbers as demo users and marks their sessions phone-validated on
creation. Since this build never shows the phone OTP screen, a non-demo number leaves the
session unvalidated and the email OTP endpoints return 403 PHONE_NOT_VALIDATED - which
surfaces in the app as a generic failure. Always use +7426.

### Registration needs an unused number

An existing account routes the backup code screen down the recovery path, where the email
step leads to recovery-success rather than photo capture. `run_tests.py` generates a fresh
number for any test-data entry whose `phone_number` is `__GENERATE__`.

### The email_otp_verification switch

The email screens only appear when the `email_otp_verification` waffle Switch is active on
connect-staging. When it is off, the app silently behaves like 2.63 - signup goes straight
from backup code to photo. If the email step is missing, check this before debugging flows.
```

- [ ] **Step 3: Verify the full local suite**

```bash
python maestro_mobile/scripts/run_tests.py TC_1
python maestro_mobile/scripts/run_tests.py TC_2
python maestro_mobile/scripts/run_tests.py SE_ADD
python maestro_mobile/scripts/run_tests.py SE_VERIFY
```

Expected: all four PASS. Capture the Maestro failure screenshot for any that don't.

- [ ] **Step 4: Run the helper unit tests**

```bash
python -m pytest maestro_mobile/scripts/tests -c maestro_mobile/pytest.ini --rootdir maestro_mobile
```

Expected: 10 passed.

- [ ] **Step 5: Commit**

```bash
git add maestro_mobile/scripts/run_on_browserstack.py maestro_mobile/README.md
git commit -m "docs: register signup email flows and document the qaAutomation build"
```

---

## Phase 1 done when

- SE_01–SE_12 are covered by flows that pass locally against the 2.65 staging build
- `TC_1` and `TC_2` still pass (no regression from the runner rewrite)
- Helper unit tests pass
- `README.md` documents the build, the `+7426` rule, and the switch

## Known follow-ups (not phase 1)

- `taken_email` in `SE_ADD` needs a real verified address before SE_11 can pass.
- SE_12's attempt threshold is server-enforced and may need its own isolated flow.
- Phase 2 (Manage Profile) reuses `shared_registration.yaml` but needs a *signed-in* sub-flow;
  extract `shared_signin.yaml` then rather than pre-emptively now.
