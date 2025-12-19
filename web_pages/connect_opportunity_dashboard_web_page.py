from selenium.webdriver.common.by import By
from web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class OpportunityDashboardPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)


    ADD_WORKER_ICON = locators.get("opportunity_dashboard_page", "add_worker_icon")
    START_DATE_TEXT = locators.get("opportunity_dashboard_page", "start_date_text")
    END_DATE_TEXT = locators.get("opportunity_dashboard_page", "end_date_text")
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page","dashboard_card")
    PROGRESS_FUNNEL = locators.get("opportunity_dashboard_page", "progress_funnel")


    def click_dashboard_card_in_opportunity(self, title, subtitle):
        by, value = self.DASHBOARD_CARD
        actual_xpath = value.format(title=title, subtitle=subtitle)
        self.scroll_into_view((by, actual_xpath))
        self.click_element((by, actual_xpath))

    def click_add_worker_icon(self):
        self.click_element(self.ADD_WORKER_ICON)

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