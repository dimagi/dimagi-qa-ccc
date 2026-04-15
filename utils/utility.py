import subprocess
import time

from pages.mobile_pages.base_page import BasePage


def simulate_fingerprint(driver, run_on, finger_id=1, success=True):
    if not BasePage.BIOMETRIC_ENABLED:
        print("Biometric disabled, skipping fingerprint simulation")
        return

    if run_on == "browserstack":
        if not driver:
            raise ValueError("Driver is required for BrowserStack fingerprint simulation")

        driver.execute_script(
            "browserstack_executor",
            {
                "action": "biometricAuthentication",
                "arguments": {
                    "type": "fingerprint",
                    "success": success
                }
            }
        )
    else:
        # Local emulator
        subprocess.run(
            ["adb", "emu", "finger", "touch", str(finger_id)],
            check=False
        )

def open_notification(driver):
    # subprocess.run(["adb", "shell", "cmd", "statusbar", "expand-notifications"])
    try:
        driver.execute_script("mobile: openNotifications")
    except:
        size = driver.get_window_size()
        driver.swipe(
            size["width"] // 2,
            int(size["height"] * 0.01),
            size["width"] // 2,
            int(size["height"] * 0.6),
            1000
        )

def close_notification(driver):
    try:
        driver.execute_script("mobile: closeNotifications")
    except:
        size = driver.get_window_size()
        driver.swipe(
            size["width"] // 2,
            int(size["height"] * 0.6),
            size["width"] // 2,
            int(size["height"] * 0.01),
            1000
        )

def clear_notifications(driver):
    """Click Android's 'Clear all' button inside the notification shade."""
    from appium.webdriver.common.appiumby import AppiumBy
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException

    selectors = [
        (AppiumBy.XPATH, '//*[@content-desc="Clear all notifications"]'),
        (AppiumBy.XPATH, '//*[contains(@content-desc,"Clear all")]'),
        (AppiumBy.XPATH, '//*[@text="CLEAR ALL" or @text="Clear all" or @text="Clear All"]'),
        (AppiumBy.ANDROID_UIAUTOMATOR,
         'new UiSelector().descriptionContains("Clear all")'),
    ]
    for locator in selectors:
        try:
            el = WebDriverWait(driver, 5).until(EC.element_to_be_clickable(locator))
            el.click()
            print(f"Cleared notifications via UI using {locator}")
            return
        except (TimeoutException, Exception):
            continue
    print("clear_notifications: 'Clear all' button not found — notification panel may already be empty")

def background_app(driver, seconds=3):
    driver.background_app(seconds)

def relaunch_app(driver):
    driver.close_app()
    time.sleep(2)
    driver.launch_app()
