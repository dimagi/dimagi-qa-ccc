import allure
from datetime import datetime

def attach_mobile_screenshot(driver, name="Mobile Screenshot"):
    try:
        if driver:
            screenshot = driver.get_screenshot_as_png()
            allure.attach(
                screenshot,
                name=name,
                attachment_type=allure.attachment_type.PNG
            )
    except Exception as e:
        print(f"[WARN] Failed to capture mobile screenshot: {e}")

def attach_web_screenshot(driver, name="Web Screenshot"):
    screenshot = driver.get_screenshot_as_png()
    allure.attach(screenshot, name, allure.attachment_type.PNG)

def attach_text(name, text):
    allure.attach(text, name, allure.attachment_type.TEXT)
