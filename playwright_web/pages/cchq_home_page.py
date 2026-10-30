from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class CCHQHomePage(BasePage):
    TITLE_ELE = locators.get("cchq_home_page", "welcome_title")
    APPLICATIONS_TAB = locators.get("cchq_home_page", "applications_tab")

    def verify_home_page_title(self, title):
        text = self.get_text(self.TITLE_ELE)
        assert title in text

    def select_app_under_applications_tab(self, app):
        self.click(self.APPLICATIONS_TAB)
        self.page.get_by_role("link", name=app, exact=False).first.click()
        self.page.wait_for_load_state("load")
        assert "/apps/view" in self.page.url

    def verify_app_present_under_applications_tab(self, app):
        self.click(self.APPLICATIONS_TAB, force=True)
        link = self.page.get_by_role("link", name=app, exact=False).first
        link.scroll_into_view_if_needed()
        assert link.is_visible(), f"{app} not found under applications tab"
        print(f"{app} present under applications tab")
        self.click(self.APPLICATIONS_TAB, force=True)
