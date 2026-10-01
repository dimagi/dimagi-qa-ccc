# Assessment Push Notification Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OS tray and in-app notification verification to `test_04_learn_app_assessments_delivery_app` after a user passes the learn assessment.

**Architecture:** Extend two existing page objects (`MobileNotifications`, `AppNotifications`) with new methods, add two locators to the YAML file, then wire three new `allure.step` blocks into the existing test. No new files are created.

**Tech Stack:** Python, pytest, Appium, allure-pytest, PyYAML-based locator loading

---

## File Map

| File | Change |
|---|---|
| `locators/mobile_locators.yaml` | Add 2 locators |
| `pages/mobile_pages/mobile_notifications.py` | Add 1 class constant + 1 method |
| `pages/mobile_pages/app_notifications.py` | Add 1 class constant + 1 method |
| `tests/mobile_tests/test_tc_03.py` | Add 2 page object instantiations + 3 allure steps |

---

### Task 1: Add locators to `mobile_locators.yaml`

**Files:**
- Modify: `locators/mobile_locators.yaml`

- [ ] **Step 1: Add the OS tray locator under `mobile_notifications`**

Open `locators/mobile_locators.yaml`. Find the `mobile_notifications:` section (currently ends at `payment_txt`). Add one line after `payment_txt`:

```yaml
mobile_notifications:
  invite_opp_title_txt: "(//android.widget.TextView[contains(@text, 'You have been invited to a CommCare Connect opportunity')])[1]"
  invite_opp_txt: "(//android.widget.TextView[contains(@text, 'You have been invited to a new job in Commcare Connect')])[1]"
  expand_btn: "//android.widget.TextView[contains(@text,'CommCare')]/ancestor::android.widget.RelativeLayout//android.widget.Button"
  payment_received_title_txt: "//android.widget.TextView[contains(@text,'Payment received')]"
  payment_txt: "//android.widget.TextView[contains(@text, 'You have received a payment')]"
  assessment_scored_title_txt: "//android.widget.TextView[contains(@text, 'Update on your Assessment')]"
```

- [ ] **Step 2: Add the in-app notification locator under `app_notification`**

Find the `app_notification:` section. Add one line after `notification_arrow`:

```yaml
app_notification:
  payment_txt: "//android.widget.TextView[contains(@text, 'You have received a payment')]"
  notification_header_txt: "//android.widget.TextView[@text='Notifications']"
  no_notification_txt: "org.commcare.dalvik:id/tvNoNotifications"
  notification_sync_btn: "org.commcare.dalvik:id/notification_cloud_sync"
  notification_row: "//androidx.recyclerview.widget.RecyclerView[@resource-id='org.commcare.dalvik:id/rvNotifications']/android.view.ViewGroup"
  notification_icon: "//android.widget.ImageView[@resource-id='org.commcare.dalvik:id/ivNotification']"
  notification_text: "//android.widget.TextView[@resource-id='org.commcare.dalvik:id/tvNotification']"
  notification_time: "//android.widget.TextView[@resource-id='org.commcare.dalvik:id/tvTime']"
  notification_arrow: "//android.widget.ImageView[@resource-id='org.commcare.dalvik:id/ivForwardArrow']"
  assessment_scored_txt: "//android.widget.TextView[@resource-id='org.commcare.dalvik:id/tvNotification' and contains(@text, 'Update on your Assessment')]"
```

- [ ] **Step 3: Commit**

```bash
git add locators/mobile_locators.yaml
git commit -m "feat: add assessment notification locators to mobile_locators.yaml"
```

---

### Task 2: Extend `MobileNotifications` with assessment notification method

**Files:**
- Modify: `pages/mobile_pages/mobile_notifications.py`

- [ ] **Step 1: Add the class-level locator constant**

Open `pages/mobile_pages/mobile_notifications.py`. After the existing `PAYMENT_TXT` constant, add:

```python
ASSESSMENT_SCORED_TITLE_TXT = locators.get("mobile_notifications", "assessment_scored_title_txt")
```

So the constants block looks like:

```python
class MobileNotifications(BasePage):

    INVITE_OPP_TITLE_TXT = locators.get("mobile_notifications", "invite_opp_title_txt")
    INVITE_OPP_TXT = locators.get("mobile_notifications", "invite_opp_txt")
    EXPAND_BTN = locators.get("mobile_notifications", "expand_btn")
    PAYMENT_RECEIVED_TXT = locators.get("mobile_notifications", "payment_received_title_txt")
    PAYMENT_TXT = locators.get("mobile_notifications", "payment_txt")
    ASSESSMENT_SCORED_TITLE_TXT = locators.get("mobile_notifications", "assessment_scored_title_txt")
```

- [ ] **Step 2: Add `check_and_open_assessment_notification` method**

Add this method after `check_and_open_notification`. It mirrors that method's retry pattern exactly — 6 retries at 20-second intervals (up to 2 minutes), closes the shade on final failure, raises a clear error:

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

- [ ] **Step 3: Commit**

```bash
git add pages/mobile_pages/mobile_notifications.py
git commit -m "feat: add check_and_open_assessment_notification to MobileNotifications"
```

---

### Task 3: Extend `AppNotifications` with assessment notification verification

**Files:**
- Modify: `pages/mobile_pages/app_notifications.py`

- [ ] **Step 1: Add the class-level locator constant**

Open `pages/mobile_pages/app_notifications.py`. After the existing `SYNC_BTN` constant, add:

```python
ASSESSMENT_SCORED_TXT = locators.get("app_notification", "assessment_scored_txt")
```

So the constants block looks like:

```python
class AppNotifications(BasePage):

    PAYMENT_RECEIVED_TXT = locators.get("app_notification", "payment_txt")

    NOTIFICATION_ROW = locators.get("app_notification", "notification_row")
    NOTIFICATION_ICON = locators.get("app_notification", "notification_icon")
    NOTIFICATION_TEXT = locators.get("app_notification", "notification_text")
    NOTIFICATION_TIME = locators.get("app_notification", "notification_time")
    NOTIFICATION_ARROW = locators.get("app_notification", "notification_arrow")
    NO_NOTIFICATION_TXT = locators.get("app_notification", "no_notification_txt")
    SYNC_BTN = locators.get("app_notification", "notification_sync_btn")
    ASSESSMENT_SCORED_TXT = locators.get("app_notification", "assessment_scored_txt")
```

- [ ] **Step 2: Add `verify_assessment_scored_notification` method**

Add this method after `verify_all_notifications`. It syncs first (consistent with `verify_all_notifications`) then asserts the specific row is visible:

```python
def verify_assessment_scored_notification(self):
    self.click_element(self.SYNC_BTN)
    time.sleep(10)
    assert self.is_displayed(self.ASSESSMENT_SCORED_TXT), \
        "Assessment scored notification not found in in-app notifications"
```

- [ ] **Step 3: Commit**

```bash
git add pages/mobile_pages/app_notifications.py
git commit -m "feat: add verify_assessment_scored_notification to AppNotifications"
```

---

### Task 4: Wire notification verification into `test_04_learn_app_assessments_delivery_app`

**Files:**
- Modify: `tests/mobile_tests/test_tc_03.py`

- [ ] **Step 1: Add page object instantiations**

Open `tests/mobile_tests/test_tc_03.py`. Find the `test_04_learn_app_assessments_delivery_app` function. Locate the block where mobile page objects are instantiated (around line 159–161):

```python
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    learn = LearnAppPage(mobile_driver)
```

Add two more instantiations:

```python
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    opportunity = OpportunityPage(mobile_driver)
    learn = LearnAppPage(mobile_driver)
    mobile_notifications = MobileNotifications(mobile_driver)
    app_notifications = AppNotifications(mobile_driver)
```

(`MobileNotifications` and `AppNotifications` are already imported at the top of the file.)

- [ ] **Step 2: Insert three new allure steps after `verify_certificate_screen()`**

Find the existing step (around line 219–221):

```python
    with allure.step("Verify Job Status for Passed Assessment"):
        learn.sync_with_server()
        learn.verify_certificate_screen()

    with allure.step("Verify Completed Opportunity details"):
        learn.verify_opportunity_details_screen()
```

Insert three new steps between them:

```python
    with allure.step("Verify Job Status for Passed Assessment"):
        learn.sync_with_server()
        learn.verify_certificate_screen()

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

    with allure.step("Verify Completed Opportunity details"):
        learn.verify_opportunity_details_screen()
```

- [ ] **Step 3: Commit**

```bash
git add tests/mobile_tests/test_tc_03.py
git commit -m "feat: add assessment push notification verification steps to test_04"
```

---

### Task 5: Push and update PR

- [ ] **Step 1: Push branch**

```bash
git push origin feat/assessment-push-notification-verification
```

- [ ] **Step 2: Verify PR dimagi/dimagi-qa-ccc#12 shows all 4 commits**

Open the PR and confirm the following commits are listed:
1. `Add design spec for assessment push notification verification in test_04`
2. `feat: add assessment notification locators to mobile_locators.yaml`
3. `feat: add check_and_open_assessment_notification to MobileNotifications`
4. `feat: add verify_assessment_scored_notification to AppNotifications`
5. `feat: add assessment push notification verification steps to test_04`
