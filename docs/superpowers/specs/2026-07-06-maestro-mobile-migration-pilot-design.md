# Maestro Mobile Migration — Pilot Design

## Context

The existing mobile test suite (`tests/mobile_tests/`) is built on Appium + Pytest, using a Page Object Model with YAML-defined locators (`locators/mobile_locators.yaml`) and a `BasePage` class. Tests run against the CommCare Android app (`org.commcare.dalvik`), primarily on BrowserStack, with a local-emulator fallback.

We're moving mobile automation to **Maestro**, using YAML flow files with embedded JS (`runScript`/`evalScript`) for data-driven/conditional logic where needed. This is a from-scratch project setup — no Maestro project exists yet.

This spec covers a **pilot**: proving out the framework pattern with 2 representative tests before porting the remaining 7. The existing Appium tests are used as the source of truth for business logic, locators, and edge-case handling, but reimplemented idiomatically as declarative Maestro flows rather than translated line-by-line.

## Pilot scope

Port 2 tests, both sharing the same login/signup flow up to "enter username," then diverging:
- `test_tc_01` → `login_signup_success.yaml` — full signup: mobile number entry, fingerprint handling, demo-user popup, username entry, backup code verification (including a wrong-code negative check), side-menu options, sign out. (Foundational flow.)
- `test_tc_02` → `login_account_locked.yaml` — same signup flow but ending in an "Account Locked" error popup. (Validates data-driven values and a negative-path assertion using the *same* shared steps.)

## Project structure

New folder inside the existing `dimagi-qa-ccc` repo, alongside (not replacing) the Appium suite:

```
dimagi-qa-ccc/
└── maestro_mobile/
    ├── flows/
    │   ├── shared_login_signup.yaml    # common steps, invoked via runFlow
    │   ├── login_signup_success.yaml   # tc_01
    │   └── login_account_locked.yaml   # tc_02
    ├── config/
    │   └── browserstack.yml            # BrowserStack App Automate config (phase 2)
    ├── test_data/
    │   └── mobile_test_data.yaml       # ported TC_1 / TC_2 blocks, same shape as mobile_workers.yaml
    ├── scripts/
    │   └── run_tests.py                # reads test_data, invokes maestro locally or via BrowserStack SDK
    └── README.md
```

## Flow authoring & locators

- Maestro flows are declarative YAML (`tapOn`, `inputText`, `assertVisible`, `back`, etc.) — no page-object classes; the flow *is* the test.
- Locators from `mobile_locators.yaml` translate directly: resource-ids become `id: "org.commcare.dalvik:id/..."` selectors, XPath text-matches become `text:` selectors (raw XPath also supported if needed).
- Real logic (reading test data values, conditional branches like "handle fingerprint prompt if it appears") uses Maestro's `runScript`/`evalScript` JS steps.
- Shared steps between the two pilot flows (signup entry → fingerprint → demo-user popup → username entry) are factored into `shared_login_signup.yaml`, invoked from each flow via `runFlow`, rather than duplicated.

## Test data & execution wiring — two phases

**Phase 1 (local):** Run both flows via `maestro test flows/<name>.yaml` directly against a local Android emulator or a device connected over ADB, installing `app-cccStaging-release.apk` locally. This validates locators, flow logic, and the shared sub-flow against a real build before adding cloud complexity.

**Phase 2 (BrowserStack):** Once both flows pass locally, add `config/browserstack.yml` and run the same, unmodified flow files via BrowserStack's Maestro integration (`browserstack-sdk maestro test ...`) against BrowserStack App Automate — same flows, only the execution target changes. `BROWSERSTACK_USERNAME`/`BROWSERSTACK_ACCESS_KEY` are read the same way as `settings.cfg`/env vars today. BrowserStack's SDK auto-uploads the APK, so the manual `curl`-based upload logic in `appium_driver.py` does not need to be ported.

`test_data/mobile_test_data.yaml` keeps the same shape as today's `mobile_workers.yaml` (`TC_1: {country_code, phone_number, username, backup_code}`, `TC_2: {...}`). `scripts/run_tests.py` reads the relevant block and invokes each flow with the values passed in as env overrides (`-e COUNTRY_CODE=... -e PHONE_NUMBER=... -e USERNAME=... -e BACKUP_CODE=...`), interpolated into the flow as `${COUNTRY_CODE}` etc. The same runner script supports both local and BrowserStack invocation modes.

## Out of scope for this pilot (deferred, not forgotten)

- Remaining 7 mobile test files (tc_03, 05–10 — opportunity flows, learn/delivery apps, payments, messaging, notifications)
- GitHub Actions CI, Slack/email notifications
- Allure/JUnit reporting integration beyond BrowserStack's own dashboard

## Testing

Manual verification: run both flows locally against a real device/emulator and confirm they pass (tc_01 completes sign-in and reaches the home screen with the side menu verified; tc_02 reaches the account-locked popup), matching what the Appium versions currently verify. Then repeat against BrowserStack App Automate once phase 2 is wired up.
