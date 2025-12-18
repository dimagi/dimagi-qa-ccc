import time
from selenium.common import TimeoutException
from selenium.webdriver import Keys
from selenium.webdriver.support import expected_conditions as EC
from web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class OpportunityDashboardPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    CONNECT_WORKERS_LINK = locators.get("opportunity_dashboard_page", "connect_workers_link")
    ADD_WORKER_ICON = locators.get("opportunity_dashboard_page", "add_worker_icon")

    def click_connect_workers_link(self):
        self.click_element(self.CONNECT_WORKERS_LINK)

    def click_add_worker_icon(self):
        self.click_element(self.ADD_WORKER_ICON)

