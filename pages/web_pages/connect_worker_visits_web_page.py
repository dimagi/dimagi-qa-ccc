import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from selenium.webdriver.common.keys import Keys

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class WorkerVisitsPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    TABLE_ELEMENT = locators.get("connect_workers_page", "table_element")
    WORKER_VISITS_ROW = locators.get("worker_visits_page", "worker_visits_row_item")
    WORKER_VISITS_SELECT_ALL_CHECKBOX = locators.get("worker_visits_page", "worker_visits_select_all_checkbox")
    APPROVE_ALL_BUTTON = locators.get("worker_visits_page", "approve_all_button")
    REJECT_ALL_BUTTON = locators.get("worker_visits_page", "reject_all_button")
    APPROVE_BUTTON = locators.get("worker_visits_page", "approve_button")
    REJECT_BUTTON = locators.get("worker_visits_page", "reject_button")
    TABS_CONTAINER = locators.get("worker_visits_page", "tabs_container")
    VISITS_TAB_ITEM_BY_NAME = locators.get("worker_visits_page", "visits_tab_item_by_name")
    VISIT_DETAILS_CONTAINER = locators.get("worker_visits_page", "visit_details_container")


    def set_select_all_checkbox_worker_visits(self, state):
        checkbox = self.wait_for_element(self.WORKER_VISITS_SELECT_ALL_CHECKBOX)
        if checkbox.is_selected() != state:
            checkbox.click()
        time.sleep(1)
        self.verify_approve_and_reject_all_btns_present()

    def set_row_checkbox_from_list(self, row_data_list):
        if len(row_data_list) != 3:
            raise ValueError("row_data must contain exactly 3 items: [date, entity_name, check_status]")
        date, entity_name, check = row_data_list
        by, xpath = self.WORKER_VISITS_ROW
        actual_xpath = xpath.format(date=date, entity_name=entity_name)
        table = self.wait_for_element(self.TABLE_ELEMENT)
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
        table = self.wait_for_element(self.TABLE_ELEMENT)
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

    def click_reject_all_btn(self):
        self.click_element(self.REJECT_ALL_BUTTON)

    def click_approve_btn(self):
        self.scroll_into_view(self.APPROVE_BUTTON)
        self.click_element(self.APPROVE_BUTTON)

    def click_reject_btn(self):
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