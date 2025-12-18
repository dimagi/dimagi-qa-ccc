import allure
from datetime import datetime

def attach_mobile_screenshot(driver, name="Mobile Screenshot"):
    screenshot = driver.get_screenshot_as_png()
    allure.attach(screenshot, name, allure.attachment_type.PNG)

def attach_web_screenshot(driver, name="Web Screenshot"):
    screenshot = driver.get_screenshot_as_png()
    allure.attach(screenshot, name, allure.attachment_type.PNG)

def attach_text(name, text):
    allure.attach(text, name, allure.attachment_type.TEXT)
