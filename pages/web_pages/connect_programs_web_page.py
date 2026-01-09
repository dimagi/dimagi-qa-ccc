import time

from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from pages.web_pages.base_web_page import BaseWebPage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/web_locators.yaml", platform="web")

class ConnectProgramsPage(BaseWebPage):

    def __init__(self, driver):
        super().__init__(driver)

    VIEW_STATUS_BUTTON = locators.get("connect_programs_page", "view_status_btn")
    HIDE_STATUS_BUTTON = locators.get("connect_programs_page", "hide_status_btn")
    NMS_INVITE_CARD = locators.get("connect_programs_page", "nms_invite_card")
    NMS_INVITE_CARD_BY_NAME = locators.get("connect_programs_page", "nms_invite_card_by_name")
    PROGRAM_CARD_BY_NAME = locators.get("connect_programs_page", "program_card_by_name")

    def click_view_status_for_program(self, program):
        by, value = self.VIEW_STATUS_BUTTON
        actual_xpath = value.format(program=program)
        self.scroll_into_view((by, actual_xpath))
        self.click_element((by, actual_xpath))

    def click_hide_status_for_program(self, program):
        by, value = self.HIDE_STATUS_BUTTON
        actual_xpath = value.format(program=program)
        self.scroll_into_view((by, actual_xpath))
        self.click_element((by, actual_xpath))

    def verify_status_of_nms_invited(self):
        by, value = self.NMS_INVITE_CARD
        nms = self.find_all_elements((by, value))
        for each in nms:
            self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", each)
            name_ele = each.find_element(By.XPATH, ".//p[@class='card_title']")
            status_ele = each.find_element(By.XPATH, ".//span")
            if name_ele.is_displayed() and status_ele.is_displayed():
                print(f"Network Manager '{name_ele.text}' status is: '{status_ele.text}'")
            else:
                print(f"Network Manager element - Not Found")
                raise NoSuchElementException()

    def verify_info_card_details_present(self, program):
        by, value = self.PROGRAM_CARD_BY_NAME
        actual_xpath = value.format(program=program)
        program_ele = self.wait_for_element((by, actual_xpath))
        cards = program_ele.find_elements(By.XPATH, ".//div[contains(@class, 'infocard-dark')]")
        for card in cards:
            if card.is_displayed():
                h6_text = card.find_element(By.TAG_NAME, "h6").text
                p_text = card.find_element(By.TAG_NAME, "p").text
                print(f"{h6_text}: {p_text}")
            else:
                raise NoSuchElementException

    def verify_program_info_present_for_a_program(self, program):
        self.click_view_status_for_program(program)
        time.sleep(1)
        self.verify_info_card_details_present(program)

    def navigate_n_verify_status_for_nms_in_program(self, program):
        self.verify_status_of_nms_invited()
        time.sleep(2)
        self.click_hide_status_for_program(program)

    def verify_create_opportunity_in_accepted_nm_in_program(self, program, network_manager):
        self.click_view_status_for_program(program)
        by, value = self.NMS_INVITE_CARD_BY_NAME
        actual_xpath = value.format(network_manager=network_manager)
        nm_card = self.wait_for_element((by, actual_xpath))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nm_card)
        status_ele = nm_card.find_element(By.XPATH, ".//span")
        create_opp = nm_card.find_element(By.XPATH, ".//p[contains(text(), 'Create Opportunity')]")
        if status_ele.text.strip() == "Accepted":
            print(f"Network Manager '{network_manager}' status is: Accepted")
            create_opp.click()
            time.sleep(2)
            self.verify_text_in_url("opportunity-init")
            self.navigate_backward()
        else:
            print(f"Network Manager or Status element - Not Found")
            raise NoSuchElementException()

    def verify_view_opportunities_in_accepted_nm_in_program(self, program, network_manager):
        # self.click_view_status_for_program(program)
        by, value = self.NMS_INVITE_CARD_BY_NAME
        actual_xpath = value.format(network_manager=network_manager)
        nm_card = self.wait_for_element((by, actual_xpath))
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", nm_card)
        status_ele = nm_card.find_element(By.XPATH, ".//span")
        view_opp = nm_card.find_element(By.XPATH, ".//p[contains(text(), 'View Opportunities')]")
        if status_ele.text.strip() == "Accepted":
            print(f"Network Manager '{network_manager}' status is: Accepted")
            view_opp.click()
            time.sleep(2)
            self.verify_text_in_url("/opportunity/")
            self.navigate_backward()
        else:
            print(f"Network Manager or Status element - Not Found")
            raise NoSuchElementException()