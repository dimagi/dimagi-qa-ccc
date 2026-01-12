import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class WorkerVisitsPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    WORKER_VISITS_TABLE_ELEMENT = locators.get("worker_visits_page", "worker_visits_table_element")
    WORKER_VISITS_ROW = locators.get("worker_visits_page", "worker_visits_row_item")
    WORKER_VISITS_SELECT_ALL_CHECKBOX = locators.get("worker_visits_page", "worker_visits_select_all_checkbox")
    APPROVE_ALL_BUTTON = locators.get("worker_visits_page", "approve_all_button")
    APPROVE_POPUP_BUTTON = locators.get("worker_visits_page", "approve_popup_button")
    REJECT_ALL_BUTTON = locators.get("worker_visits_page", "reject_all_button")
    REJECT_POPUP_BUTTON = locators.get("worker_visits_page", "approve_popup_button")
    APPROVE_BUTTON = locators.get("worker_visits_page", "approve_button")
    REJECT_BUTTON = locators.get("worker_visits_page", "reject_button")
    TABS_CONTAINER = locators.get("worker_visits_page", "tabs_container")
    VISITS_TAB_ITEM_BY_NAME = locators.get("worker_visits_page", "visits_tab_item_by_name")
    VISIT_DETAILS_CONTAINER = locators.get("worker_visits_page", "visit_details_container")
    USERNAME_SECTION = locators.get("worker_visits_page", "username_section")
    SUSPEND_BUTTON = locators.get("worker_visits_page", "suspend_button")
    SUSPEND_USER_REASON_INPUT = locators.get("worker_visits_page", "suspend_user_reason_input")
    SUSPEND_POPUP_BUTTON = locators.get("worker_visits_page", "suspend_popup_button")
    REVOKE_SUSPEND_BUTTON = locators.get("worker_visits_page", "revoke_suspend_button")


    def set_select_all_checkbox_worker_visits(self, state):
        checkbox = self.wait_for_element(self.WORKER_VISITS_SELECT_ALL_CHECKBOX)
        if checkbox.is_selected() != state:
            checkbox.click()
        time.sleep(2)
        self.verify_approve_and_reject_all_btns_present()

    def set_row_checkbox_from_list(self, row_data_list):
        if len(row_data_list) != 3:
            raise ValueError("row_data must contain exactly 3 items: [date, entity_name, check_status]")
        date, entity_name, check = row_data_list
        by, xpath = self.WORKER_VISITS_ROW
        actual_xpath = xpath.format(date=date, entity_name=entity_name)
        table = self.wait_for_element(self.WORKER_VISITS_TABLE_ELEMENT)
        row = table.find_element(By.XPATH, actual_xpath)
        checkbox = row.find_element(By.XPATH, ".//td[1]//input[@type='checkbox']")
        self.wait_for_clickable(checkbox)
        if checkbox.is_selected() != check:
            checkbox.click()
        time.sleep(1)
        self.verify_approve_and_reject_all_btns_present()

    def click_row_item_from_list(self, row_data_list):
        if len(row_data_list) != 2:
            raise ValueError("row_data must contain exactly 2 items: [date, entity_name]")
        date, entity_name = row_data_list
        by, xpath = self.WORKER_VISITS_ROW
        actual_xpath = xpath.format(date=date, entity_name=entity_name)
        table = self.wait_for_element(self.WORKER_VISITS_TABLE_ELEMENT)
        row = table.find_element(By.XPATH, actual_xpath)
        date_ele = row.find_element(By.XPATH, f".//td[contains(normalize-space(), '{date}')]")
        self.click_element(date_ele)
        time.sleep(1)
        assert self.wait_for_element(self.VISIT_DETAILS_CONTAINER).is_displayed(), "Details container not present."

    def verify_approve_and_reject_all_btns_present(self):
        approve_all = self.wait_for_element(self.APPROVE_ALL_BUTTON)
        reject_all = self.wait_for_element(self.REJECT_ALL_BUTTON)
        assert approve_all.is_displayed() and reject_all.is_displayed(), "Approve & Reject All buttons not present."

    def click_approve_all_btn(self):
        self.click_element(self.APPROVE_ALL_BUTTON)
        time.sleep(1)
        self.click_element(self.APPROVE_POPUP_BUTTON)
        time.sleep(2)

    def click_reject_all_btn(self):
        self.click_element(self.REJECT_ALL_BUTTON)
        time.sleep(1)
        self.click_element(self.REJECT_POPUP_BUTTON)
        time.sleep(2)

    def click_approve_btn_in_details(self):
        self.scroll_into_view(self.APPROVE_BUTTON)
        self.click_element(self.APPROVE_BUTTON)

    def click_reject_btn_in_details(self):
        self.scroll_into_view(self.REJECT_BUTTON)
        self.click_element(self.REJECT_BUTTON)

    def verify_tabs_present(self, expected_tabs):
        tabs_container = self.wait_for_element(self.TABS_CONTAINER)
        missing_tabs = []
        for tab in expected_tabs:
            tab_xpath = "//label[contains(@class,'tab')][normalize-space(./text()[normalize-space()][1])='" + tab + "']"
            try:
                element = tabs_container.find_element(By.XPATH, tab_xpath)
                if not element.is_displayed():
                    missing_tabs.append(tab)
            except NoSuchElementException:
                missing_tabs.append(tab)
        assert not missing_tabs, f"Missing tabs: {', '.join(missing_tabs)}"

    def verify_worker_visits_tabs_present(self):
        self.verify_tabs_present(["Pending NM Review", "Approved", "Rejected", "All"])

    def click_tab_by_name(self, tab_name):
        by, xpath = self.VISITS_TAB_ITEM_BY_NAME
        actual_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_for_element((by, actual_xpath))
        self.click_element(tab)
        time.sleep(2)
        self.verify_tab_is_active(tab_name)

    def verify_tab_is_active(self, tab_name):
        by, xpath = self.VISITS_TAB_ITEM_BY_NAME
        actual_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_for_element((by, actual_xpath))
        class_items = tab.get_attribute("class")
        assert "active" in class_items, f"Tab '{tab_name}' is not active"

    def verify_worker_visits_table_headers_present(self, pending=False):
        if pending:
            expected_headers = ["Date", "Entity Name", "Deliver Unit", "Payment Unit", "Flags"]
        else:
            expected_headers = ["Date", "Entity Name", "Deliver Unit", "Payment Unit", "Flags", "Last Activity"]
        table = self.wait_for_element(self.WORKER_VISITS_TABLE_ELEMENT)
        headers = table.find_elements(By.XPATH, ".//thead//th")
        actual_headers = []
        for th in headers[1:]:
            text = th.text.strip()
            if text:
                actual_headers.append(text)
        actual_headers_lower = [h.lower() for h in actual_headers]
        expected_headers_lower = [h.lower() for h in expected_headers]
        missing_headers = [
            header for header in expected_headers_lower
            if header.lower() not in actual_headers_lower
        ]
        assert not missing_headers, (
            f"Missing headers: {missing_headers}\n"
            f"Actual headers found: {actual_headers}"
        )
        print(actual_headers)

    def approve_entity_from_visits_using_name_and_id(self, entity_name, entity_id):
        table = self.wait_for_element(self.WORKER_VISITS_TABLE_ELEMENT)
        row_xpath = f".//td[contains(normalize-space(), '{entity_name}')]"
        rows = table.find_elements(By.XPATH, row_xpath)
        for each in rows:
            self.click_element(each)
            time.sleep(2)
            assert self.wait_for_element(self.VISIT_DETAILS_CONTAINER).is_displayed(), "Details container not present."
            entity_id_element = self.find((By.XPATH, "//*[@id='visit-details']/div/div[1]/div[3]/div[2]"))
            if entity_id_element.is_displayed() and entity_id_element.text == entity_id:
                self.click_approve_btn_in_details()
                break

    def suspend_user_in_worker_visits(self, reason):
        self.click_element(self.USERNAME_SECTION)
        time.sleep(1)
        self.click_element(self.SUSPEND_BUTTON)
        time.sleep(1)
        self.type(self.SUSPEND_USER_REASON_INPUT, reason)
        self.click_element(self.SUSPEND_POPUP_BUTTON)
        time.sleep(2)

    def revoke_suspension_for_worker(self):
        self.click_element(self.USERNAME_SECTION)
        time.sleep(1)
        self.click_element(self.REVOKE_SUSPEND_BUTTON)
        time.sleep(1)
        self.navigate_backward()
        time.sleep(1)
        self.reload_page()
        self.wait_for_page_to_load()
        self.click_element(self.USERNAME_SECTION)
        time.sleep(1)
        assert self.wait_for_element(self.SUSPEND_BUTTON).is_displayed()

    def verify_overlimit_flag_present_for_the_entity_in_visits(self, entity_name):
        table = self.wait_for_element(self.WORKER_VISITS_TABLE_ELEMENT)
        row_xpath = f".//tbody/tr[td[normalize-space()='{entity_name}']]"
        row_ele = table.find_element(By.XPATH, row_xpath)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", row_ele)
        flags_ele = row_ele.find_elements(By.XPATH, "./td[6]//span")
        flags_list = [flag.text.strip().lower() for flag in flags_ele]
        print(flags_list)
        assert "over limit" in flags_list, f"Over limit flag not present for {entity_name}."
        print(f"Over limit flag present for {entity_name}.")
