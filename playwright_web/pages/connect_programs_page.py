from datetime import datetime

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class ConnectProgramsPage(BasePage):
    CREATE_OPPORTUNITY_LINK_BY_NETWORK_MANAGER = locators.get(
        "connect_programs_page", "create_opportunity_link_by_network_manager"
    )
    ADD_PROGRAM_BUTTON = locators.get("connect_programs_page", "add_program_btn")
    PROGRAM_ADD_FORM = locators.get("connect_programs_page", "program_add_form")
    PROGRAM_NAME_INPUT = locators.get("connect_programs_page", "program_name_input")
    PROGRAM_DESCRIPTION_INPUT = locators.get("connect_programs_page", "program_description_input")
    PROGRAM_DELIVERY_TYPE_DROPDOWN = locators.get("connect_programs_page", "program_delivery_type_dropdown")
    PROGRAM_BUDGET_INPUT = locators.get("connect_programs_page", "program_budget_input")
    PROGRAM_CURRENCY_DROPDOWN = locators.get("connect_programs_page", "program_currency_dropdown")
    PROGRAM_COUNTRY_DROPDOWN = locators.get("connect_programs_page", "program_country_dropdown")
    PROGRAM_START_DATE_INPUT = locators.get("connect_programs_page", "program_start_date_input")
    PROGRAM_END_DATE_INPUT = locators.get("connect_programs_page", "program_end_date_input")
    PROGRAM_SUBMIT_BUTTON = locators.get("connect_programs_page", "program_submit_btn")
    PROGRAM_CARD_BY_NAME = locators.get("connect_programs_page", "program_card_by_name")
    INVITE_BTN_BY_PROGRAM = locators.get("connect_programs_page", "invite_btn_by_program")
    INVITE_ORG_SELECT_BY_PROGRAM = locators.get("connect_programs_page", "invite_org_select_by_program")
    INVITE_SUBMIT_BTN_BY_PROGRAM = locators.get("connect_programs_page", "invite_submit_btn_by_program")
    APPLY_TO_PROGRAM_BTN_BY_PROGRAM = locators.get("connect_programs_page", "apply_to_program_btn_by_program")
    ACCEPT_APPLICATION_BTN_BY_PROGRAM = locators.get("connect_programs_page", "accept_application_btn_by_program")
    VIEW_STATUS_BTN_BY_PROGRAM = locators.get("connect_programs_page", "view_status_btn_by_program")

    def create_program(self, data):
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        program_name = f"{data['program_name']}_{timestamp}"

        self.click(self.ADD_PROGRAM_BUTTON)
        self.page.locator(self.PROGRAM_NAME_INPUT).first.wait_for(state="visible")
        self.page.locator(self.PROGRAM_NAME_INPUT).first.fill(program_name)
        self.page.locator(self.PROGRAM_DESCRIPTION_INPUT).first.fill(data["program_description"])
        # Case-insensitive: staging lists this delivery type as "Wellme", prod as
        # "WellMe", and one test-data value has to satisfy both.
        self.select_by_visible_text_ci(self.PROGRAM_DELIVERY_TYPE_DROPDOWN, data["delivery_type"])
        self.page.locator(self.PROGRAM_BUDGET_INPUT).first.fill(data["program_budget"])
        self.select_by_visible_text_forced(self.PROGRAM_CURRENCY_DROPDOWN, data["currency"])
        self.select_by_visible_text_forced(self.PROGRAM_COUNTRY_DROPDOWN, data["country"])
        start, end = self.generate_date_range(365)
        self.enter_date(self.PROGRAM_START_DATE_INPUT, start)
        self.enter_date(self.PROGRAM_END_DATE_INPUT, end)
        self.click(self.PROGRAM_SUBMIT_BUTTON)

        self.verify_program_present(program_name)
        return program_name

    def verify_program_present(self, program_name):
        """Find a program's card, reporting what was on the page if it is not there.

        Known failing on staging as of 04-Aug-2026: the program IS created, but its
        card never appears. Programs cannot be deleted, so the list only grows, and
        the likely cause is that the newest one is no longer on the first page -
        unlike the opportunities list, this page offers no page-size control to
        widen, so it needs a different fix (pagination or a filter). Until then the
        failure at least says what it did see, instead of a bare 30s timeout.
        """
        card = self.page.locator(self.PROGRAM_CARD_BY_NAME.format(program=program_name)).first
        try:
            card.wait_for(state="visible", timeout=30000)
        except Exception:
            visible = [
                text.strip().splitlines()[0]
                for text in self.page.locator(self.PROGRAM_CARD_BY_NAME.format(program="")).all_inner_texts()
                if text.strip()
            ]
            raise AssertionError(
                f"Program '{program_name}' was created but its card is not on the page. "
                f"{len(visible)} card(s) visible: {visible[:10]}"
            ) from None

    def invite_network_manager(self, program_name, network_manager):
        self.click(self.INVITE_BTN_BY_PROGRAM.format(program=program_name))
        org_select = self.INVITE_ORG_SELECT_BY_PROGRAM.format(program=program_name)
        self.page.locator(org_select).first.wait_for(state="attached")
        self.select_by_visible_text_forced(org_select, network_manager)
        self.click(self.INVITE_SUBMIT_BTN_BY_PROGRAM.format(program=program_name))
        self.page.wait_for_load_state("networkidle")
        self.page.wait_for_timeout(2000)

    def apply_to_program(self, program_name):
        self.click(self.APPLY_TO_PROGRAM_BTN_BY_PROGRAM.format(program=program_name))
        self.page.wait_for_timeout(3000)

    def accept_application(self, program_name, network_manager):
        self.click(self.VIEW_STATUS_BTN_BY_PROGRAM.format(program=program_name))
        accept_btn = self.ACCEPT_APPLICATION_BTN_BY_PROGRAM.format(program=program_name)
        self.page.locator(accept_btn).first.wait_for(state="visible")
        self.click(accept_btn)
        self.page.wait_for_timeout(3000)

    def open_create_opportunity_form(self, program_name, network_manager):
        self.click(self.VIEW_STATUS_BTN_BY_PROGRAM.format(program=program_name))
        create_opportunity_link = self.CREATE_OPPORTUNITY_LINK_BY_NETWORK_MANAGER.format(
            network_manager=network_manager
        )
        self.page.locator(create_opportunity_link).first.wait_for(state="visible")
        self.click(create_opportunity_link)
        self.page.wait_for_url("**/opportunity-init")
