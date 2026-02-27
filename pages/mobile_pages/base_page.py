import os
import time

from appium.webdriver.common.appiumby import AppiumBy
from selenium.common import NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

class BasePage:
    BIOMETRIC_ENABLED = os.getenv("BIOMETRIC_ENABLED", "false").lower() == "true"

    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 60)

    def wait_for_element(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def click_element(self, locator):
        self.wait.until(EC.element_to_be_clickable(locator)).click()

    def type_element(self, locator, text):
        el = self.wait.until(EC.visibility_of_element_located(locator))
        el.clear()
        el.send_keys(text)

    def click_when_enabled(self, locator):
        self.wait.until(lambda d: d.find_element(*locator).is_enabled())
        self.driver.find_element(*locator).click()

    def get_text(self, locator):
        return self.wait.until(
            EC.visibility_of_element_located(locator)
        ).text

    def is_displayed(self, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.visibility_of_element_located(locator)
            )
            return True
        except:
            return False

    def is_present(self, locator, timeout=10):
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(*locator)
            )
            return True
        except:
            return False

    def get_elements(self, locator, timeout=10):
        return self.wait.until(EC.presence_of_all_elements_located(locator))

    def navigate_back(self):
        self.driver.back()

    def wait_for_element_to_disappear(self, locator):
        return self.wait.until(EC.invisibility_of_element(locator))

    def tap_element(self, locator):
        element = self.wait_for_element(locator)
        loc = element.location
        size = element.size

        x = loc["x"] + size["width"] // 2
        y = loc["y"] + size["height"] // 2

        finger = PointerInput("touch", "finger")
        actions = ActionBuilder(self.driver, mouse=finger)

        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pointer_up()

        actions.perform()

    def scroll_to_end(self):
        actions = ActionChains(self.driver)
        finger = PointerInput("touch", "finger")
        actions.w3c_actions = ActionBuilder(self.driver, mouse=finger)

        size = self.driver.get_window_size()
        start_x = size["width"] * 0.5
        start_y = size["height"] * 0.8
        end_y   = size["height"] * 0.2

        actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(start_x, end_y)
        actions.w3c_actions.pointer_action.release()
        actions.perform()

    def get_elements_if_present(self, locator):
        return self.driver.find_elements(*locator)

    def scroll_down(self):
        size = self.driver.get_window_size()
        start_y = int(size['height'] * 0.8)
        end_y = int(size['height'] * 0.3)
        x = int(size['width'] / 2)

        self.driver.swipe(x, start_y, x, end_y, 800)

    def scroll_to_element(self, locator, max_swipes=5):
        for _ in range(max_swipes):
            try:
                element = self.driver.find_element(*locator)
                return element
            except NoSuchElementException:
                self.driver.find_element(
                    AppiumBy.ANDROID_UIAUTOMATOR,
                    'new UiScrollable(new UiSelector().scrollable(true)).scrollForward()'
                    )
        raise NoSuchElementException(f"Element {locator} not found after scrolling")

    def scroll_to_text(self, text):
        return self.driver.find_element(
            AppiumBy.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().text("{text}"));'
            )