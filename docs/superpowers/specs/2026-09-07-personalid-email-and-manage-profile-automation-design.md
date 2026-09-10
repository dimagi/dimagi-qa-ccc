# PersonalID Email + Manage Profile — Mobile Automation Design

**Ticket:** [CCCT-2784](https://dimagi.atlassian.net/browse/CCCT-2784) — End to end testing scripts for Manage Profile
**Feature source:** [CCC-101](https://dimagi.atlassian.net/browse/CCC-101) → epic CCCT-2344 (CCCT-2456 … CCCT-2461)
**Target build:** CommCare Connect **2.65 staging** — the APK now in `app/app-cccStaging-release.apk`
(verified `versionName=2.65`, pointing at `staging.commcarehq.org`). No `commcare_2.65`
branch exists yet, so **`origin/master` is the source reference**; behaviour below was first
established on `origin/commcare_2.64` and then re-verified against `origin/master`.
**Framework:** Maestro (`maestro_mobile/`), continuing the migration off the Appium suite
**Date:** 2026-09-07

> **Scope decision (2026-09-07):** 2.65 also adds a *Change Backup Code* feature to the
> Profile screen (a fourth email workflow, `FORGOT_BACKUP_CODE_EXISTING_USER`, plus a
> "Recover backup code" → email OTP → "Set New Backup Code" journey). It is
> **deliberately deferred** — this spec covers signup, email addition, and Manage Profile
> only. See §8.

## 1. Why this is bigger than "Manage Profile"

Manage Profile cannot be tested in isolation. 2.64 introduces email capture as a
cross-cutting feature with **three launch contexts**, and Manage Profile is only one of
them. `EmailWorkFlow` names them explicitly:

| Workflow | Entry point | On success |
|---|---|---|
| `REGISTRATION` | new signup, after backup code | → photo capture |
| `RECOVERY` | account recovery, after backup code | → finalize recovery, success message |
| `EXISTING_USER` | Manage Profile → Edit Profile, or the email offer prompt | → write email, finish activity |

The same two screens (`PersonalIdEmailFragment`, `PersonalIdEmailVerificationFragment`)
serve all three. Automating one context and not the others would leave the shared screens
covered by accident rather than by design, so this spec covers all four surfaces:
signup, recovery, the email offer prompt, and Manage Profile.

## 2. Feature behaviour

Established from the 2.64 source and re-verified against `origin/master` (the 2.65 build).
`PersonalIdBackupCodeFragment` was rewritten from Java to Kotlin between the two, but the
routing conditions below are byte-for-byte equivalent, and every selector in §7 is
unchanged. Where this section names a screen, that screen is identical on both.

### 2.1 Master toggle

Every email screen is gated on the server-driven release toggle `email_otp_verification`
(`ReleaseToggleHelper`, read from `PersonalIdSessionData.featureReleaseToggles` or the
local toggle table). **If it is off for the test account, all email screens silently
disappear** and the app falls back to 2.63 behaviour. This is an environment
precondition, not a test case.

### 2.2 Signup (REGISTRATION)

The nav graph now runs:

```
phone → biometric config → phone OTP → name → backup code → email → photo capture
```

`PersonalIdBackupCodeFragment` routes to the email step when the toggle is active,
and straight to photo capture when it is not.

### 2.3 Recovery (RECOVERY)

`PersonalIdBackupCodeFragment` shows the email step after the backup code is accepted
**only when the session data carries no email**. `ConfirmBackupCodeResponseParser`
populates that field only when the server already holds a *verified* address for the user.
The branch:

- recovering user **without** an email → email step offered; skip or verify → recovery success
- recovering user **with** a verified email → email step skipped entirely → recovery success

This is the single most important behaviour in the release notes, and it requires two
distinct recovery accounts to test.

Note: navigating to the email step also stamps the last-offer date, which suppresses the
offer prompt (§2.4) for 30 days.

### 2.4 Email offer prompt (EmailOfferHelper)

A signed-in user with no email is offered one. Guard conditions, all of which must hold:
signed in, toggle active, no email on the account, offer count below 2, and either no
prior offer or 30+ days since the last one. The count and date are written **before** the
dialog is shown, so dismissing by back/swipe still consumes an offer.

Accepting launches the PersonalID activity in its existing-user email collection mode.

### 2.5 Manage Profile

Drawer profile card → **"Manage Profile"** (`header_manage_profile`) → PersonalID unlock
gate → `PersonalIdProfileActivity` (portrait-locked, back arrow on every destination).

**Profile screen** — read-only rows for Name / Phone Number / Email Address, a photo that
is tappable to update, a destructive "Forget PersonalID Account" button, and an
"Edit Profile" toolbar action.

**Edit Profile screen** — editable Name and Email, **disabled** Phone, an OTP notice above
the email field, and a Cancel/Save row where Save **starts disabled**.

Validation (`PersonalIdProfileEditViewModel`):

- Save is enabled only when the form is modified **and** the name is valid **and** the email is valid
- name is valid when it is not blank
- an empty email is valid only when the user had no email to begin with — clearing an
  existing address is explicitly disallowed
- otherwise the address must pass the shared email-format check

**Documented quirk worth its own case** (from `docs/personalid/manage_profile.md` in
commcare-android): photo, name and email are three independent saves, and **name commits
before the email OTP step**. A user who edits both and then abandons verification keeps
the new name while the email stays unchanged.

### 2.6 Verification screen

Shared by all three workflows. 2-minute resend cooldown, with the countdown text and the
resend button mutually exclusive. Repeated failure raises "Verification unsuccessful"
offering "Try again" / "Proceed without email". Post-verify routing is workflow-specific
per the table in §1.

## 3. Test inventory

37 cases across 10 test flows (plus one shared sub-flow that carries no cases of its own).
Case steps are written at UI level; resource IDs live in the selector appendix (§7) so the
cases stay readable.

### 3.1 Signup — `signup_email_add.yaml` (REGISTRATION)

| ID | Case |
|---|---|
| SE_01 | After the backup code is set, the Email step is shown, titled "Add your email (optional)" with the account-recovery description |
| SE_02 | Continue stays disabled until a validly formatted address is entered |
| SE_03 | An invalid address shows "Please enter a valid email address." |
| SE_04 | "Skip for now" raises "Skip email?" / "Are you sure you want to skip?"; **NO** returns to the Email step with the typed value intact |
| SE_05 | **YES** continues to photo capture |

### 3.2 Signup — `signup_email_verify.yaml` (REGISTRATION)

| ID | Case |
|---|---|
| SE_06 | A valid address + Continue opens Verify Email, showing the code prompt with that address |
| SE_07 | Resend is hidden behind a countdown for 2 minutes, then becomes available |
| SE_08 | A wrong code shows "You have entered the wrong 6-digit passcode. Please try again." |
| SE_09 | Repeated failures raise "Verification unsuccessful"; "Proceed without email" continues to photo capture |
| SE_10 | The correct code continues to photo capture, which greets the new user. **Automated in Appium** (`test_tc_11.py`), not Maestro — see §5. There is **no** "Email Added" dialog on this path; that belongs to MP_13 |
| SE_11 | **Moved to Manage Profile - see MP_19.** Not reachable during signup: `verify_email_otp` parks the address on the ConfigurationSession with no uniqueness check when no account exists yet. The error is an `IntegrityError` raised only when writing an email onto an *existing* user, so it needs the `EXISTING_USER` path AND a correct code |
| SE_12 | Exhausting the verification attempts shows "Maximum verification attempts reached. Please try again later." |

### 3.3 Recovery — `recovery_email_prompt.yaml` (RECOVERY)

| ID | Case |
|---|---|
| RE_01 | Recovering an account with no stored email shows the Email step once the backup code is accepted |
| RE_02 | Skipping the Email step completes recovery and shows the recovery success message — not photo capture |
| RE_03 | **[OTP-gated]** Verifying the code completes recovery |

### 3.4 Recovery — `recovery_email_skipped.yaml` (RECOVERY)

| ID | Case |
|---|---|
| RE_04 | Recovering an account that already has a verified email goes straight to recovery success, with no Email step |

### 3.5 Email offer — `email_offer_prompt.yaml` (EXISTING_USER)

| ID | Case |
|---|---|
| EO_01 | A signed-in user with no email is offered "Add your email address" |
| EO_02 | "Not now" dismisses the offer and leaves the user where they were |
| EO_03 | "Add email" opens the email collection screen |

### 3.6 Manage Profile — `profile_view.yaml`

| ID | Case |
|---|---|
| MP_01 | The drawer shows "Manage Profile" beneath the user's name when signed in |
| MP_02 | Tapping it passes the unlock gate and opens Profile, showing photo, name and phone subtitle |
| MP_03 | Personal Information lists Name, Phone Number and Email Address matching the account |
| MP_04 | "Edit Profile" opens the edit form with Save disabled and Phone not editable |

### 3.7 Manage Profile — `profile_edit_name.yaml`

| ID | Case |
|---|---|
| MP_05 | Changing the name enables Save |
| MP_06 | Saving shows "Your profile has been updated successfully."; the new name appears on Profile and in the drawer header |
| MP_07 | Clearing the name keeps Save disabled |

### 3.8 Manage Profile — `profile_edit_email.yaml`

| ID | Case |
|---|---|
| MP_08 | An invalid address shows "Enter a valid email address." and Save stays disabled |
| MP_09 | Clearing an existing address is rejected with "Email is required." |
| MP_10 | A valid new address + Save raises "Verify your new email"; Cancel returns to the form with values intact |
| MP_11 | "Send Code" opens the Verify Email screen for the new address |
| MP_12 | Changing name and email together and then abandoning verification keeps the new name and leaves the email unchanged (§2.5) |
| MP_13 | **[OTP-gated]** The correct code updates the email and returns to Profile |

### 3.9 Manage Profile — `profile_discard.yaml`

| ID | Case |
|---|---|
| MP_14 | Backing out with unsaved changes raises "Discard your changes?"; "Keep editing" returns to the form with values intact |
| MP_15 | "Discard" returns to Profile showing the original values |
| MP_16 | Backing out with no changes returns immediately, with no dialog |

### 3.10 Manage Profile — `profile_forget.yaml` (destructive — runs last)

| ID | Case |
|---|---|
| MP_17 | "Forget PersonalID Account" raises "Forget PersonalID?"; Cancel keeps the account signed in |
| MP_18 | Confirming clears the account and returns the app to its signed-out state |
| MP_19 | Changing the email to one another account already uses is rejected with "This email is already linked to another account. Please use a different email address." **[needs a real code - Appium]** Moved here from SE_11 |

## 4. Structure and conventions

### 4.1 Grouping

The existing flows are one-per-case, each paying a full `clearState` + signup (~2 min).
At 36 cases that is untenable, so flows are **grouped by area** and each performs sign-in
once. `profile_forget.yaml` runs last because it destroys session state.

### 4.2 Files

```
maestro_mobile/
  flows/
    shared_signin.yaml              # sub-flow (refactor of shared_login_signup.yaml)
    signup_email_add.yaml
    signup_email_verify.yaml
    recovery_email_prompt.yaml
    recovery_email_skipped.yaml
    email_offer_prompt.yaml
    profile_view.yaml
    profile_edit_name.yaml
    profile_edit_email.yaml
    profile_discard.yaml
    profile_forget.yaml
  scripts/run_tests.py              # register new flows + OTP injection
  test_data/mobile_test_data.yaml   # new accounts and addresses
```

`shared_signin.yaml` stays a sub-flow only and must **not** appear in the BrowserStack
`execute` list — the same constraint the README already records for
`shared_login_signup.yaml`.

### 4.3 Existing-suite fix (in scope)

`login_signup_success.yaml` taps `text: "Forget PersonalID user"`. On 2.64 the string
`personalid_forget_user` is gone; the Login 3-dot menu now reuses
`personalid_profile_forget_account` — **"Forget PersonalID Account"**. The flow fails on
2.64 until this is updated. Fixing it is part of this work; landing new flows on a red
suite is not acceptable.

## 5. Email OTP retrieval — solved

**The OTP-dependent cases go in the Appium suite, not Maestro.** Reading a code means
pausing mid-session to poll a mailbox, which only works where Python holds the session.
That is how `dimagi-qa-sureadhere` does it for password reset, and it works against
BrowserStack because the Python process runs locally and only the device is remote.

Maestro cannot: flows execute remotely as declarative YAML with no way to call back into
Python. It *could* fetch over HTTP via `evalScript`, but the mailbox is IMAP, and putting
mail credentials inside a flow file would ship them to BrowserStack on every run.

So SE_10, RE_03 and MP_13 are Appium; everything else stays Maestro. `utils/email_otp.py`
provides `EmailOtpReader`, modelled on the SureAdhere implementation:

```python
mailbox = EmailOtpReader(settings)
address = mailbox.address_for("se10")        # unique, plus-addressed
requested_at = time.time()                    # BEFORE asking the app to send
pid.enter_email(address)
code = mailbox.get_verification_code(address, not_before=requested_at)
```

`not_before` matters: a failed earlier run leaves a valid code in the inbox, and without it
a later run fails on a code that was genuinely correct at the time.

Configuration is two lines in `settings.cfg` (`address`, `imap_password` — a Gmail **app
password**, not the account password), or `QA_EMAIL_*` environment variables on CI. See
`settings-sample.cfg`.

**Proven on a real device 2026-09-08** (`test_tc_11.py`, ~7 minutes): PersonalID does deliver
to a plus-addressed Gmail, and the code is read and accepted end to end.

**Retracted 2026-09-10:** an earlier note here claimed the OTP email was sometimes
not delivered despite the API reporting success. That was wrong - a bug in
`_find_code`, not in the product. `imap_tools` `reverse=True` orders by UID, not by
date, and the reader treated the first message older than `not_before` as a
terminator. Out-of-order messages therefore ended the search before the real code
was reached, and every supposedly missing email was later confirmed present in the
inbox. The reader now collects all matches and takes the newest by date.

### Original design notes

Three of the 37 cases (SE_10, RE_03, MP_13) require reading a 6-digit code from a mailbox.
No mechanism exists in the suite today — the `+7426` demo accounts bypass phone OTP
entirely and there is no email equivalent.

**Design:** `run_tests.py` gains a helper that polls a QA mailbox over IMAP, extracts the
code, and injects it into the Maestro run as an `EMAIL_OTP` env var — the same mechanism
already used for `COUNTRY_CODE` and `BACKUP_CODE`. Credentials come from a new `[email]`
section of the existing root `settings.cfg` (the file the BrowserStack credentials already
use), and from repository secrets on CI. Credentials are supplied by the QA owner and read
from config; they are never typed into a login form.

**Until that mailbox exists**, the three cases are written as stubs that assert the flow
reaches the Verify Email screen correctly and then stop, each marked with the blocker.
The remaining 34 cases — every negative path, every skip path, and everything up to and
including "Send Code" — are fully automatable without it. Wiring the helper in later is a
contained change, not a rewrite.

## 6. Preconditions

| # | Requirement | Status |
|---|---|---|
| 1 | Staging APK at `app/app-cccStaging-release.apk` | **Met** — 2.65 staging build in place as of 2026-09-07 |
| 2 | `email_otp_verification` toggle active for all test accounts | **Outstanding** — server-side |
| 3 | Recovery account **with** a verified email | **Outstanding** |
| 4 | Recovery account **without** an email | **Outstanding** |
| 5 | Fresh signed-in account with no email and no prior offers (for EO_01–03) | **Outstanding** |
| 6 | An address already bound to another account (for MP_19) | **Met** - `automation.user.commcarehq+se101788875825@gmail.com`, bound by a passing SE_10 run |
| 7 | QA mailbox + IMAP credentials in `settings.cfg` | **Met** — verified reading a real code on a device 2026-09-08 |
| 8 | BrowserStack credentials in `settings.cfg` | **Met** |

**Run on BrowserStack against staging, not a local emulator.** `settings.cfg` sets
`run_on = browserstack` and `env.yaml` defaults to `stage`, which is where the `+7426` test
accounts exist. This is not a preference — a local emulator **cannot** register a fresh
account: Google Play Integrity rejects a side-loaded build, and the only bypass in ConnectID
is `UserInvite.objects.filter(phone_number=...).exists()`, i.e. the number must already be
invited to an opportunity on Connect. A real BrowserStack device (Pixel 7 / Android 13, with
`enableBiometric: true`) clears integrity and needs no such invite for an existing account.

Whether a **fresh** number clears integrity on a real device is still untested, and it is the
open question behind precondition 3-6. If it does not, registration cases need a pool of
pre-invited numbers rather than generated ones.

## 7. Selector appendix (2.64)

All ids are prefixed `org.commcare.dalvik:id/` in Maestro selectors.

**Drawer**

| Element | Selector |
|---|---|
| Manage Profile link | `header_manage_profile` — "Manage Profile" (underlined) |
| User name | `header_user_name` |
| Profile card | `profile_card` |

**Profile screen** (`personalid_profile_screen.xml`, title "Profile")

| Element | Selector |
|---|---|
| Photo | `profile_user_image_card` / `profile_user_image` |
| Name / phone subtitle | `profile_name` / `profile_phone_subtitle` |
| Value rows | `profile_value_name`, `profile_value_phone`, `profile_value_email` |
| Forget button | `profile_btn_forget_personalid` — "Forget PersonalID Account" |
| Edit action | menu `action_profile_edit` — "Edit Profile" |

**Edit Profile screen** (`personalid_profile_edit_screen.xml`, title "Edit Profile")

| Element | Selector |
|---|---|
| Name | `profile_input_name` / `profile_name_edit_text` |
| Phone (disabled) | `profile_input_phone` / `profile_phone_edit_text` |
| OTP notice | `profile_email_otp_notice` |
| Email | `profile_input_email` / `profile_email_edit_text` |
| Buttons | `btn_cancel` / `btn_save` (Save starts disabled) |

**Email screen** (`fragment_personalid_email.xml`, app bar "Email")

| Element | Selector |
|---|---|
| Input | `email_text_value` (hint "Email address") |
| Inline error | `personalid_email_error` |
| Skip / Continue | `personalid_email_skip_button` / `personalid_email_continue_button` |

**Verify Email screen** (`fragment_personalid_email_verification.xml`, app bar "Verify Email")

| Element | Selector |
|---|---|
| Description | `email_verification_description` |
| Code entry | `otp_code_view` |
| Error | `personalid_email_verify_error` |
| Countdown / Resend | `personalid_resend_countdown_text` / `personalid_email_resend_button` |
| Verify | `personalid_email_verify_button` |

**Code entry fields — not plain text inputs**

The backup code and both OTP fields are `org.commcare.views.connect.NumericCodeView`
(introduced 2.64, commcare-android `3d194096c`): a `LinearLayout` that builds one `EditText`
per digit at runtime. The children are assigned raw integer ids via `setId(index)`, so they
carry **no resource-id** and can only be reached by class.

Consequences, both confirmed on a real device:

- Sending a whole string to the container fails — Appium raises
  `InvalidElementStateException: Cannot set the element to '123456'`. `BasePage.type_code()`
  fills the child `EditText`s one digit at a time; the Maestro flows need the equivalent
  rather than a single `inputText` against `backup_code_view`.
- The registration screen carries **two** such widgets (`backup_code_view` +
  `confirm_code_view`); recovery carries only `backup_code_view`, alongside
  `welcome_back_layout`, `user_photo` and `not_me_button`. That difference is the most
  reliable registration-vs-recovery check — see the collision guard in the plan.
- Entry auto-submits on the sixth digit (`setCodeCompleteListener`), so no Verify tap is
  needed after filling an OTP.

**Text casing — two different rules**

Material **buttons** upper-case their labels, so the skip dialog's `Yes`/`No` string
resources render as **`YES`/`NO`** and must be matched that way. Material **menu items** do
not, so the overflow entry really is `Forget PersonalID Account`. Both are `@text` matches
and they behave differently; check a screenshot before trusting a string resource.

**Dialog strings**

| Context | Text |
|---|---|
| Skip email | "Skip email?" / "Are you sure you want to skip?" / **YES** / **NO** |
| OTP failure | "Verification unsuccessful" / "Try again" / "Proceed without email" |
| Email added | "Email Added" / "Your email has been added successfully." |
| Email offer | "Add your email address" / "Add email" / "Not now" |
| Forget | "Forget PersonalID?" / "This will remove your PersonalID account, ..." |
| Discard | "Discard your changes?" / "Discard" / "Keep editing" |
| Profile email OTP | "Verify your new email" / "Send Code" / "Cancel" |
| Save success | "Your profile has been updated successfully." |

Note: Maestro `text:` selectors match the **full** string, not a substring — wrap partial
matches as `.*phrase.*`, per the README.

## 8. Out of scope

- **Change Backup Code / forgot-backup-code (2.65).** The Profile screen in 2.65 carries an
  additional `profile_change_backup_code` button ("Change backup code") leading to a
  "Recover backup code" → email OTP → "Set New Backup Code" journey, backed by a fourth
  workflow `FORGOT_BACKUP_CODE_EXISTING_USER`. Deferred by decision on 2026-09-07. No flow
  in this spec asserts on it, and none assumes Forget is the only action on the Profile
  screen, so the extra button is inert for our purposes. Note for whoever picks it up: that
  journey *requires* an email on the account ("Please add an email address" otherwise), so
  it depends on both the email feature and the OTP retrieval in §5.
- **Photo capture / update.** Camera automation is unreliable on the emulator and the
  behaviour is already covered by CCCT-2330. The Profile screen's photo element is
  asserted as present (MP_02) but not exercised.
- **Analytics events** (CCCT-2476). Not observable through the UI.
- **The Appium suite** in `tests/mobile_tests/`. This work lands in Maestro only.
- **Server-side toggle administration.** Treated as an environment precondition.
