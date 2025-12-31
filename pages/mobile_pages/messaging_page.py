import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification, simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class Message(BasePage):


    def verify_channel_list(self):
        self.navigate_back()
        pass
