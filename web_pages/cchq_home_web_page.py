import time
from selenium.webdriver import Keys
from web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class HomePage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    TITLE_ELE = locators.get("home_page", "welcome_title")

    def verify_home_page_title(self, title):
        assert title in self.get_text(self.TITLE_ELE)

