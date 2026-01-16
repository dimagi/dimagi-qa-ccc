import subprocess
import time

def simulate_fingerprint(driver=None, run_on="local", finger_id=1, success=True):
    # pass
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

def open_notification():
    subprocess.run(["adb", "shell", "cmd", "statusbar", "expand-notifications"])


def background_app(driver, seconds=3):
    driver.background_app(seconds)

def relaunch_app(driver):
    driver.close_app()
    time.sleep(2)
    driver.launch_app()
