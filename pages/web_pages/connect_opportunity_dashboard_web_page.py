import time

from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from web_pages.connect_opportunities_web_page import ConnectOpportunitiesPage

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class OpportunityDashboardPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    ADD_WORKER_ICON = locators.get("opportunity_dashboard_page", "add_worker_icon")
    INVITE_USERS_INPUT = locators.get("opportunity_dashboard_page", "invite_users_input")
    SUBMIT_BUTTON = locators.get("connect_opportunities_page", "submit_button")
    START_DATE_TEXT = locators.get("opportunity_dashboard_page", "start_date_text")
    END_DATE_TEXT = locators.get("opportunity_dashboard_page", "end_date_text")
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page","dashboard_card")
    PROGRESS_FUNNEL = locators.get("opportunity_dashboard_page", "progress_funnel")
    TAB_ITEM_BY_NAME = locators.get("opportunity_dashboard_page", "tab_items")
    HAMBURGER_ICON = locators.get("opportunity_dashboard_page", "hamburger_icon")
    HAMBURGER_CONTEXT_MENU = locators.get("opportunity_dashboard_page", "hamburger_context_menu")
    TABLE_ELEMENT = locators.get("opportunity_dashboard_page", "table_element")


    def click_dashboard_card_in_opportunity(self, title, subtitle):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        self.scroll_into_view((by, actual_xpath))
        self.click_element((by, actual_xpath))
        time.sleep(2)

    def click_add_worker_icon(self):
        self.click_element(self.ADD_WORKER_ICON)
        self.verify_text_in_url("user_invite")

    def enter_invite_users_in_opportunity(self, num_list):
        input_element = self.wait_for_element(self.INVITE_USERS_INPUT)
        for each in num_list:
            input_element.send_keys(each)
            input_element.send_keys(Keys.ENTER)

    def click_submit_btn(self):
        self.scroll_into_view(self.SUBMIT_BUTTON)
        self.click_element(self.SUBMIT_BUTTON)

    def enter_users_and_submit_in_opportunity(self, num_list):
        self.enter_invite_users_in_opportunity(num_list)
        time.sleep(2)
        self.click_submit_btn()

    def verify_start_date_card_value_present(self):
        element = self.wait_for_element(self.START_DATE_TEXT)
        value = element.text.strip()
        print(f"Start date in Opportunity Dashboard --> {value}")
        assert value != "", "Start Date card value is empty in Opportunity Dashboard"

    def verify_end_date_card_value_present(self):
        element = self.wait_for_element(self.END_DATE_TEXT)
        value = element.text.strip()
        print(f"End date in Opportunity Dashboard --> {value}")
        assert value != "", "Start Date card value is empty in Opportunity Dashboard"

    def verify_dashboard_card_details_present(self, title, subtitle):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        self.scroll_into_view((by, actual_xpath))
        card = self.wait_for_element((by, actual_xpath))
        count = card.find_element(By.XPATH, ".//h3[contains(@class,'text-2xl')]").text.strip()
        assert count != "", f"{title} {subtitle} count is empty"
        print(f"{title} {subtitle} in Opportunity Dashboard --> {count}")

    def verify_progress_funnel_present(self):
        self.scroll_into_view(self.PROGRESS_FUNNEL)
        self.wait_for_element(self.PROGRESS_FUNNEL).is_displayed()

    def click_invite_workers_to_opportunity(self):
        self.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        self.is_breadcrumb_item_present("Connect Workers")
        self.click_add_worker_icon()

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.is_breadcrumb_item_present(data["opportunity_name"])
        self.verify_start_date_card_value_present()
        self.verify_end_date_card_value_present()
        self.verify_dashboard_card_details_present("Connect Workers", "Invited")
        self.verify_dashboard_card_details_present("Connect Workers", "Yet to Accept Invitation")
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("Services Delivered", "Pending NM Review")
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")
        self.verify_progress_funnel_present()

    def nav_to_add_worker(self, opp):
        self.click_link_by_text(opp)
        self.click_dashboard_card_in_opportunity("Connect Workers", "Invited")
        self.is_breadcrumb_item_present("Connect Workers")
        self.click_add_worker_icon()

    def click_tab_by_name(self, tab_name):
        by, xpath_template = self.TAB_ITEM_BY_NAME
        xpath = xpath_template.format(tab_name=tab_name)
        tab = self.wait_for_element((by, xpath))
        self.click_element(tab)
        time.sleep(1)
        self.verify_tab_is_active(tab_name)

    def verify_tab_is_active(self, tab_name):
        by, xpath = self.TAB_ITEM_BY_NAME
        actual_xpath = xpath.format(tab_name=tab_name)
        tab = self.wait_until_class_present((by, actual_xpath), "active")
        class_items = tab.get_attribute("class")
        assert "active" in class_items, f"Tab '{tab_name}' is not active"

    def click_hamburger_icon(self):
        self.click_element(self.HAMBURGER_ICON)

    def verify_hamburger_menu_items_present(self, expected_items):
        menu = self.wait_for_element(self.HAMBURGER_CONTEXT_MENU)
        menu_texts = [
            el.text.strip()
            for el in menu.find_elements(By.XPATH, ".//a[normalize-space()]")
            if el.text.strip()
        ]
        missing_items = [item for item in expected_items if item not in menu_texts]
        assert not missing_items, (f"Missing menu items: {missing_items}. "f"Available items: {menu_texts}")
        print(f"All menu items are present: {expected_items}")

    def click_and_verify_hamburger_menu_items_present(self, expected_items):
        self.click_hamburger_icon()
        self.verify_hamburger_menu_items_present(expected_items)

    def select_hamburger_menu_item(self, value: str):
        menu = self.wait_for_element(self.HAMBURGER_CONTEXT_MENU)
        elements = menu.find_elements(By.XPATH, ".//a[normalize-space()]")
        for each in elements:
            if each.text.strip() == value:
                self.click_element(each)
                if not self.is_breadcrumb_item_present(value):
                    raise AssertionError(f"Breadcrumb for '{value}' not found after clicking menu item.")
                return
        else:
            raise ValueError(f"Hamburger menu item '{value}' not found.")

    def verify_table_element_present(self):
        element = self.wait_for_element(self.TABLE_ELEMENT)
        assert element.is_displayed(), "Table element is present"
