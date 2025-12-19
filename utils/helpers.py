import yaml
import json

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.by import By


class ConfigLoader:
    def __init__(self, env):
        with open("config/env.yaml", "r") as f:
            data = yaml.safe_load(f)

        self.env = env or data["default"]
        self.config = data[self.env]

        with open("config/android_caps.json", "r") as f:
            self.android_caps = json.load(f)

    def get(self, key):
        return self.config.get(key)

    def caps(self):
        return self.android_caps


class LocatorLoader:
    def __init__(self, file_path, platform):
        """
        platform: 'mobile' or 'web'
        """
        self.platform = platform
        with open(file_path, "r") as f:
            self.data = yaml.safe_load(f)

    def get(self, page, element):
        locator_value = self.data[page][element]

        # XPath detection (safe version)
        if locator_value.startswith("//") or locator_value.startswith("("):
            return (
                AppiumBy.XPATH if self.platform == "mobile" else By.XPATH,
                locator_value
            )

        # Default → ID
        return (
            AppiumBy.ID if self.platform == "mobile" else By.ID,
            locator_value
        )

import yaml

# class TestDataLoader:
#     def __init__(self, file_path="test_data/mobile_workers.yaml"):
#         with open(file_path, "r") as f:
#             self.data = yaml.safe_load(f)
#
#     def get(self, tc_id):
#         if tc_id not in self.data:
#             raise KeyError(f"No test data found for {tc_id}")
#         return self.data[tc_id]


class TestDataLoader:
    def __init__(self, file_paths=["test_data/mobile_workers.yaml", "test_data/web_test_data.yaml"]):
        self.data = {}
        for file_path in file_paths:
            with open(file_path, "r") as f:
                file_data = yaml.safe_load(f)
                if file_data:
                    self.data.update(file_data)

    def get(self, tc_id):
        if tc_id not in self.data:
            raise KeyError(f"No test data found for {tc_id}")
        return self.data[tc_id]
