import os
from appium import webdriver
from appium.options.android import UiAutomator2Options


def create_mobile_driver(config, settings, run_on):
    caps = config.caps(run_on)

    options = UiAutomator2Options()

    # Inject BrowserStack credentials
    if run_on == "browserstack":
        bs_user = settings.get(
            section="browserstack",
            key="BROWSERSTACK_USERNAME",
            env_var="BROWSERSTACK_USERNAME"
            )
        bs_key = settings.get(
            section="browserstack",
            key="BROWSERSTACK_ACCESS_KEY",
            env_var="BROWSERSTACK_ACCESS_KEY"
            )
        # bs_user = settings.get("BROWSERSTACK_USERNAME")
        # bs_key = settings.get("BROWSERSTACK_ACCESS_KEY")

        if not bs_user or not bs_key:
            raise Exception("BrowserStack credentials not set in environment")

        bstack_opts = caps.get("bstack:options", {}).copy()
        bstack_opts["userName"] = bs_user
        bstack_opts["accessKey"] = bs_key

        options.set_capability("bstack:options", bstack_opts)

    # Set remaining capabilities (avoid overriding bstack:options)
    for key, value in caps.items():
        if key != "bstack:options":
            options.set_capability(key, value)

    # 3Create driver with correct hub URL
    driver = webdriver.Remote(
        command_executor=config.get(
            "browserstack_url" if run_on == "browserstack" else "appium_local_url"
        ),
        options=options
    )

    return driver
