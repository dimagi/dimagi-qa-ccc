from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class OpportunityDashboardPage(BasePage):
    DASHBOARD_CARD = locators.get("opportunity_dashboard_page", "dashboard_card")

    def verify_dashboard_card_details_present(self, title, subtitle, count_section=True):
        selector = self.DASHBOARD_CARD.format(title=title, subtitle=subtitle)
        self.scroll_into_view(selector)
        card = self.page.locator(selector)
        card.wait_for(state="visible")
        if count_section:
            count = card.locator("xpath=.//h3[contains(@class,'text-2xl')]").inner_text().strip()
            assert count != "", f"{title} {subtitle} count is empty"
            print(f"{title} {subtitle} in Opportunity Dashboard --> {count}")

    def navigate_to_opportunity_and_verify_all_fields_present_in_connect(self, data):
        self.click_link_by_text(data["opportunity_name"])
        self.verify_dashboard_card_details_present("Connect Workers", "", count_section=False)
        self.verify_dashboard_card_details_present("Tasks Assigned to Connect Workers", "")
        self.verify_dashboard_card_details_present("Connect Workers", "Inactive last 3 days")
        self.verify_dashboard_card_details_present("Services Delivered", "Total")
        self.verify_dashboard_card_details_present("View Progress Map", "", count_section=False)
        self.verify_dashboard_card_details_present("Audit Opportunity", "", count_section=False)
        self.verify_dashboard_card_details_present("Payments", "Earned")
        self.verify_dashboard_card_details_present("Payments", "Due")
