import configparser
import os
import re
from pathlib import Path

import yaml

PLAYWRIGHT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[2]


class LocatorLoader:
    def __init__(self, file_path="locators/web_locators.yaml"):
        with open(PLAYWRIGHT_ROOT / file_path, "r") as f:
            self.data = yaml.safe_load(f)

    def get(self, page, element):
        locator_value = self.data[page][element]
        if locator_value.startswith("//") or locator_value.startswith("("):
            return f"xpath={locator_value}"
        return f"#{locator_value}"


class ConfigLoader:
    def __init__(self, env):
        with open(REPO_ROOT / "config" / "env.yaml", "r") as f:
            data = yaml.safe_load(f)
        self.env = env or data["default"]
        self.config = data[self.env]

    def get(self, key):
        return self.config.get(key)


class SettingsLoader:
    def __init__(self):
        self.config = configparser.ConfigParser()
        cfg_path = REPO_ROOT / "settings.cfg"
        if cfg_path.exists():
            try:
                self.config.read(cfg_path)
            except configparser.Error:
                pass

    def get(self, section, key, env_var=None, required=False, default=None):
        if env_var:
            env_value = os.getenv(env_var)
            if env_value:
                return env_value
        if self.config.has_option(section, key):
            return self.config.get(section, key)
        if default is not None:
            return default
        if required:
            raise RuntimeError(f"Missing setting: env_var={env_var} or [{section}].{key}")
        return None


def parse_org_and_opp(url):
    """Extract (org_slug, opp_id) from any Connect opportunity URL.

    Connect URLs look like https://<host>/a/<org_slug>/opportunity/<opp_id>/...
    The assigned-tasks page has no navigation entry, so tasking tests build its
    URL from these parts.
    """
    # opp ids are numeric on some deployments and UUIDs on others (staging)
    match = re.search(r"/a/([^/]+)/opportunity/([0-9a-fA-F-]+)(?:/|$|\?)", url)
    if not match:
        raise ValueError(f"Not an opportunity URL: {url}")
    return match.group(1), match.group(2)


class TestDataLoader:
    def __init__(self, file_path="test_data/web_test_data.yaml"):
        with open(REPO_ROOT / file_path, "r") as f:
            self.data = yaml.safe_load(f) or {}

    def get(self, tc_id):
        if tc_id not in self.data:
            raise KeyError(f"No test data found for {tc_id}")
        return self.data[tc_id]
