import os
from datetime import datetime, timedelta

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

_AI_HEALING_ENABLED = os.getenv("AI_HEALING_ENABLED", "false").lower() == "true"


class BasePage:
    def __init__(self, page):
        self.page = page

    def _locator(self, selector):
        return self.page.locator(selector).first

    def click(self, selector, force=False):
        try:
            self._locator(selector).click(force=force)
        except PlaywrightTimeoutError:
            if _AI_HEALING_ENABLED:
                healed = self._ai_heal(selector)
                self._locator(healed).click(force=force)
            else:
                raise

    def type(self, selector, text):
        try:
            self._locator(selector).fill(text)
        except PlaywrightTimeoutError:
            if _AI_HEALING_ENABLED:
                healed = self._ai_heal(selector)
                self._locator(healed).fill(text)
            else:
                raise

    def get_text(self, selector):
        return self._locator(selector).inner_text()

    def is_displayed(self, selector, timeout=5000):
        try:
            self._locator(selector).wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def select_by_visible_text(self, selector, text):
        self._locator(selector).select_option(label=text)

    def scroll_into_view(self, selector):
        self._locator(selector).scroll_into_view_if_needed()

    def click_link_by_text(self, link_text):
        self.page.get_by_role("link", name=link_text, exact=False).first.click()

    def enter_date(self, selector, date_value):
        parts = date_value.split("-")
        if len(parts) == 3 and len(parts[2]) == 4:
            formatted = f"{parts[2]}-{parts[1]}-{parts[0]}"
        else:
            formatted = date_value

        self._locator(selector).evaluate(
            "(el, value) => { el.value = value; el.dispatchEvent(new Event('change')); }",
            formatted,
        )
        actual_value = self._locator(selector).input_value()
        assert actual_value == formatted, (
            f"Failed to set date. Expected '{formatted}', but got '{actual_value}'"
        )

    def generate_date_range(self, days_to_add):
        today = datetime.today()
        start = today + timedelta(days=2)
        end = start + timedelta(days=days_to_add)
        return start.strftime("%d-%m-%Y"), end.strftime("%d-%m-%Y")

    def _ai_heal(self, selector):
        from openai import OpenAI

        api_key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError(f"Element not found and AI healing has no API key: {selector}")

        page_src = self.page.content()[:6000]
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=150,
            messages=[{
                "role": "user",
                "content": (
                    "In this HTML page source, find an element that matches "
                    f"the intent of CSS/XPath selector {selector}. "
                    "Reply with ONLY a valid XPath string (starting with //) or CSS selector, nothing else.\n\n"
                    f"{page_src}"
                ),
            }],
        )
        healed = response.choices[0].message.content.strip()
        if not healed:
            raise RuntimeError(f"AI healing returned unusable result for: {selector}")
        if healed.startswith("//") or healed.startswith("("):
            healed = f"xpath={healed}"
        print(f"[AI HEAL] Original: {selector} -> Healed: {healed}")
        return healed
