from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class LoginPage(BasePage):
    USERNAME_ELE = locators.get("cchq_login_page", "username_field")
    PASSWORD_ELE = locators.get("cchq_login_page", "password_field")
    COOKIE_ACCEPT_BUTTON = locators.get("cchq_login_page", "cookie_accept_button")
    IFRAME_GUIDE_POPUP = locators.get("cchq_login_page", "iframe_guide_popup")
    GUIDE_POPUP = locators.get("cchq_login_page", "guide_popup")
    SKIP_ONBOARDING = locators.get("cchq_home_page", "skip_onboarding")

    def enter_username_and_password(self, username, password):
        try:
            self.click(self.COOKIE_ACCEPT_BUTTON)
        except Exception:
            print("No Cookies alert present")
        self.type(self.USERNAME_ELE, username)
        self.page.locator(self.PASSWORD_ELE).first.fill(password)
        self.page.locator(self.PASSWORD_ELE).first.press("Enter")
        self.page.wait_for_timeout(3000)

    def valid_login_cchq(self, config, settings):
        try:
            cchq_url = config.get("cchq_url")
            self.page.goto(cchq_url)
            self.page.wait_for_load_state("load")
            self.enter_username_and_password(
                settings.get(section="creds", key="hq_username", env_var="hq_username"),
                settings.get(section="creds", key="hq_password", env_var="hq_password"),
            )
            self.page.wait_for_timeout(3000)
        except Exception:
            print("User is already logged in")

    def navigate_to_connect_page(self, config):
        connect_url = config.get("connect_url")
        new_page = self.page.context.new_page()
        # The root URL now serves the public marketing site, not the app - go straight to login.
        new_page.goto(f"{connect_url}/accounts/login/")
        assert connect_url in new_page.url
        return new_page

    def dismiss_guide_popup(self):
        try:
            frame = self.page.frame_locator(self.IFRAME_GUIDE_POPUP)
            popup = frame.locator(self.GUIDE_POPUP)
            popup.wait_for(state="visible", timeout=8000)
            frame.locator(self.SKIP_ONBOARDING).click()
            print("Skipped onboarding popup")
        except Exception:
            print("No onboarding popup occurred")
