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
