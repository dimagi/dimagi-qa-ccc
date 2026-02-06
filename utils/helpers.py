import yaml
import json
import os
import configparser
from pathlib import Path

from appium.webdriver.common.appiumby import AppiumBy
from selenium.webdriver.common.by import By

PROJECT_ROOT = Path(__file__).resolve().parents[1]

class ConfigLoader:
    def __init__(self, env):
        with open(PROJECT_ROOT / "config/env.yaml", "r") as f:
            data = yaml.safe_load(f)

        self.env = env or data["default"]
        self.config = data[self.env]

        with open(PROJECT_ROOT / "config/android_caps.json", "r") as f:
            self.android_caps = json.load(f)

    def get(self, key):
        return self.config.get(key)

    def caps(self, run_on):
        return self.android_caps[run_on]

# utils/helpers.py (or utils/settings_loader.py)

class SettingsLoader:
    def __init__(self):
        self.config = configparser.ConfigParser()

        cfg_path = PROJECT_ROOT / "settings.cfg"
        if cfg_path.exists():
            self.config.read(cfg_path)

    def get(self, section, key, env_var=None, required=True, default=None):
        """
        Resolution order:
        1. CI / environment variables
        2. Local settings.cfg
        3. Default value (optional)
        """

        # 1️⃣ CI → env vars
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value

        # 2️⃣ Local → settings.cfg
        if self.config.has_option(section, key):
            return self.config.get(section, key)

        # 3️⃣ Default (for non-secret configs like run_on)
        if default is not None:
            return default

        if required:
            raise RuntimeError(
                f"Missing setting: env_var={env_var} or [{section}].{key}"
            )

        return None

class LocatorLoader:
    def __init__(self, file_path, platform):
        """
        platform: 'mobile' or 'web'
        """
        self.platform = platform
        with open(PROJECT_ROOT / file_path, "r") as f:
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
            with open(PROJECT_ROOT / file_path, "r") as f:
                file_data = yaml.safe_load(f)
                if file_data:
                    self.data.update(file_data)

    def get(self, tc_id):
        if tc_id not in self.data:
            raise KeyError(f"No test data found for {tc_id}")
        return self.data[tc_id]
