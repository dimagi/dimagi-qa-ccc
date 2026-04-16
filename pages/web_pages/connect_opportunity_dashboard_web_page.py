import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader
from selenium.webdriver.common.keys import Keys

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class OpportunityDashboardPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    START_DATE_TEXT = locators.get("opportunity_dashboard_page", "start_date_text")
    END_DATE_TEXT = locators.get("opportunity_dashboard_page", "end_date_text")
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page","dashboard_card")
    PROGRESS_FUNNEL = locators.get("opportunity_dashboard_page", "progress_funnel")
    HAMBURGER_ICON = locators.get("opportunity_dashboard_page", "hamburger_icon")
    HAMBURGER_CONTEXT_MENU = locators.get("opportunity_dashboard_page", "hamburger_menu")
    PAGE_SIZE = locators.get("connect_opportunities_page", "page_size")
    LEFT_ARROW = locators.get("connect_opportunities_page", "left_arrow")
    RIGHT_ARROW = locators.get("connect_opportunities_page", "right_arrow")
    PAGE_INPUT = locators.get("connect_opportunities_page", "page_input")

    def click_dashboard_card_in_opportunity(self, title, subtitle):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        print(by, actual_xpath)
        self.scroll_to_element((by, actual_xpath))
        time.sleep(1)
        self.js_click((by, actual_xpath))
        time.sleep(3)

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

    def verify_dashboard_card_details_present(self, title, subtitle, count_section=True):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        print(by, actual_xpath)
        self.scroll_to_element((by, actual_xpath))
        card = self.wait_for_element((by, actual_xpath))
        if count_section:
            count = card.find_element(By.XPATH, ".//h3[contains(@class,'text-2xl')]").text.strip()
            assert count != "", f"{title} {subtitle} count is empty"
            print(f"{title} {subtitle} in Opportunity Dashboard --> {count}")

    def verify_progress_funnel_present(self):
        self.scroll_to_element(self.PROGRESS_FUNNEL)
        self.wait_for_element(self.PROGRESS_FUNNEL).is_displayed()

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.click_link_by_text(data["opportunity_name"])
        self.verify_dashboard_card_details_present("Connect Workers", '', count_section=False)
        self.verify_dashboard_card_details_present("Tasks Assigned to Connect Workers", '')
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("View Progress Map", "", count_section=False)
        self.verify_dashboard_card_details_present("Audit Opportunity", "", count_section=False)
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")


    def _find_and_click_opp_in_table(self, opp):
        """Scan all //tr//td/a links on the current page. If opp is found, scroll to it
        inside the inner container and click. Returns True if clicked, False if not found."""
        links = self.driver.find_elements(By.XPATH, "//tr//td//a")
        print(f"Links found on page: {len(links)}")
        for link in links:
            if opp in link.text:
                print(f"Found opportunity: {link.text.strip()}")
                self.driver.execute_script(
                    "arguments[0].scrollIntoView({block:'center', inline:'nearest'});", link
                )
                time.sleep(1)
                self.driver.execute_script("arguments[0].click();", link)
                self.wait_for_page_load()
                time.sleep(2)
                return True
        return False

    def _navigate_to_opp_in_table(self, opp):
        """Page through the opportunities table until opp is found and clicked."""
        time.sleep(5)
        try:
            self.select_by_value(self.PAGE_SIZE, "100")
            time.sleep(5)
            self.wait_for_page_to_load()
        except:
            print("Dropdown not present")
        while True:
            if self._find_and_click_opp_in_table(opp):
                return
            print(f"'{opp}' not on this page, going to next page")
            self.click(self.RIGHT_ARROW)
            time.sleep(5)
            self.wait_for_page_to_load()

    def navigate_to_connect_workers(self, opp):
        self._navigate_to_opp_in_table(opp)
        self.click_dashboard_card_in_opportunity("Connect Workers", '')
        self.verify_text_in_url("workers")
        time.sleep(1)

    def navigate_to_services_delivered(self, opp):
        self._navigate_to_opp_in_table(opp)
        self.click_dashboard_card_in_opportunity("Services Delivered", "Total")
        self.verify_text_in_url("workers/deliver")
        time.sleep(1)

    def navigate_to_payments_earned(self, opp):
        self._navigate_to_opp_in_table(opp)
        time.sleep(2)
        self.click_dashboard_card_in_opportunity("Payments", "Earned")
        self.verify_text_in_url("workers/payments")
        time.sleep(1)

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

    def verify_hamburger_menu_items_present_in_opportunity(self):
        self.click_hamburger_icon()
        time.sleep(1)
        self.verify_hamburger_menu_items_present(["Edit Opportunity", "Add Payment Unit", "Catchment Areas", "Add Connect Workers", "Add Budget", "Verification Flags", "Send Message"])

    def select_hamburger_menu_item(self, value: str):
        self.click_hamburger_icon()
        menu = self.wait_for_element(self.HAMBURGER_CONTEXT_MENU)
        elements = menu.find_elements(By.XPATH, ".//a[normalize-space()]")
        for each in elements:
            if each.text.strip() == value:
                self.click_element(each)
                break
        else:
            raise ValueError(f"Hamburger menu item '{value}' not found.")

