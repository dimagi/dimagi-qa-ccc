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

    NOTIFICATION_BTN = locators.get("delivery_app_page", "notification_btn")
    PAYMENT_CONFIRM_LBL_TXT = locators.get("delivery_app_page", "payment_confirm_lbl_txt")
    YES_BTN = locators.get("delivery_app_page", "yes_btn")
    ASK_ME_LATER_BTN = locators.get("delivery_app_page", "ask_me_later_btn")

    TRANSFERRED_TOTAL_TXT = locators.get("delivery_app_page", "transferred_total_txt")
    PAYMENT_ROWS = locators.get("delivery_app_page", "payment_rows")
    ROW_AMOUNT_TXT = locators.get("delivery_app_page", "row_amount_txt")
    ROW_STATUS_TXT = locators.get("delivery_app_page", "row_status_txt")
    RECEIVED_BTN =locators.get("delivery_app_page", "received_btn")
    CONFIRM_PAYMENT_POPUP_TXT = locators.get("delivery_app_page", "confirm_pay_popup_btn")
    PAYMENT_YES_BTN = locators.get("delivery_app_page", "payment_yes_btn")
    PAYMENT_NO_BTN = locators.get("delivery_app_page", "payment_no_btn")
    REVERT_BTN = locators.get("delivery_app_page", "revert_btn")
    CONNECT_MESSAGE_TXT = locators.get("delivery_app_page", "connect_message_txt")
    SYNC_WITH_SERVER = locators.get("learn_app_page", "sync_with_server")
    PRIMARY_VISIT_COUNT = locators.get("delivery_app_page", "primary_visit_count_txt")
    USER_ID = locators.get("delivery_app_page", "logged_in_userid_txt")
    PAYMENT_TAB = locators.get("delivery_app_page", "payment_tab")

    def submit_form(self, form_name, record_loc=True, user_id_input=None):
        if not self.is_displayed(self.DELIVERY_START_BTN):
            self.navigate_back()
        self.click_element(self.DELIVERY_START_BTN)
        time.sleep(1)
        self.click_element(self.CASE_LIST_BTN)
        for el in self.get_elements(self.CASE_FORMS_BTN):
            if form_name.lower() in el.text.lower():
                el.click()
                break

        ts = int(time.time() * 1000)  # milliseconds
        name = f"Automation User {ts}"
        if user_id_input is None:
            user_id_input = ts % 1000000

        self.type_element(self.NAME_INPUT, name)
        self.click_element(self.NEXT_BTN)
        self.type_element(self.ID_INPUT, user_id_input)
        self.click_element(self.NEXT_BTN)
        if record_loc:
            self.click_element(self.RECORD_LOCATION_BTN)
            time.sleep(3)
            if self.is_displayed(self.RECORD_LOCATION_BTN):
                self.click_element(self.RECORD_LOCATION_BTN)
        self.wait_for_element(self.FINISH_BTN)
        self.click_element(self.FINISH_BTN)

        return {
            "name": name,
            "id": user_id_input
        }
    time.sleep(20)

    def verify_payment_info(self):
        self.sync_with_server()
        self.nav_to_view_job()
        time.sleep(2)
        self.scroll_to_end()
        assert self.is_displayed(self.PU_TITLE_TXT), "PU title is not displayed"
        assert self.is_displayed(self.PAYMENT_APPROVED_COUNT_TXT), "Approved count is not displayed"
        assert self.is_displayed(self.PAYMENT_AMOUNT_TXT), "Payment amount is not displayed"
        assert self.is_displayed(self.REMAINING_COUNT_TXT), "Remaining count is not displayed"
        assert self.is_displayed(self.PU_NEXT_ARROW_BTN), "Next arrow button is not displayed"
        self.click_element(self.PU_NEXT_ARROW_BTN)

        # ---------- Submitted Delivery List ----------
        delivery_cards = self.get_elements(self.DELIVERY_LIST)

        assert len(delivery_cards) > 0, "No submitted delivery records found"

        for card in delivery_cards:
            assert card.find_element(*self.DELIVERY_ITEM_NAME_TXT).is_displayed(), \
                "Delivery item name not displayed"

            assert card.find_element(*self.DELIVERY_ITEM_DATE_TXT).is_displayed(), \
                "Delivery item date not displayed"

        self.navigate_back()

    def nav_to_view_job(self):
        self.click_element(self.VIEW_JOB_STATUS_BTN)
        # time.sleep(1)
        # self.click_element(self.PAYMENT_TAB)


    def nav_to_app_notification(self):
        self.click_element(self.NOTIFICATION_BTN)

    def verify_payment_popup(self):
        time.sleep(5)
        assert self.is_displayed(self.PAYMENT_CONFIRM_LBL_TXT), "Payment confirmation not displayed"
        assert self.is_displayed(self.YES_BTN), "Yes is not displayed"
        assert self.is_displayed(self.ASK_ME_LATER_BTN), "Ask Me Later is not displayed"
        self.click_element(self.YES_BTN)
        time.sleep(2)

    def verify_transfer_tile_on_payment_tab(self):
        # transferred total
        total_txt = self.get_text(self.TRANSFERRED_TOTAL_TXT)
        total_amount = int("".join(filter(str.isdigit, total_txt)))

        # Iterate
        rows = self.get_elements(self.ROW_AMOUNT_TXT)
        calculated_sum = 0

        for row in rows:
            amount_txt = row.text
            amount = int("".join(filter(str.isdigit, amount_txt)))
            calculated_sum += amount

        assert calculated_sum == total_amount, (
            f"Transferred mismatch: UI={total_amount}, Calculated={calculated_sum}"
        )

    def confirm_pay_on_payment_tab(self, confirm):
        self.click_element(self.RECEIVED_BTN)
        self.wait_for_element(self.CONFIRM_PAYMENT_POPUP_TXT)
        if confirm == "Yes":
            self.click_element(self.PAYMENT_YES_BTN)
            time.sleep(2)
            assert self.wait_for_element(self.REVERT_BTN)
        else:
            self.click_element(self.PAYMENT_NO_BTN)

    def verify_suspend_message(self):
        assert self.get_text(self.CONNECT_MESSAGE_TXT) == "User is Suspended. Please contact admin."

    def sync_with_server(self):
        self.click_element(self.SYNC_WITH_SERVER)
        time.sleep(3)

    def complete_daily_visits(self):
        """
        Completes daily visits until PRIMARY_VISIT_COUNT reaches max.
        Example: 0/5 -> 5/5
        """
        while True:
            visit_text = self.get_text(self.PRIMARY_VISIT_COUNT).strip()  # e.g. "2/5"
            current, total = map(int, visit_text.split("/"))
            print(f"Daily visit progress: {current}/{total}")
            if current >= total:
                break
            self.submit_form("Registration Form")
            time.sleep(2)
            self.sync_with_server()

        # Final assertion
        assert self.get_text(self.PRIMARY_VISIT_COUNT) == f"{total}/{total}", \
            "Daily visits did not complete correctly"


    def get_user_id(self):
        self.wait_for_element(self.USER_ID)
        id_txt = self.get_text(self.USER_ID).split(":")[1]
        print(id_txt)
        return id_txt.strip()

    def verify_daily_visits_progress(self):
        visit_text = self.get_text(self.PRIMARY_VISIT_COUNT).strip()  # e.g. "5/5"
        current, total = map(int, visit_text.split("/"))
        assert current == total, "Daily visits did not complete correctly"

    def verify_over_limit_message(self):
        return len(self.get_elements_if_present(self.CONNECT_MESSAGE_TXT)) > 0