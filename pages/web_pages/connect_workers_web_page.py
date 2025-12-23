import time
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from selenium.webdriver.common.keys import Keys

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectWorkersPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    ADD_WORKER_ICON = locators.get("connect_workers_page", "add_worker_icon")
    INVITE_USERS_INPUT = locators.get("connect_workers_page", "invite_users_input")
    TAB_ITEM_BY_NAME = locators.get("connect_workers_page", "tab_item_by_name")
    TABLE_ELEMENT = locators.get("connect_workers_page", "table_element")
    NAME_ITEM_IN_TABLE = locators.get("connect_workers_page", "name_item_in_table")
    COUNT_BREAKDOWN_POPUP = locators.get("connect_workers_page", "count_breakdown_popup")


    def click_add_worker_icon(self):
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

    def enter_users_and_submit_in_opportunity(self, num_list):
        self.enter_invite_users_in_opportunity(num_list)
        self.click_submit_btn()

    def verify_invite_users_input_present(self):
        input_element = self.wait_for_element(self.INVITE_USERS_INPUT)
        time.sleep(1)
        assert input_element.is_displayed(), "Invite users input is not present"

    def click_tab_by_name(self, tab_name):
        by, xpath_template = self.TAB_ITEM_BY_NAME
        xpath = xpath_template.format(tab_name=tab_name)
        tab = self.wait_for_element((by, xpath))
        self.click_element(tab)
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

    def click_name_in_table(self, name):
        by, xpath = self.NAME_ITEM_IN_TABLE
        actual_xpath = xpath.format(name=name)
        name_column = self.wait_for_element((by, actual_xpath))
        self.click_element(name_column)
        time.sleep(2)

    def click_and_verify_status_count_for_item(self, params):
        item_name = params[0].strip()
        column_name = params[1].strip().lower()
        table = self.wait_for_element(self.TABLE_ELEMENT)
        header_xpath = ".//thead//th[.//span[normalize-space() = '" + column_name.capitalize() + "']]"
        header = table.find_element(By.XPATH, header_xpath)
        column_index = len(header.find_elements(By.XPATH, "preceding-sibling::th")) + 1
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