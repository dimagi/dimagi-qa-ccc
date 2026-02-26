import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import open_notification, simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class Message(BasePage):

    CHANNEL_HEADER_TXT = locators.get("messaging", "channel_header_txt")
    NO_CHANNEL_MSG_TXT = locators.get("messaging", "no_channel_message_txt")
    MESSAGE_TXT = locators.get("messaging", "message_txt")
    MESSAGE_TIME_TXT = locators.get("messaging", "message_time_txt")
    CHANNEL_NAME = locators.get("messaging", "channel_name_txt")
    MESSAGE_INPUT = locators.get("messaging", "message_input")
    SEND_MSG_BTN = locators.get("messaging", "send_msg_btn")

    NAVIGATION_DRAWER = locators.get("home_page", "navigation_drawer_btn")
    MESSAGING_BTN = locators.get("home_page", "messaging_btn")

    def verify_channel_list(self):
        assert self.is_displayed(self.CHANNEL_HEADER_TXT), "Channel Header not visible"
        assert (self.is_displayed(self.NO_CHANNEL_MSG_TXT) or
                self.is_displayed(self.CHANNEL_NAME)), "Channel Message not visible"
        self.navigate_back()
        pass

    def verify_connect_message(self):
        time.sleep(5)
        self.wait_for_element(self.MESSAGE_TXT)
        self.is_displayed(self.MESSAGE_TXT)
        self.is_displayed(self.MESSAGE_TIME_TXT)

    def open_channel_on_message(self, channel_name):
        self.click_element(self.NAVIGATION_DRAWER)
        time.sleep(2)
        self.click_element(self.MESSAGING_BTN)
        time.sleep(5)
        channels = self.get_elements(self.CHANNEL_NAME)
        print(len(channels))
        for channel in channels:
            name = channel.text.strip()
            print(name)
            if name == channel_name:
                channel.click()
            assert self.is_displayed(self.MESSAGE_INPUT)

    def fill_survey_form(self, timeout=30):
        start_time = time.time()
        answered_name = False
        answered_id = False

        while time.time() - start_time < timeout:
            try:
                messages = self.get_elements(self.MESSAGE_TXT)
                if not messages:
                    time.sleep(1)
                    continue

                last_message_text = messages[-1].text.strip().lower()

                # NAME question
                if last_message_text == "name" and not answered_name:
                    self.type_element(self.MESSAGE_INPUT, "test user")
                    self.click_element(self.SEND_MSG_BTN)
                    answered_name = True
                    time.sleep(1)
                    continue

                # ID question
                if last_message_text == "id" and answered_name and not answered_id:
                    self.type_element(self.MESSAGE_INPUT, "101")
                    self.click_element(self.SEND_MSG_BTN)
                    answered_id = True
                    break

            except Exception as e:
                # Handles stale element during RecyclerView refresh
                time.sleep(1)
                continue

        # Hard assertions
        assert answered_name, "Survey question 'Name' did not appear"
        assert answered_id, "Survey question 'ID' did not appear after Name"


