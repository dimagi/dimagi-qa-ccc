import subprocess
import time

def simulate_fingerprint(finger_id=1):
    subprocess.run(["adb", "emu", "finger", "touch", str(finger_id)])

def background_app(driver, seconds=3):
    driver.background_app(seconds)

def relaunch_app(driver):
    driver.close_app()
    time.sleep(2)
    driver.launch_app()
