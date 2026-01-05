import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification, simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class Message(BasePage):

    CHANNEL_HEADER_TXT = locators.get("messaging", "channel_header_txt")
    NO_CHANNEL_MSG_TXT = locators.get("messaging", "no_channel_message_txt")

    def verify_channel_list(self):
        assert self.is_displayed(self.CHANNEL_HEADER_TXT), "Channel Header not visible"
        assert self.is_displayed(self.NO_CHANNEL_MSG_TXT), "Channel Message not visible"
        self.navigate_back()
        pass
