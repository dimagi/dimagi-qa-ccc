import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class LearnAppPage(BasePage):

    LEARN_APP_START_BTN = locators.get("learn_app_page", "learn_app_start_btn")
    VIEW_JOB_STATUS_BTN = locators.get("learn_app_page", "view_job_status_btn")
    SURVEYS_BTN = locators.get("learn_app_page", "surveys_btn")
    SURVEY_NAME_BTN = locators.get("learn_app_page", "survey_name_btn")
    FINISH_BTN = locators.get("learn_app_page", "finish_btn")

    LEARNING_STATUS_TXT = locators.get("learn_app_page", "learn_status_txt")
    LEARN_PROGRESS_TXT = locators.get("learn_app_page", "learn_progress_txt")
    CONTINUE_LEARNING_BTN = locators.get("learn_app_page", "continue_learning_btn")
    SCORE_INPUT = locators.get("learn_app_page", "score_input")

    CERT_TITLE_TXT = locators.get("learn_app_page", "cert_title_txt")
    CERT_OPP_NAME_TXT = locators.get("learn_app_page", "cert_opp_name_txt")
    CERT_WORKER_NAME_TXT = locators.get("learn_app_page", "cert_worker_name_txt")
    CERT_COMPLETE_DATE_TXT = locators.get("learn_app_page", "cert_complete_date_txt")
    VIEW_OPP_DETAILS_BTN = locators.get("learn_app_page", "view_opp_details_btn")

    OPP_DETAILS_HEADER_TXT = locators.get("learn_app_page", "opp_details_header_txt")
    DELIVERY_DETAILS_TXT = locators.get("learn_app_page", "delivery_details_txt")
    REVIEW_DELIVERY_DETAILS_TXT = locators.get("learn_app_page", "review_delivery_details_txt")
    START_VISIT_TXT = locators.get("learn_app_page", "start_visit_txt")
    DOWNLOAD_DELIVERY_TXT = locators.get("learn_app_page", "download_delivery_txt")
    DOWNLOAD_DELIVERY_APP_BTN = locators.get("learn_app_page", "download_delivery_app_btn")
    TOTAL_VISIT_TXT = locators.get("opportunity_page", "total_visit_txt")
    DELIVERY_DAYS_TXT = locators.get("opportunity_page", "delivery_days_txt")
    DELIVERY_MAX_DAILY_TXT = locators.get("opportunity_page", "delivery_max_daily_txt")
    DELIVERY_BUDGET_TXT = locators.get("opportunity_page", "delivery_budget_txt")

    def complete_learn_survey(self, survey_name):
        self.wait_for_element(self.LEARN_APP_START_BTN)
        self.click_element(self.LEARN_APP_START_BTN)
        self.click_element(self.SURVEYS_BTN)

        for el in self.get_elements(self.SURVEYS_BTN):
            if survey_name in el.text.lower():
                el.click()
                break
        self.click_element(self.FINISH_BTN)


    def view_in_progress_job_status(self):
        self.wait_for_element(self.VIEW_JOB_STATUS_BTN)
        self.click_element(self.VIEW_JOB_STATUS_BTN)
        assert "Finish learning to earn your certificate." in self.get_text(self.LEARN_APP_START_BTN)
        assert self.is_displayed(self.LEARN_PROGRESS_TXT)
        assert self.get_text(self.CONTINUE_LEARNING_BTN).lower() == "continue learning"

    def view_completed_job_status(self):
        self.wait_for_element(self.VIEW_JOB_STATUS_BTN)
        self.click_element(self.VIEW_JOB_STATUS_BTN)
        assert self.get_text(self.LEARN_APP_START_BTN).lower() == "Complete the assessment to finish training."
        assert self.get_text(self.LEARN_PROGRESS_TXT)== "100%"
        assert self.get_text(self.CONTINUE_LEARNING_BTN).lower() == "go to assessment"

    def complete_assessment(self, passing_score):
        if self.is_displayed(self.CONTINUE_LEARNING_BTN):
            self.click_element(self.CONTINUE_LEARNING_BTN)
        self.wait_for_element(self.LEARN_APP_START_BTN)
        self.click_element(self.LEARN_APP_START_BTN)
        self.click_element(self.SURVEYS_BTN)
        for el in self.get_elements(self.SURVEYS_BTN):
            if "Assesss" in el.text.lower():
                el.click()
                break
        self.type_element(self.SCORE_INPUT, passing_score)
        self.click_element(self.FINISH_BTN)

    def view_failed_assess_job_status(self):
        self.wait_for_element(self.VIEW_JOB_STATUS_BTN)
        self.click_element(self.VIEW_JOB_STATUS_BTN)
        assert self.get_text(self.LEARN_APP_START_BTN).lower() == "Sorry, you did not earn a passing score on your assessment. Please try again.\nYour score: 10\nPassing score: 70"


    def verify_job_status(self, status):
        JOB_STATUS_EXPECTATIONS = {
            "IN_PROGRESS": {
                "start_text": "Finish learning to earn your certificate.",
                "progress": "50%",
                "continue_btn": "continue learning"
            },
            "COMPLETED": {
                "start_text": "Complete the assessment to finish training.",
                "progress": "100%",
                "continue_btn": "go to assessment"
            },
            "FAILED_ASSESSMENT": {
                "start_text": (
                    "Sorry, you did not earn a passing score on your assessment. "
                    "Please try again.\nYour score: 10\nPassing score: 70"
                ),
                "progress": "100%",
                "continue_btn": "go to assessment"
            }
        }

        expected = JOB_STATUS_EXPECTATIONS[status]

        self.wait_for_element(self.VIEW_JOB_STATUS_BTN)
        self.click_element(self.VIEW_JOB_STATUS_BTN)

        # Start / message text
        assert expected["start_text"] in self.get_text(self.LEARN_APP_START_BTN)
        assert self.get_text(self.LEARN_PROGRESS_TXT) == expected["progress"]
        assert self.get_text(self.CONTINUE_LEARNING_BTN).lower() == expected["continue_btn"]

    def verify_certificate_screen(self):
        self.click_element(self.VIEW_JOB_STATUS_BTN)
        elements = [
            self.CERT_TITLE_TXT,
            self.CERT_OPP_NAME_TXT,
            self.CERT_COMPLETE_DATE_TXT,
            self.CERT_WORKER_NAME_TXT,
            self.VIEW_OPP_DETAILS_BTN
        ]

        for name, locator in elements.items():
            assert self.is_displayed(locator), f"{name} is not visible"


    def verify_opportunity_details_screen(self):
        self.click_element(self.VIEW_OPP_DETAILS_BTN)
        elements = [
            self.OPP_DETAILS_HEADER_TXT,
            self.DELIVERY_DETAILS_TXT,
            self.REVIEW_DELIVERY_DETAILS_TXT,
            self.START_VISIT_TXT,
            self.DOWNLOAD_DELIVERY_TXT,
            self.DOWNLOAD_DELIVERY_APP_BTN,
            self.TOTAL_VISIT_TXT,
            self.DELIVERY_DAYS_TXT,
            self.DELIVERY_MAX_DAILY_TXT,
            self.DELIVERY_BUDGET_TXT
        ]

        for name, locator in elements.items():
            assert self.is_displayed(locator), f"{name} is not visible"
