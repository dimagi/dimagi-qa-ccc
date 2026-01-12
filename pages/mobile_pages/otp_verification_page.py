import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class OTPVerificationPage(BasePage):

    OTP_VERIFICATION_TXT = locators.get("otp_page", "one_time_verification_txt")
    CHANGE_BTN = locators.get("otp_page", "change_btn")
    PHONE_INPUT = locators.get("login_page", "phone_input")


    def change_phone_number(self):
        self.wait_for_element(self.OTP_VERIFICATION_TXT)
        self.click_element(self.CHANGE_BTN)
        time.sleep(1)
        self.wait_for_element(self.PHONE_INPUT)

