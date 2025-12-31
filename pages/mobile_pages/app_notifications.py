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


    def verify_payment_received(self):
        assert self.is_displayed(self.PAYMENT_RECEIVED_TXT)
        self.click_element(self.PAYMENT_RECEIVED_TXT)
        time.sleep(2)
        simulate_fingerprint()

    def verify_all_notifications(self):
        rows = self.get_elements(self.NOTIFICATION_ROW)

        assert len(rows) > 0, "No notifications found in the list"

        for idx, row in enumerate(rows, start=1):
            assert row.find_element(*self.NOTIFICATION_ICON).is_displayed(), \
                f"Notification icon missing in row {idx}"

            text = row.find_element(*self.NOTIFICATION_TEXT).text
            assert text.strip() != "", f"Notification text empty in row {idx}"

            time = row.find_element(*self.NOTIFICATION_TIME).text
            assert time.strip() != "", f"Notification time missing in row {idx}"

            assert row.find_element(*self.NOTIFICATION_ARROW).is_displayed(), \
                f"Forward arrow missing in row {idx}"


