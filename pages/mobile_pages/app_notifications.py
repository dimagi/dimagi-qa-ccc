import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class AppNotifications(BasePage):

    PAYMENT_RECEIVED_TXT = locators.get("app_notification", "payment_txt")

    NOTIFICATION_ROW = locators.get("app_notification", "notification_row")
    NOTIFICATION_ICON = locators.get("app_notification", "notification_icon")
    NOTIFICATION_TEXT = locators.get("app_notification", "notification_text")
    NOTIFICATION_TIME = locators.get("app_notification", "notification_time")
    NOTIFICATION_ARROW = locators.get("app_notification", "notification_arrow")
    NO_NOTIFICATION_TXT = locators.get("app_notification", "no_notification_txt")
    SYNC_BTN = locators.get("app_notification", "notification_sync_btn")


    def verify_payment_received(self):
        assert self.is_displayed(self.PAYMENT_RECEIVED_TXT)
        self.click_element(self.PAYMENT_RECEIVED_TXT)
        time.sleep(2)
        simulate_fingerprint(driver=self.driver, run_on=self.driver.run_on)

    def verify_all_notifications(self):
        self.click_element(self.SYNC_BTN)
        time.sleep(10)
        if self.is_displayed(self.NO_NOTIFICATION_TXT):
            print("No notifications found in the list")
            self.navigate_back()
            return

        icons = self.get_elements(self.NOTIFICATION_ICON)
        texts = self.get_elements(self.NOTIFICATION_TEXT)
        times = self.get_elements(self.NOTIFICATION_TIME)
        arrows = self.get_elements(self.NOTIFICATION_ARROW)

        count = len(texts)
        assert count > 0, "No notifications found"

        for i in range(count):
            assert icons[i].is_displayed(), f"Notification icon missing at index {i}"
            assert texts[i].text.strip(), f"Notification text empty at index {i}"
            assert times[i].text.strip(), f"Notification time missing at index {i}"
            assert arrows[i].is_displayed(), f"Notification arrow missing at index {i}"

        self.navigate_back()

