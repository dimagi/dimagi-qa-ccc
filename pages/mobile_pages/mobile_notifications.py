import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification, close_notification, clear_notifications

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class MobileNotifications(BasePage):

    INVITE_OPP_TITLE_TXT = locators.get("mobile_notifications", "invite_opp_title_txt")
    INVITE_OPP_TXT = locators.get("mobile_notifications", "invite_opp_txt")
    EXPAND_BTN = locators.get("mobile_notifications", "expand_btn")
    PAYMENT_RECEIVED_TXT = locators.get("mobile_notifications", "payment_received_title_txt")
    PAYMENT_TXT = locators.get("mobile_notifications", "payment_txt")

    def verify_opportunity_invite(self):
        if self.is_displayed(self.EXPAND_BTN, timeout=30):
            self.click_element(self.EXPAND_BTN)
        time.sleep(5)
        self.scroll_to_element(self.INVITE_OPP_TITLE_TXT)
        assert(self.is_displayed(self.INVITE_OPP_TITLE_TXT)
               & self.is_displayed(self.INVITE_OPP_TXT))

    def click_opportunity_invite(self):
        self.scroll_to_element(self.INVITE_OPP_TITLE_TXT)
        self.click_element(self.INVITE_OPP_TITLE_TXT)

    def _invite_in_system_notifications(self):
        """Return True if the invite notification is present in the system notification list."""
        try:
            system_notifications = self.driver.execute_script("mobile: getNotifications")
            for n in system_notifications:
                title = (n.get("title") or "").lower()
                text = (n.get("text") or "").lower()
                if "commcare connect" in title or "invited" in title or "invited" in text:
                    return True
        except Exception as e:
            print(f"getNotifications failed: {e}")
        return False

    def check_and_open_notification(self, retries=5, wait_between=10):
        """Poll until the invite notification is received, then open the shade and click it."""
        for attempt in range(1, retries + 1):
            print(f"Waiting for invite notification (attempt {attempt}/{retries})...")
            if self._invite_in_system_notifications():
                open_notification(driver=self.driver)
                time.sleep(3)
                if self.is_displayed(self.EXPAND_BTN, timeout=5):
                    self.click_element(self.EXPAND_BTN)
                self.scroll_to_element(self.INVITE_OPP_TITLE_TXT)
                self.click_element(self.INVITE_OPP_TITLE_TXT)
                return
            if attempt < retries:
                time.sleep(wait_between)
        raise AssertionError(f"Invite notification not received after {retries} attempts ({retries * wait_between}s)")

    def refresh_notifications(self):
        close_notification(driver=self.driver)
        time.sleep(2)
        open_notification(driver=self.driver)
        time.sleep(3)

    def clear_all_notifications(self):
        clear_notifications(driver=self.driver)
        time.sleep(1)

    def open_notifications(self):
        time.sleep(2)
        open_notification(driver=self.driver)
        time.sleep(5)

    def close_notifications(self):
        time.sleep(1)
        try:
            close_notification(driver=self.driver)
            time.sleep(5)
        except:
            print("No notification screen present")


    def verify_payment_received(self):
        if self.is_displayed(self.EXPAND_BTN):
            self.click_element(self.EXPAND_BTN)
        assert self.is_displayed(self.PAYMENT_RECEIVED_TXT)
        assert self.is_displayed(self.PAYMENT_TXT)

    def click_payment_received(self):
        self.wait_for_element(self.PAYMENT_RECEIVED_TXT)
        self.click_element(self.PAYMENT_RECEIVED_TXT)