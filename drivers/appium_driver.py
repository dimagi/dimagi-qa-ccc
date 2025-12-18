from appium import webdriver
from appium.options.android import UiAutomator2Options

def create_mobile_driver(config):
    caps = config.caps()  # dict from android_caps.json

    options = UiAutomator2Options()
    for key, value in caps.items():
        options.set_capability(key, value)

    driver = webdriver.Remote(
        command_executor="http://127.0.0.1:4723",
        options=options
    )
    return driver
