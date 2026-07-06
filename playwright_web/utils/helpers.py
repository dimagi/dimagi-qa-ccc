from pathlib import Path

import yaml

PLAYWRIGHT_ROOT = Path(__file__).resolve().parents[1]


class LocatorLoader:
    def __init__(self, file_path="locators/web_locators.yaml"):
        with open(PLAYWRIGHT_ROOT / file_path, "r") as f:
            self.data = yaml.safe_load(f)

    def get(self, page, element):
        locator_value = self.data[page][element]
        if locator_value.startswith("//") or locator_value.startswith("("):
            return f"xpath={locator_value}"
        return f"#{locator_value}"
