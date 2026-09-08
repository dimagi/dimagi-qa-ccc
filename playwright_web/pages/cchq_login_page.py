from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

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

    # HQ's login page is occasionally slow to render the form; this is a bounded
    # wait for it to appear, not a guess at how long login takes.
    LOGIN_FORM_TIMEOUT_MS = 30_000

    def valid_login_cchq(self, config, settings):
        """Log in to CommCare HQ, or confirm an existing session.

        Deliberately NOT wrapped in a blanket try/except. It used to be, and
        printed "User is already logged in" for *any* exception - a slow page, a
        renamed field, a network blip - then returned as though authenticated.
        The caller's next step (verify_home_page_title) would time out on the
        welcome heading, so the real cause was replaced by a reassuring message
        and a confusing symptom one step later. Seen intermittently on prod:
        "User is already logged in" followed by a 30s timeout on
        //h1[@class='mb-3 mt-5'].

        Being already logged in IS legitimate - the browser context is reused
        across tests in a file - so it is now detected positively, by the login
        form being absent, rather than inferred from something having gone
        wrong. Anything else raises with the URL it actually landed on.
        """
        self.page.goto(config.get("cchq_url"))
        self.page.wait_for_load_state("load")

        try:
            self.page.locator(self.USERNAME_ELE).first.wait_for(
                state="visible", timeout=self.LOGIN_FORM_TIMEOUT_MS
            )
        except PlaywrightTimeoutError:
            # No login form. Either an existing session (fine) or we are
            # somewhere unexpected (not fine) - tell the two apart.
            if "login" in self.page.url:
                raise AssertionError(
                    "On a login page but the username field never appeared after "
                    f"{self.LOGIN_FORM_TIMEOUT_MS // 1000}s: {self.page.url}"
                ) from None
            print("Already authenticated - reusing the existing session")
            return

        self.enter_username_and_password(
            settings.get(section="creds", key="hq_username", env_var="hq_username"),
            settings.get(section="creds", key="hq_password", env_var="hq_password"),
        )
        self.page.wait_for_timeout(3000)

        # Verify rather than assume: if the form is still up, the credentials or
        # the submit did not take, and failing here names that instead of
        # leaving the caller to time out on a heading.
        if self.page.locator(self.USERNAME_ELE).first.is_visible():
            raise AssertionError(
                f"Still on the login page after submitting credentials: {self.page.url}"
            )

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
