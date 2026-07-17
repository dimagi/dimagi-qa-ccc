# Maestro Mobile Tests

Pilot Maestro port of the Appium mobile suite in `tests/mobile_tests/`. Covers `test_tc_01` and `test_tc_02` only — see `docs/superpowers/specs/2026-07-06-maestro-mobile-migration-pilot-design.md` for the full migration plan.

## Prerequisites
- A JDK on `JAVA_HOME` (Maestro needs it to run). Android Studio ships one — point `JAVA_HOME` at its `jbr` folder (e.g. `...\Android\Android Studio\jbr`) rather than installing a separate JDK.
- Maestro CLI installed (`curl -Ls "https://get.maestro.mobile.dev" | bash`), with `~/.maestro/bin` on `PATH`.
- Android SDK platform-tools/emulator on `PATH` (`adb`, `emulator`), with `ANDROID_HOME` set.
- Android Studio emulator running, or a physical device connected over ADB. On this repo's dev machine, the emulator (`Medium_Phone_API_36.0`) needed `-gpu swiftshader_indirect` — the default hardware GL renderer crashed on launch.
- The staging APK installed on that target — it currently lives at `../app/app-cccStaging-release.apk` (i.e. `dimagi-qa-ccc/app/`, not `commcare-android/app/`): `adb install -r -g ../app/app-cccStaging-release.apk`. The `-g` grants all runtime permissions at install time, avoiding a string of permission dialogs on first launch.

## Running a flow directly
maestro test flows/login_signup_success.yaml

## Running via the data-driven runner
python scripts/run_tests.py TC_1
python scripts/run_tests.py TC_2

## Running on BrowserStack
python scripts/run_on_browserstack.py

Uploads `app/app-cccStaging-release.apk` and the `flows/` folder to BrowserStack App Automate via its REST API (no `browserstack-sdk` CLI wrapper exists for Maestro — this hits the API directly), triggers a build against `Google Pixel 7-13.0` (matching the existing Appium suite's device), polls until it finishes, and prints the result. Exits non-zero on failure.

Credentials: reads `BROWSERSTACK_USERNAME`/`BROWSERSTACK_ACCESS_KEY` from the environment first, falling back to the `[browserstack]` section of `settings.cfg`. This is the **same `settings.cfg` at the repo root that the existing Appium/Selenium setup already uses** — no new file or location; if you already have it configured for the old suite, nothing extra is needed. On CI the values come from the repo's existing `BROWSERSTACK_*` secrets as environment variables, so `settings.cfg` is only needed for local runs.

Only `login_signup_success.yaml` and `login_account_locked.yaml` are passed via the `execute` parameter — `shared_login_signup.yaml` is a sub-flow only (invoked via `runFlow`) and would fail if BrowserStack tried to run it standalone.

**Zip structure matters**: BrowserStack requires every file to sit inside a single root folder within the uploaded zip (`flows/login_signup_success.yaml`, not flat at the zip root) — a flat zip fails with `BROWSERSTACK_TESTSUITE_PARSE_ERROR`. The `execute` paths themselves are relative to that root folder's *contents*, so they do **not** repeat the folder name (`login_signup_success.yaml`, not `flows/login_signup_success.yaml`).

## Debugging
maestro studio   # interactive element inspector against the running emulator/device

Alternative when you can't/don't want to use Maestro Studio's browser UI: `adb shell uiautomator dump /sdcard/window_dump.xml && adb pull //sdcard/window_dump.xml` (note the double leading slash on the remote path in Git Bash — a single `/` gets mangled by MSYS path conversion) gives you the same UI hierarchy as a static XML file.

## Confirmed selectors (no resource-id in the Appium locators file)
- Navigation drawer / hamburger icon: no resource-id, but has `content-desc="Open navigation drawer"` — use `tapOn: {text: "Open navigation drawer"}` (Maestro's `text:` selector matches accessibility content-description too).
- Toolbar overflow ("three-dot") menu: `content-desc="More options"` — use `tapOn: {text: "More options"}`.

## Known environment quirks (this emulator image)
- **Google phone-number / Smart Lock autofill sheet** pops up automatically whenever a phone-number-adjacent input field gains focus (country code, phone number, even the name field triggered a "stylus tips" variant) and steals the keystrokes meant for the underlying field. Fix applied throughout the flows: after `tapOn` on a text field, add `tapOn: {text: "Cancel", optional: true}` to dismiss it if present, then `tapOn` the field again before `inputText` — the popup only appears on first focus.
- **`assertVisible`/`tapOn` on `text:` selectors require a full match, not substring.** Popup body text that continues past your target phrase (e.g. "You have entered the wrong Backup Code. Please try again...") won't match a plain substring — wrap it as `.*your phrase.*`.
- **Device-level location prompts** (Google's "Location Accuracy" dialog, then the app's own "Enable Location Service" screen) block the very first sign-up attempt after a fresh install/clear. `adb shell cmd location set-location-enabled true` isn't sufficient on its own — you also have to tap through the Google Location Accuracy dialog once (choosing "Turn on") and relaunch the app for it to pass the check.
- **`maestro test`/`run_tests.py` need `maestro`, `adb`, and `java` resolvable via a real Windows `PATH` search**, not just a shell alias — Python's `subprocess.run` on Windows won't find `maestro.bat` from a bare `"maestro"` without `shutil.which` resolving it first (already handled in `run_tests.py`).
