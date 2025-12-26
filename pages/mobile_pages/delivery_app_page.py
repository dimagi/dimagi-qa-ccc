from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class DeliveryAppPage(BasePage):

    DELIVERY_APP_HEADER_TXT = locators.get("delivery_app_page", "delivery_app_header_txt")
