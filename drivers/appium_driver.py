import os
from appium import webdriver
from appium.options.android import UiAutomator2Options

def create_mobile_driver(config, run_on):
    caps = config.caps(run_on)

    options = UiAutomator2Options()
    for key, value in caps.items():
        options.set_capability(key, value)

    if run_on == "browserstack":
        bstack_opts = caps.get("bstack:options", {})

        bstack_opts["userName"] = os.getenv("BROWSERSTACK_USERNAME")
        bstack_opts["accessKey"] = os.getenv("BROWSERSTACK_ACCESS_KEY")

        if not bstack_opts["userName"] or not bstack_opts["accessKey"]:
            raise Exception("BrowserStack credentials not set in environment")

        caps["bstack:options"] = bstack_opts

    driver = webdriver.Remote(
        command_executor=config.get(
            "browserstack_url" if run_on == "browserstack" else "appium_local_url"
        ),
        options=options
    )
    return driver
