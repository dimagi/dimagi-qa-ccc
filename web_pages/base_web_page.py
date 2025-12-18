from selenium.common import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys

class BaseWebPage:
    def __init__(self, driver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 30)

    def find(self, locator):
        return self.driver.find_element(*locator)

    def click(self, locator):
        self.find(locator).click()

    def type(self, locator, text):
        el = self.find(locator)
        el.clear()
        el.send_keys(text)

    def wait_for_element(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def wait_for_clickable(self, locator):
        return self.wait.until(EC.element_to_be_clickable(locator))

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

    def switch_to_latest_tab(self):
        self.driver.switch_to.window(self.driver.window_handles[-1])

    def switch_to_first_tab(self):
        self.driver.switch_to.window(self.driver.window_handles[0])

    def open_url_in_new_tab(self, url: str):
        self.driver.execute_script(f"window.open('{url}', '_blank');")
        self.switch_to_latest_tab()

    def select_by_visible_text(self, dropdown_locator, text):
        element = self.wait.until(EC.presence_of_element_located(dropdown_locator))
        Select(element).select_by_visible_text(text)

    def scroll_to_top(self):
        self.driver.execute_script("window.scrollTo(0, 0);")

    def scroll_to_bottom(self):
        self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    def scroll_into_view(self, locator, center=True):
        element = self.wait.until(EC.presence_of_element_located(locator))
        if center:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        else:
            self.driver.execute_script("arguments[0].scrollIntoView(true);",element)

    def scroll_until_element_visible(self, locator, max_scrolls=10):
        for _ in range(max_scrolls):
            try:
                element = self.find(*locator)
                if element.is_displayed():
                    return element
            except:
                pass
            self.driver.execute_script("window.scrollBy(arguments[0], arguments[1]);", 0, 500)
        raise TimeoutError("Element not visible after scrolling")

    def click_link_by_text(self, link_text: str):
        xpath = f"//a[normalize-space()='{link_text}']"
        element = self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath))).click()

    def is_breadcrumb_item_present(self, text: str) -> bool:
        xpath = f"//ul[contains(@class,'breadcrumb')]//a[normalize-space()='{text}']"
        try:
            self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
            return True
        except TimeoutException:
            return False

    def verify_text_in_url(self, expected_text: str, timeout: int = 10):
        WebDriverWait(self.driver, timeout).until(lambda driver: expected_text in driver.current_url)
        assert expected_text in self.driver.current_url, (
            f"Expected '{expected_text}' to be in URL, "
            f"but actual URL is '{self.driver.current_url}'"
        )

    def enter_date(self, locator, date_value: str):
        element = self.wait.until(EC.visibility_of_element_located(locator))
        try:
            #element.clear()
            element.send_keys(date_value)
        except Exception:
            self.driver.execute_script(
                "arguments[0].value = arguments[1];"
                "arguments[0].dispatchEvent(new Event('change'));",
                element,
                date_value
            )

