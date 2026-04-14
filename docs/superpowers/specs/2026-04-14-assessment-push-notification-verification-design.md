# Design: Assessment Push Notification Verification in test_04

**Date:** 2026-04-14  
**Scope:** Add post-assessment push notification verification to `test_04_learn_app_assessments_delivery_app` in `tests/mobile_tests/test_tc_03.py`

---

## Background

After a user submits an assessment form in the Learn app and it syncs to CommCare Connect, the server fires a Celery task (`notify_user_for_scored_assessment` in `commcare_connect/opportunity/tasks.py:719`) that sends a `ccc_generic_opportunity` FCM push notification with:

- **Action:** `ccc_generic_opportunity`
- **Key:** `scored_assessment`
- **Title:** `"Update on your Assessment"`
- **Body:** `"Assessment for opportunity '...' scored, check your status"`

This notification arrives on the device within ~1 minute of the assessment form syncing. On Android, clicking it navigates the user to the opportunity's learn progress screen (`CCC_DEST_LEARN_PROGRESS` routing via `ConnectActivity`). Currently `test_04` does not verify this notification.

---

## What We're Adding

After the user passes the assessment (`complete_assessment("90")`) and `verify_certificate_screen()` confirms the certificate, add three verification steps:

1. **OS tray notification** — wait for "Update on your Assessment" in the system notification shade, click it, verify the learn progress screen (certificate) is still displayed
2. **In-app notifications screen** — navigate to the in-app Notifications history, verify the "Update on your Assessment" notification is present by text

---

## Changes

### 1. `locators/mobile_locators.yaml`

Two new locators:

```yaml
mobile_notifications:
  # existing locators...
  assessment_scored_title_txt: "//android.widget.TextView[contains(@text, 'Update on your Assessment')]"

app_notification:
  # existing locators...
  assessment_scored_txt: "//android.widget.TextView[@resource-id='org.commcare.dalvik:id/tvNotification' and contains(@text, 'Update on your Assessment')]"
```

- `assessment_scored_title_txt`: matches the notification title in the OS system shade
- `assessment_scored_txt`: matches the notification row in the in-app history, scoped to `tvNotification` resource-id for precision

### 2. `pages/mobile_pages/mobile_notifications.py`

New class-level constant:
```python
ASSESSMENT_SCORED_TITLE_TXT = locators.get("mobile_notifications", "assessment_scored_title_txt")
```

New method — mirrors the existing `check_and_open_notification()` retry pattern (6 retries × 20 seconds = up to 2 minutes of polling):
```python
def check_and_open_assessment_notification(self, retries=6, wait_between=20):
    for attempt in range(1, retries + 1):
        try:
            self.open_notifications()
            self.scroll_to_element(self.ASSESSMENT_SCORED_TITLE_TXT)
            assert self.is_displayed(self.ASSESSMENT_SCORED_TITLE_TXT)
            self.click_element(self.ASSESSMENT_SCORED_TITLE_TXT)
            return
        except:
            if attempt < retries:
                self.refresh_notifications()
                time.sleep(wait_between)
            else:
                close_notification(driver=self.driver)
    raise AssertionError(f"Assessment scored notification not found after {retries} attempts")
```

### 3. `pages/mobile_pages/app_notifications.py`

New class-level constant:
```python
ASSESSMENT_SCORED_TXT = locators.get("app_notification", "assessment_scored_txt")
```

New method — syncs first (consistent with `verify_all_notifications()`), then asserts the notification row is visible:
```python
def verify_assessment_scored_notification(self):
    self.click_element(self.SYNC_BTN)
    time.sleep(10)
    assert self.is_displayed(self.ASSESSMENT_SCORED_TXT), \
        "Assessment scored notification not found in in-app notifications"
```

### 4. `tests/mobile_tests/test_tc_03.py` — `test_04_learn_app_assessments_delivery_app`

Add two page object instantiations alongside the others at the top of the test:
```python
mobile_notifications = MobileNotifications(mobile_driver)
app_notifications = AppNotifications(mobile_driver)
```

Insert three new `allure.step` blocks after the existing `"Verify Job Status for Passed Assessment"` step (after `learn.verify_certificate_screen()`), before `"Verify Completed Opportunity details"`:

```python
with allure.step("Wait for and click assessment scored push notification from OS tray"):
    mobile_notifications.check_and_open_assessment_notification()

with allure.step("Verify certificate screen still displayed after notification tap"):
    learn.verify_certificate_screen()

with allure.step("Navigate to in-app notifications and verify assessment scored notification"):
    home.open_side_menu()
    home.nav_to_notifications()
    app_notifications.verify_assessment_scored_notification()
    home.nav_to_opportunities()
    opportunity.open_opportunity_from_list(opp_name, "new opportunity")
```

After the in-app check, navigation returns to the opportunity list and reopens the opportunity so the existing `verify_opportunity_details_screen()` and `download_delivery_app()` steps continue unaffected.

---

## Assumptions

- The `ccc_generic_opportunity` notification fires after **any** assessment scoring (pass or fail). The test adds this check only after the passing assessment, as the passing flow is not skipped and produces the most meaningful verification.
- The OS notification title text `"Update on your Assessment"` is stable — it comes from a hardcoded string in `notify_user_for_scored_assessment` on the server, not a translated string at this time.
- After clicking the tray notification, the app navigates to the learn progress screen where `VIEW_JOB_STATUS_BTN` is present, allowing `verify_certificate_screen()` to run without modification.

---

## Files Changed Summary

| File | Type of change |
|---|---|
| `locators/mobile_locators.yaml` | 2 new locators |
| `pages/mobile_pages/mobile_notifications.py` | 1 constant + 1 method |
| `pages/mobile_pages/app_notifications.py` | 1 constant + 1 method |
| `tests/mobile_tests/test_tc_03.py` | 2 instantiations + 3 allure steps |
