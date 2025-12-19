import time

from mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class Notifications(BasePage):

    INVITE_OPP_TITLE_TXT = locators.get("notifications", "invite_opp_title_txt")
    INVITE_OPP_TXT = locators.get("notifications", "invite_opp_txt")



    def verify_opportunity_invite(self):
        self.wait_for_element(self.INVITE_OPP_TITLE_TXT)
        assert(self.is_displayed(self.INVITE_OPP_TITLE_TXT)
               & self.is_displayed(self.INVITE_OPP_TXT))

    def click_opportunity_invite(self):
        self.wait_for_element(self.INVITE_OPP_TITLE_TXT)
        self.click_element(self.INVITE_OPP_TITLE_TXT)

    def open_notifications(self):
        time.sleep(2)
        open_notification()
        time.sleep(2)




