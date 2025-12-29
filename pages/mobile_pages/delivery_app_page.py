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
    VIEW_JOB_STATUS_BTN = locators.get("delivery_app_page", "view_job_status_btn")

    PU_TITLE_TXT = locators.get("delivery_app_page", "pu_title_txt")
    PAYMENT_APPROVED_COUNT_TXT = locators.get("delivery_app_page", "payment_approved_count_txt")
    PAYMENT_AMOUNT_TXT = locators.get("delivery_app_page", "payment_amount_txt")
    REMAINING_COUNT_TXT = locators.get("delivery_app_page", "remaining_count_txt")
    PU_NEXT_ARROW_BTN = locators.get("delivery_app_page", "pu_next_arrow_btn")

    DELIVERY_LIST = locators.get("delivery_app_page", "delivery_list")
    DELIVERY_ITEM_NAME_TXT = locators.get("delivery_app_page", "delivery_item_name_txt")
    DELIVERY_ITEM_DATE_TXT = locators.get("delivery_app_page", "delivery_item_date_txt")

    def submit_form(self, form_name, record_loc=True):
        if self.is_displayed(self.DELIVERY_START_BTN):
            self.navigate_back()
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
        if record_loc:
            self.click_element(self.RECORD_LOCATION_BTN)
        time.sleep(2)
        self.wait_for_element(self.FINISH_BTN)
        self.click_element(self.FINISH_BTN)

    def verify_payment_info(self):
        assert self.is_displayed(self.PU_TITLE_TXT), "PU title is not displayed"
        assert self.is_displayed(self.PAYMENT_APPROVED_COUNT_TXT), "Approved count is not displayed"
        assert self.is_displayed(self.PAYMENT_AMOUNT_TXT), "Payment amount is not displayed"
        assert self.is_displayed(self.REMAINING_COUNT_TXT), "Remaining count is not displayed"
        assert self.is_displayed(self.PU_NEXT_ARROW_BTN), "Next arrow button is not displayed"

        # ---------- Submitted Delivery List ----------
        delivery_cards = self.get_elements(self.DELIVERY_LIST)

        assert len(delivery_cards) > 0, "No submitted delivery records found"

        for card in delivery_cards:
            assert card.find_element(*self.DELIVERY_ITEM_NAME_TXT).is_displayed(), \
                "Delivery item name not displayed"

            assert card.find_element(*self.DELIVERY_ITEM_DATE_TXT).is_displayed(), \
                "Delivery item date not displayed"

        self.navigate_back()

