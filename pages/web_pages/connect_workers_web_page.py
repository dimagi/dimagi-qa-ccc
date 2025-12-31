import os
import time
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectWorkersPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    ADD_WORKER_ICON = locators.get("connect_workers_page", "add_worker_icon")
    CONNECT_WORKERS_TABLE = locators.get("connect_workers_page", "connect_workers_table")
    DELETE_INVITES_BUTTON = locators.get("connect_workers_page", "delete_invites_btn")
    DELETE_INVITES_POPUP_BUTTON = locators.get("connect_workers_page", "delete_invites_popup_btn")
    INVITE_USERS_INPUT = locators.get("connect_workers_page", "invite_users_input")
    TAB_ITEM_BY_NAME = locators.get("connect_workers_page", "tab_item_by_name")
    TABLE_ELEMENT = locators.get("connect_workers_page", "table_element")
    NAME_ITEM_IN_TABLE = locators.get("connect_workers_page", "name_item_in_table")
    COUNT_BREAKDOWN_POPUP = locators.get("connect_workers_page", "count_breakdown_popup")
    FILTER_BUTTON = locators.get("connect_workers_page", "filter_button")
    FILTERS_MODAL_WINDOW = locators.get("connect_workers_page", "filters_modal_window")
    FILTER_BADGE = locators.get("connect_workers_page", "filter_badge")
    LAST_ACTIVE_DROPDOWN_FILTERS_WINDOW = locators.get("connect_workers_page", "last_active_dropdown")
    HAS_DUPLICATES_DROPDOWN_FILTERS_WINDOW = locators.get("connect_workers_page", "has_duplicates_dropdown")
    DELIVERIES_FLAGS_DROPDOWN_FILTERS_WINDOW = locators.get("connect_workers_page", "deliveries_with_flags_dropdown")
    HAS_OVERLIMIT_DROPDOWN_FILTERS_WINDOW = locators.get("connect_workers_page", "has_overlimit_dropdown")
    DELIVERIES_PENDING_REVIEW_DROPDOWN_FILTERS_WINDOW = locators.get("connect_workers_page","deliveries_with_pending_review_dropdown")
    APPLY_BTN_FILTER_WINDOW = locators.get("connect_workers_page", "apply_button_filter_window")
    ROLLBACK_LAST_PAYMENT_BTN = locators.get("connect_workers_page", "rollback_last_payment_btn")
    ROLLBACK_POPUP_BUTTON = locators.get("connect_workers_page", "rollback_popup_btn")
    IMPORT_PAYMENT_ICON = locators.get("connect_workers_page", "import_payment_btn")
    FILE_UPLOAD_IMPORT_PAYMENT = locators.get("connect_workers_page", "file_upload_import_payment")
    IMPORT_POPUP_BTN = locators.get("connect_workers_page", "import_popup_btn")
    IMPORT_STATUS_TEXT = locators.get("connect_workers_page", "import_status_text")


    def click_add_worker_icon(self):
        self.wait_for_element(self.ADD_WORKER_ICON)
        self.click_element(self.ADD_WORKER_ICON)

    def enter_invite_users_in_opportunity(self, num_list):
        input_element = self.wait_for_element(self.INVITE_USERS_INPUT)
        for each in num_list:
            input_element.send_keys(each)
            input_element.send_keys(Keys.ENTER)

    def nav_to_add_worker(self):
        self.is_breadcrumb_item_present("Connect Workers")
        self.click_add_worker_icon()
        self.verify_invite_users_input_present()

    def invite_workers_to_opportunity(self, num_list):
        self.nav_to_add_worker()
        self.enter_invite_users_in_opportunity(num_list)
        self.click_submit_btn()

    def verify_invite_users_input_present(self):
        input_element = self.wait_for_element(self.INVITE_USERS_INPUT)
        time.sleep(1)
        assert input_element.is_displayed(), "Invite users input is not present"

    def verify_numbers_in_connect_workers_table(self, num_list):
        table = self.wait_for_element(self.CONNECT_WORKERS_TABLE)
        rows = table.find_elements(By.XPATH, ".//tbody/tr")
        table_numbers = [row.find_element(By.XPATH, "./td[5]").text.strip() for row in rows]
        for number in num_list:
            assert number in table_numbers, f"Number '{number}' not found in the table!"

    def click_delete_invites_button(self):
        self.click_element(self.DELETE_INVITES_BUTTON)
        self.click_element(self.DELETE_INVITES_POPUP_BUTTON)

    def select_and_delete_rows_by_phone_numbers(self, num_list):
        table = self.wait_for_element(self.TABLE_ELEMENT)
        checkboxes = []
        for num in num_list:
            num = num.strip()
            try:
                row_xpath = f".//tbody//tr[.//td[normalize-space()='{num}']]"
                row = table.find_element(By.XPATH, row_xpath)
                checkboxes.append(row.find_element(By.XPATH, ".//td[1]//input[@type='checkbox']"))
            except NoSuchElementException:
                print(f"Phone number not found in table: {num}")
        if checkboxes:
            for checkbox in checkboxes:
                self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", checkbox)
                if not checkbox.is_selected():
                    self.click_element(checkbox)
            self.click_delete_invites_button()

    def is_number_present_in_table(self, number):
        table = self.wait_for_element(self.TABLE_ELEMENT)
        number = number.strip()
        row_xpath = f".//tbody//tr[.//td[normalize-space()='{number}']]"
        rows = table.find_elements(By.XPATH, row_xpath)
        if not rows:
            print(f"Phone number not present in table: {number}")
            return False
        return True

    def verify_and_delete_if_numbers_present_in_invites(self, num_list):
        numbers_present = []
        for each in num_list:
            if self.is_number_present_in_table(each):
                numbers_present.append(each)
        self.select_and_delete_rows_by_phone_numbers(numbers_present)
        time.sleep(1)

    def click_tab_by_name(self, tab_name):
        by, xpath_template = self.TAB_ITEM_BY_NAME
        xpath = xpath_template.format(tab_name=tab_name)
        self.click_element((by, xpath))
        time.sleep(2)
        self.verify_tab_is_active(tab_name)

    def verify_tab_is_active(self, tab_name):
        by, xpath = self.TAB_ITEM_BY_NAME
        actual_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_for_element((by, actual_xpath))
        class_items = tab.get_attribute("class")
        assert "active" in class_items, f"Tab '{tab_name}' is not active"

    def verify_table_element_present(self):
        time.sleep(2)
        element = self.wait_for_element(self.TABLE_ELEMENT)
        assert element.is_displayed(), "Table element is not present"

    def verify_table_headers_present(self, expected_headers_list):
        self.verify_table_element_present()
        table_element = self.wait_for_element(self.TABLE_ELEMENT)
        header_elements = table_element.find_elements(By.XPATH, ".//thead//th")
        actual_headers = [
            header.text.strip()
            for header in header_elements
            if header.text.strip()
        ]
        actual_headers_lower = [h.lower() for h in actual_headers]
        expected_headers_lower = [h.lower() for h in expected_headers_list]
        missing_headers = [
            header for header in expected_headers_lower
            if header.lower() not in actual_headers_lower
        ]
        assert not missing_headers, (
            f"Missing headers: {missing_headers}\n"
            f"Actual headers found: {actual_headers}"
        )
        print(actual_headers)

    def verify_deliver_table_headers_present(self):
        self.verify_table_headers_present(["#", "Name", "Last active", "Payment unit", "Delivery progress", "Delivered", "Pending", "Approved", "Rejected"])

    def verify_payments_table_headers_present(self):
        self.verify_table_headers_present(["#", "Name", "Last active", "Accrued (INR)", "Total Paid (INR)", "Last paid", "Confirm (INR)"])

    def verify_connect_workers_table_headers_present(self):
        self.verify_table_headers_present(["#", "Status", "Name", "Phone Number", "Invited Date", "Last Active", "Started Learn", "Completed Learn", "Time to Complete Learning", "First Delivery", "Time to Start Deliver"])

    def verify_learn_table_headers_present(self):
        self.verify_table_headers_present(["#", "Name", "Last active", "Started Learning", "Modules completed", "Completed Learning", "Assessment", "Attempts", "Learning hours"])

    def click_name_in_table(self, name):
        by, xpath = self.NAME_ITEM_IN_TABLE
        actual_xpath = xpath.format(name=name)
        name_column = self.wait_for_element((by, actual_xpath))
        self.click_element(name_column)
        time.sleep(2)

    def navigate_to_worker_visits(self, worker_name):
        self.click_tab_by_name("Deliver")
        time.sleep(1)
        self.click_name_in_table(worker_name)
        time.sleep(1)
        self.is_breadcrumb_item_present("Visits")

    def click_and_verify_status_count_breakdown_for_item(self, params):
        item_name = params[0].strip()
        column_name = params[1].strip().lower()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = ".//thead//th[.//span[normalize-space() = '" + column_name.capitalize() + "']]"
        header = table.find_element(By.XPATH, header_xpath)
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        if item_name.lower() == "total":
            row_xpath = ".//tbody//tr[td[normalize-space()='Total']]"
        else:
            row_xpath = ".//tbody//tr[.//p[normalize-space() = '" + item_name + "']]"
        row = table.find_element(By.XPATH, row_xpath)
        cell_span_xpath = f"./td[{column_index}]//span"
        span_element = row.find_element(By.XPATH, cell_span_xpath)
        self.click_element(span_element)
        time.sleep(1)
        self.verify_count_breakdown_popup_present()

    def verify_count_breakdown_popup_present(self):
        menu_element = self.wait_for_element(self.COUNT_BREAKDOWN_POPUP)
        assert menu_element.is_displayed(), "Count breakdown popup is not present"
        text_elements = menu_element.find_elements(By.XPATH, ".//p | .//div | .//span")
        texts = set()
        for elem in text_elements:
            text = elem.text.strip()
            if text:
                texts.add(text)
        print(texts)

    def click_filter_button(self):
        self.click_element(self.FILTER_BUTTON)
        self.wait_for_element(self.FILTERS_MODAL_WINDOW)

    def select_last_active_filter_deliver_table(self, value):
        self.select_by_visible_text(self.LAST_ACTIVE_DROPDOWN_FILTERS_WINDOW, value)

    def select_has_duplicates_filter_deliver_table(self, value):
        self.select_by_visible_text(self.HAS_DUPLICATES_DROPDOWN_FILTERS_WINDOW, value)

    def select_deliveries_with_flags_filter_deliver_table(self, value):
        self.select_by_visible_text(self.DELIVERIES_FLAGS_DROPDOWN_FILTERS_WINDOW, value)

    def select_has_overlimit_filter_deliver_table(self, value):
        self.select_by_visible_text(self.HAS_OVERLIMIT_DROPDOWN_FILTERS_WINDOW, value)

    def select_deliveries_with_pending_review_filter_deliver_table(self, value):
        self.select_by_visible_text(self.DELIVERIES_PENDING_REVIEW_DROPDOWN_FILTERS_WINDOW, value)

    def click_apply_button_filters_window(self):
        self.click_element(self.APPLY_BTN_FILTER_WINDOW)

    def verify_active_filter_badge_present(self, value):
        value = str(value)
        element = self.wait_for_element(self.FILTER_BADGE)
        assert element.text == value, f"Filter badge value mismatch {element.text} != {value}"
        print(element.text)

    def clear_all_filters_deliver_table(self):
        self.click_filter_button()
        self.select_last_active_filter_deliver_table("Any time")
        self.select_has_duplicates_filter_deliver_table("---------")
        self.select_deliveries_with_flags_filter_deliver_table("---------")
        self.select_has_overlimit_filter_deliver_table("---------")
        self.select_deliveries_with_pending_review_filter_deliver_table("---------")
        self.click_apply_button_filters_window()
        time.sleep(2)

    def get_last_active_dates_from_deliver_table(self):
        table = self.wait_for_element(self.TABLE_ELEMENT)
        dates = []
        header_xpath = ".//thead//th[.//text()[normalize-space()='Last active']]"
        header = find_element_or_fail(table, By.XPATH, header_xpath, "Last active Column")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        rows = table.find_elements(By.XPATH, ".//tbody//tr")
        for row in rows:
            try:
                cell = row.find_element(By.XPATH, f"./td[{column_index}]")
                date_text = cell.text.strip()
                if date_text:
                    dates.append(date_text)
            except Exception:
                continue
        return dates

    def is_datetime_within_last_day(self, date_str, days_ago) -> bool:
        try:
            given_dt = datetime.strptime(date_str.strip(), "%d-%b-%Y %H:%M")
            now = datetime.now()
            lower_bound = now - timedelta(days=days_ago)
            return lower_bound <= given_dt <= now
        except ValueError:
            return False

    def apply_n_verify_last_active_filter_deliver_table(self):
        self.click_filter_button()
        self.select_last_active_filter_deliver_table("1 day ago")
        self.click_apply_button_filters_window()
        time.sleep(2)
        self.verify_active_filter_badge_present(1)
        all_dates = self.get_last_active_dates_from_deliver_table()
        for each in all_dates:
            assert self.is_datetime_within_last_day(each,
                                                    1), f"Filter Error, Last active 1 day ago\nLast active date present: {each}"

    def verify_column_value_in_learn_table(self, worker_name, expected_value, column_name):
        worker_name, column_name = worker_name.strip(), column_name.strip()
        expected_value = expected_value.strip()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = (".//thead//th[normalize-space() = '" + column_name + "']")
        header = find_element_or_fail(table, By.XPATH, header_xpath, f"{column_name} column")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = (".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]")
        row = find_element_or_fail(table, By.XPATH, row_xpath, f"{worker_name} worker")
        cell_xpath = f"./td[{column_index}]"
        cell_element = find_element_or_fail(row, By.XPATH, cell_xpath, f"Learn table column {column_index}")
        assert expected_value == cell_element.text.strip(), f"{column_name} value mismatch: {cell_element.text}"
        print(f"Value of {column_name} for {worker_name}: {expected_value}")

    def verify_column_not_empty_in_learn_table(self, worker_name, column_name):
        worker_name, column_name = worker_name.strip(), column_name.strip()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = (".//thead//th[normalize-space() = '" + column_name + "']")
        header = find_element_or_fail(table, By.XPATH, header_xpath, f"{column_name} column")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = (".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]")
        row = find_element_or_fail(table, By.XPATH, row_xpath, f"{worker_name} worker")
        cell_xpath = f"./td[{column_index}]"
        cell_element = find_element_or_fail(row, By.XPATH, cell_xpath, f"Learn table column {column_index}")
        assert cell_element.text not in ["", None], f"Value of {column_name} for {worker_name} is empty"

    def verify_modules_completed_status_bar_in_learn_table(self, worker_name, value):
        worker_name = worker_name.strip()
        column_name = 'Modules completed'
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = (".//thead//th[normalize-space() = '" + column_name + "']")
        header = find_element_or_fail(table, By.XPATH, header_xpath, f"{column_name} column")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = ".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]"
        row = find_element_or_fail(table, By.XPATH, row_xpath, f"{row_xpath} worker")
        cell_span_xpath = f"./td[{column_index}]//span"
        span_element = row.find_element(By.XPATH, cell_span_xpath)
        status_bar_xpath = f"./td[{column_index}]//div//div//div"
        status_bar_element = row.find_element(By.XPATH, status_bar_xpath)
        assert value in span_element.text, f"Percentage value '{span_element.text}' mismatch for {worker_name}"
        assert value in status_bar_element.get_attribute(
            "style"), f"Status bar value '{status_bar_element.get_attribute("style")}' mismatch for {worker_name}"
        print(f"Modules Completed Status Bar for {worker_name}: {status_bar_element.get_attribute("style")}")
        print(f"Modules completed percentage text for {worker_name}: {span_element.text}")

    def verify_green_bar_status_present(self, worker_name):
        worker_name = worker_name.strip()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = ".//thead//th[.//div[contains(@class,'bg-black')]]"
        header = find_element_or_fail(table, By.XPATH, header_xpath, f"Green status column")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = (".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]")
        row = find_element_or_fail(table, By.XPATH, row_xpath, f"{worker_name} worker")
        cell_xpath = f"./td[{column_index}]//div//div"
        cell_element = find_element_or_fail(row, By.XPATH, cell_xpath, f"Learn table column {column_index}")
        positive_condition = ('positive' in cell_element.get_attribute("class")) and (
                    'black' not in cell_element.get_attribute("class"))
        assert positive_condition, f"Green status is not present for {worker_name}"
        print(f"Green status present for {worker_name}: {cell_element.get_attribute("class")}")

    def verify_worker_assessment_status(self, worker_name, expected__status):
        self.verify_column_value_in_learn_table(worker_name, expected__status, "Assessment")
        self.verify_modules_completed_status_bar_in_learn_table(worker_name, "100")
        self.verify_green_bar_status_present(worker_name)
        self.verify_column_not_empty_in_learn_table(worker_name, "Attempts")
        self.verify_column_not_empty_in_learn_table(worker_name, "Completed Learning")

    def click_last_paid_date_n_verify_history(self, worker_name):
        worker_name = worker_name.strip()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = ".//thead//th[.//a[normalize-space() = 'Last paid']]"
        header = self.find_element_or_fail(table, By.XPATH, header_xpath, f"Last Paid date column Payment table")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = ".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]"
        row = table.find_element(By.XPATH, row_xpath)
        cell_span_xpath = f"./td[{column_index}]//span"
        span_element = row.find_element(By.XPATH, cell_span_xpath)
        self.click_element(span_element)
        time.sleep(1)
        self.verify_count_breakdown_popup_present()

    def rollback_last_payment(self):
        self.click_element(self.ROLLBACK_LAST_PAYMENT_BTN)
        time.sleep(1)
        self.click_element(self.ROLLBACK_POPUP_BUTTON)

    def fetch_username_from_payments(self, worker_name):
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = ".//thead//th[.//a[normalize-space() = 'Name']]"
        header = self.find_element_or_fail(table, By.XPATH, header_xpath, f"Name column Payment table")
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
        row_xpath = ".//tbody//tr[.//p[normalize-space() = '" + worker_name + "']]"
        row = table.find_element(By.XPATH, row_xpath)
        cell_span_xpath = f"./td[{column_index}]//div//p[2]"
        username_ele = row.find_element(By.XPATH, cell_span_xpath)
        assert username_ele, f"Username for {worker_name} is empty"
        return username_ele.text.strip()

    def import_make_payment_file(self):
        file_path = os.path.join(os.getcwd(), "test_data", "make_payment.xlsx")
        assert os.path.exists(file_path), f"File not found: {file_path}"
        print(file_path)
        file_input = self.wait_for_element(self.FILE_UPLOAD_IMPORT_PAYMENT)
        file_input.send_keys(file_path)
        assert file_input.get_attribute("value") != ""

    def make_payment_with_date_for_worker(self, worker_name, country_code, phone_number, amount):
        username = self.fetch_username_from_payments(worker_name)
        full_phone_number = country_code + phone_number
        curr_date = datetime.now().strftime("%Y-%m-%d")
        self.write_payment_details_to_excel([username, full_phone_number, worker_name, amount, curr_date])
        self.click_element(self.IMPORT_PAYMENT_ICON)
        self.import_make_payment_file()
        time.sleep(2)
        self.click_element(self.IMPORT_POPUP_BTN)
        time.sleep(2)
        assert "All done! View status" in self.get_text(self.IMPORT_STATUS_TEXT), "Import failed"