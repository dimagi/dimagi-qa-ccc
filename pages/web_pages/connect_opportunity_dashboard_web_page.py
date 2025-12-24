import time
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


    def click_dashboard_card_in_opportunity(self, title, subtitle):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        self.scroll_into_view((by, actual_xpath))
        self.click_element((by, actual_xpath))

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

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.click_link_by_text(data["opportunity_name"])
        self.verify_dashboard_card_details_present("Connect Workers", "Invited")
        self.verify_dashboard_card_details_present("Connect Workers", "Yet to Accept Invitation")
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("Services Delivered", "Pending NM Review")
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")

    def navigate_to_connect_workers(self, opp):
        self.click_link_by_text(opp)
        self.click_dashboard_card_in_opportunity("Connect Workers", "Invited")

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
