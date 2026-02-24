import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification

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
        self.wait_for_element(self.INVITE_OPP_TITLE_TXT)
        assert(self.is_displayed(self.INVITE_OPP_TITLE_TXT)
               & self.is_displayed(self.INVITE_OPP_TXT))

    def click_opportunity_invite(self):
        self.wait_for_element(self.INVITE_OPP_TITLE_TXT)
        self.click_element(self.INVITE_OPP_TITLE_TXT)

    def open_notifications(self):
        time.sleep(2)
        open_notification(driver=self.driver)
        time.sleep(3)


    def verify_payment_received(self):
        if self.is_displayed(self.EXPAND_BTN):
            self.click_element(self.EXPAND_BTN)
        assert self.is_displayed(self.PAYMENT_RECEIVED_TXT)
        assert self.is_displayed(self.PAYMENT_TXT)

    def click_payment_received(self):
        self.wait_for_element(self.PAYMENT_RECEIVED_TXT)
        self.click_element(self.PAYMENT_RECEIVED_TXT)