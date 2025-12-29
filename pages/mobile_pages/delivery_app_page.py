import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class DeliveryAppPage(BasePage):

    DELIVERY_APP_HEADER_TXT = locators.get("delivery_app_page", "delivery_app_header_txt")
    DELIVERY_START_BTN = locators.get("delivery_app_page", "delivery_app_start_btn")
    CASE_LIST_BTN = locators.get("delivery_app_page", "case_list_btn")
    CASE_FORMS_BTN = locators.get("delivery_app_page", "case_forms_btn")
    NAME_INPUT = locators.get("delivery_app_page", "name_input")
    NEXT_BTN = locators.get("delivery_app_page", "next_btn")
    FINISH_BTN = locators.get("delivery_app_page", "finish_btn")
    ID_INPUT = locators.get("delivery_app_page", "id_input")
    RECORD_LOCATION_BTN = locators.get("delivery_app_page", "record_location_btn")

    def submit_form(self, form_name):
        self.click_element(self.DELIVERY_START_BTN)
        time.sleep(1)
        self.click_element(self.CASE_LIST_BTN)
        for el in self.get_elements(self.CASE_FORMS_BTN):
            if form_name in el.text.lower():
                el.click()
                break

        self.type_element(self.NAME_INPUT, "Automation User")
        self.click_element(self.NEXT_BTN)
        self.type_element(self.ID_INPUT, "101")
        self.click_element(self.NEXT_BTN)
        self.click_element(self.RECORD_LOCATION_BTN)
        time.sleep(2)
        self.wait_for_element(self.FINISH_BTN)
        self.click_element(self.FINISH_BTN)

    def verify_payment_info(self):
        pass


