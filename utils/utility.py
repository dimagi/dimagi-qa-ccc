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

def background_app(driver, seconds=3):
    driver.background_app(seconds)

def relaunch_app(driver):
    driver.close_app()
    time.sleep(2)
    driver.launch_app()
