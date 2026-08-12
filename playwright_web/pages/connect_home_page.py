from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class ConnectHomePage(BasePage):
    LOGIN_WITH_CC_HQ = locators.get("connect_home_page", "login_with_cc_hq")
    AUTHORIZE_BUTTON = locators.get("connect_home_page", "authorize_button")
    OPPORTUNITIES_NAVBAR_LINK = locators.get("connect_home_page", "opportunities_navbar_item")
    PROGRAMS_NAVBAR_LINK = locators.get("connect_home_page", "programs_navbar_item")
    ORGANIZATION_CONTAINER = locators.get("connect_home_page", "organization_container")
    ORGANIZATION_DROPDOWN = locators.get("connect_home_page", "organization_dropdown")
    ORGANIZATION_NAME = locators.get("connect_home_page", "organization_name")

    def click_organizations_in_sidebar(self):
        self.click(self.OPPORTUNITIES_NAVBAR_LINK)
        self.page.wait_for_url("**/opportunity/**")

    def click_programs_in_sidebar(self):
        self.click(self.PROGRAMS_NAVBAR_LINK)
        self.page.wait_for_url("**/program/**")

    def signin_to_connect_page_using_cchq(self):
        try:
            self.click(self.LOGIN_WITH_CC_HQ)
            self.click(self.AUTHORIZE_BUTTON)
        except Exception:
            print("User already signed in")
        finally:
            self.click_organizations_in_sidebar()

    def is_org_selected(self, organization_name):
        self.page.wait_for_timeout(1000)
        return organization_name in self.get_text(self.ORGANIZATION_NAME)

    def select_organization_from_list(self, organization_name):
        if self.is_org_selected(organization_name):
            print(f"{organization_name} organization is already selected")
            return
        self.click(self.ORGANIZATION_DROPDOWN)
        container = self.page.locator(self.ORGANIZATION_CONTAINER).first
        # Match the row's FIRST paragraph, which is the organisation's name. Matching
        # any paragraph also matches the role line underneath it, and on prod three
        # organisations hold the role "Network Manager" while one is *named* "Network
        # Manager" - so the looser form is ambiguous and fails strict mode.
        item = container.locator(f"xpath=.//li[(.//p)[1][normalize-space()='{organization_name}']]")
        try:
            item.wait_for(state="visible", timeout=15000)
        except Exception:
            offered = [t.replace("\n", " / ").strip() for t in container.locator("xpath=.//li").all_inner_texts()]
            raise AssertionError(
                f"Organisation '{organization_name}' is not in the switcher. Offered: {offered or 'none'}"
            ) from None
        item.click()
