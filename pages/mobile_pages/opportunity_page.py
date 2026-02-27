import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class OpportunityPage(BasePage):
    
    JOB_TITLE_TXT = locators.get("opportunity_page", "job_title_txt")
    JOB_DESCRIPTION_TXT = locators.get("opportunity_page", "job_description_txt")
    VIEW_MORE_BTN = locators.get("opportunity_page", "view_more_btn")
    JOB_END_DATE_TXT = locators.get("opportunity_page", "job_end_date_txt")

    DELIVERY_DETAILS_REVIEW_TXT = locators.get("opportunity_page", "delivery_details_review_txt")
    TOTAL_VISIT_TXT = locators.get("opportunity_page", "total_visit_txt")
    DELIVERY_DAYS_TXT = locators.get("opportunity_page", "delivery_days_txt")
    DELIVERY_MAX_DAILY_TXT = locators.get("opportunity_page", "delivery_max_daily_txt")
    DELIVERY_BUDGET_TXT = locators.get("opportunity_page", "delivery_budget_txt")
    CLOSE_DELIVERY_DETAILS_BTN = locators.get("opportunity_page", "close_delivery_details_btn")

    LEARN_DETAILS_TXT = locators.get("opportunity_page", "learn_details_txt")
    LEARN_TITLE_TXT = locators.get("opportunity_page", "learn_title_txt")
    INTRO_LEARNING_MODULE_TXT = locators.get("opportunity_page", "intro_learn_module_txt")
    INTRO_LEARN_SUMMARY_TXT = locators.get("opportunity_page", "intro_learn_summary_txt")
    DOWNLOAD_LEARN_APP_BTN = locators.get("opportunity_page", "download_learn_app_btn")

    OPP_LIST_NEW = locators.get("opportunity_page", "opp_list_new")
    OPP_LIST_IN_PROGRESS = locators.get("opportunity_page", "opp_list_in_progress")
    OPP_LIST_COMPLETE = locators.get("opportunity_page", "opp_list_complete")

    OPP_LIST_CARD = locators.get("opportunity_page", "opp_list_card")
    OPP_LIST_TITLE = locators.get("opportunity_page", "opp_list_title")
    OPP_LIST_DATE = locators.get("opportunity_page", "opp_list_date")
    OPP_LIST_TYPE = locators.get("opportunity_page", "opp_list_type")
    OPP_LIST_JOB_TYPE = locators.get("opportunity_page", "opp_list_job_type")
    OPP_LIST_RESUME = locators.get("opportunity_page", "opp_list_resume")
    OPP_LIST_REVIEW = locators.get("opportunity_page", "opp_list_review")
    OPP_LIST_VIEW_INFO = locators.get("opportunity_page", "opp_list_view_info")

    APP_DOWNLOAD_PROGRESS = locators.get("opportunity_page", "download_learn_app_progress_bar")
    LEARN_APP_START_BTN = locators.get("learn_app_page", "learn_app_start_btn")
    SYNC_BTN = locators.get("opportunity_page", "sync_btn")
    NOTIFICATION_BTN = locators.get("opportunity_page", "notification_btn")



    def verify_job_card(self):
        self.click_element(self.SYNC_BTN)
        time.sleep(5)
        menu_items = [
            self.JOB_TITLE_TXT,
            self.JOB_DESCRIPTION_TXT,
            self.VIEW_MORE_BTN,
            self.JOB_END_DATE_TXT
        ]

        for item in menu_items:
            assert self.is_displayed(item), f"Job Card details not visible: {item}"

    def verify_delivery_details(self):
        self.click_element(self.VIEW_MORE_BTN)
        menu_items = [
            self.DELIVERY_DETAILS_REVIEW_TXT,
            self.TOTAL_VISIT_TXT,
            self.DELIVERY_DAYS_TXT,
            self.DELIVERY_MAX_DAILY_TXT,
            self.DELIVERY_BUDGET_TXT
        ]

        for item in menu_items:
            assert self.is_displayed(item), f"Delivery details not visible: {item}"

        self.click_element(self.CLOSE_DELIVERY_DETAILS_BTN)

    def verify_learn_details(self):
        menu_items = [
            self.LEARN_DETAILS_TXT,
            self.LEARN_TITLE_TXT,
            self.INTRO_LEARN_SUMMARY_TXT,
            self.INTRO_LEARNING_MODULE_TXT,
            self.DOWNLOAD_LEARN_APP_BTN
        ]

        for item in menu_items:
            assert self.is_displayed(item), f"Learn details not visible: {item}"

    # def verify_opportunity_list(self):
    #     time.sleep(2)
    #     cards = self.get_elements(self.OPP_LIST_CARD)
    #     assert len(cards) > 0, "No opportunities found"
    #     print(f"No of opportunity present {len(cards)}")
    #     time.sleep(2)
    #     for card in cards:
    #         try:
    #             name = card.find_element(*self.OPP_LIST_TITLE).text
    #             print(name)
    #             # opp_type = card.find_element(*self.OPP_LIST_TYPE).is_displayed()
    #             date = card.find_element(*self.OPP_LIST_DATE).text
    #             print(date)
    #             assert name, "Opportunity name missing"
    #             # assert opp_type, "Opportunity type missing"
    #             assert date, "Opportunity date missing"
    #         except:
    #             self.scroll_to_end()
    #             name = card.find_element(*self.OPP_LIST_TITLE).text
    #             print(name)
    #             # opp_type = card.find_element(*self.OPP_LIST_TYPE).is_displayed()
    #             date = card.find_element(*self.OPP_LIST_DATE).text
    #             print(date)
    #             assert name, "Opportunity name missing"
    #             # assert opp_type, "Opportunity type missing"
    #             assert date, "Opportunity date missing"

    def verify_opportunity_list(self):
        time.sleep(2)

        seen = set()
        max_scrolls = 5

        for _ in range(max_scrolls):

            cards = self.get_elements(self.OPP_LIST_CARD)

            for card in cards:
                try:
                    name = card.find_element(*self.OPP_LIST_TITLE).text
                    date = card.find_element(*self.OPP_LIST_DATE).text

                    if name not in seen:
                        print(name)
                        print(date)

                        assert name, "Opportunity name missing"
                        assert date, "Opportunity date missing"

                        seen.add(name)

                except Exception:
                    continue

            # Scroll after processing visible items
            self.scroll_down()

        print(f"Total unique opportunities found: {len(seen)}")

    def download_learn_app(self):
        self.wait_for_element(self.DOWNLOAD_LEARN_APP_BTN)
        self.click_element(self.DOWNLOAD_LEARN_APP_BTN)
        self.wait_for_element_to_disappear(self.APP_DOWNLOAD_PROGRESS)
        time.sleep(10)
        assert self.is_displayed(self.LEARN_APP_START_BTN), "Start button is not visible"
        print("Download completed. Start button is visible")

    # def open_opportunity_from_list(self, opp_name, opp_status):
        # self.click_element(self.SYNC_BTN)
        # time.sleep(1)
        # # Iterate
        # rows = self.get_elements(self.OPP_LIST_CARD)
        # for row in rows:
        #     name = row.find_element(*self.OPP_LIST_TITLE).text.strip().lower()
        #     status = row.find_element(*self.OPP_LIST_JOB_TYPE).text.strip().lower()
        #     if name == opp_name.lower() and status == opp_status:
        #         print(f"Opportunity found: {name}, [{status}]")
        #         row.click()
        #         time.sleep(15)
        #         # assert self.is_displayed(self.LEARN_APP_START_BTN), "App not opened"
        #         break
    def open_opportunity_from_list(self, opp_name, opp_status):
        if self.is_present(self.JOB_TITLE_TXT):
            print("Opportunity is already opened")
        else:
            self.click_element(self.SYNC_BTN)
            time.sleep(10)

            max_scrolls = 10
            scroll_count = 0

            while scroll_count < max_scrolls:
                rows = self.get_elements(self.OPP_LIST_CARD)

                for row in rows:
                    try:
                        name = row.find_element(*self.OPP_LIST_TITLE).text.strip()

                        if str(opp_status).lower() == "delivery":
                            status = row.find_element(*self.OPP_LIST_RESUME)
                            button_name = row.find_element(*self.OPP_LIST_RESUME).text.strip()
                        else:
                            status = row.find_element(*self.OPP_LIST_REVIEW)
                            button_name = row.find_element(*self.OPP_LIST_REVIEW).text.strip()
                        print(name, button_name)
                        if name == opp_name :
                            print(f"Opportunity found: {name}, [{button_name}]")
                            status.click()
                            time.sleep(5)
                            if button_name.lower()=="resume" :
                                try:
                                    self.download_learn_app()
                                except:
                                    print("No Learn or Delivery app Download button present")
                            return  # stop function immediately

                    except Exception:
                        continue

                # Not found → scroll
                self.scroll_down()
                scroll_count += 1

            raise Exception(f"Opportunity '{opp_name}' with status '{opp_status}' not found after scrolling.")


    def click_notification(self):
        self.wait_for_element(self.NOTIFICATION_BTN)
        self.click_element(self.NOTIFICATION_BTN)




