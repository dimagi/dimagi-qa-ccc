from datetime import datetime

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()


class ConnectOpportunitiesPage(BasePage):
    OPP_NAME_INPUT = locators.get("connect_opportunities_page", "name_input")
    OPP_CURRENCY_INPUT = locators.get("connect_opportunities_page", "currency_input")
    OPP_COUNTRY_INPUT = locators.get("connect_opportunities_page", "country_input")
    OPP_SHORT_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "short_description_input")
    OPP_HQ_SERVER_DROPDOWN = locators.get("connect_opportunities_page", "hq_server_dropdown")
    OPP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "description_input")
    OPP_API_KEY_DROPDOWN = locators.get("connect_opportunities_page", "api_key_dropdown")
    OPP_LEARN_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_domain_dropdown")
    OPP_DELIVER_APP_DOMAIN_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_domain_dropdown")
    OPP_LEARN_APP_DROPDOWN = locators.get("connect_opportunities_page", "learn_app_dropdown")
    OPP_DELIVER_APP_DROPDOWN = locators.get("connect_opportunities_page", "deliver_app_dropdown")
    OPP_LEARN_APP_DESCRIPTION_INPUT = locators.get("connect_opportunities_page", "learn_app_description")
    OPP_LEARN_APP_PASSING_SCORE_INPUT = locators.get("connect_opportunities_page", "learn_app_passing_score_input")
    SUBMIT_BUTTON = locators.get("connect_opportunities_page", "submit_button")

    ADD_PAYMENT_UNIT_BUTTON = locators.get("connect_opportunities_page", "add_payment_btn")
    AMOUNT_INPUT = locators.get("connect_opportunities_page", "amount_input")
    MAX_TOTAL_INPUT = locators.get("connect_opportunities_page", "max_total_input")
    MAX_DAILY_INPUT = locators.get("connect_opportunities_page", "max_daily_input")
    START_DATE_INPUT = locators.get("connect_opportunities_page", "start_date_input")
    END_DATE_INPUT = locators.get("connect_opportunities_page", "end_date_input")
    REQUIRED_DELIVER_UNITS_SECTION = locators.get("connect_opportunities_page", "required_delivery_section")
    PAYMENT_UNITS_TABLE = locators.get("connect_opportunities_page", "payment_units_table")
    MAX_CONNECT_WORKERS_INPUT = locators.get("connect_opportunities_page", "max_connect_workers")
    SETUP_BUDGET_BUTTON = locators.get("connect_opportunities_page", "setup_budget_btn")
    TOTAL_BUDGET_INPUT = locators.get("connect_opportunities_page", "total_budget_input")
    PAGE_SIZE = locators.get("connect_opportunities_page", "page_size")
    ORGANIZATION_DROPDOWN = locators.get("connect_opportunities_page", "organization_dropdown")

    def __init__(self, page):
        super().__init__(page)
        self.opp_full_name = None

    def enter_name_in_opportunity(self, value):
        timestamp = datetime.now().strftime("%d-%b-%Y : %H:%M")
        self.opp_full_name = f"{value}_{timestamp}"
        self.page.locator(self.OPP_NAME_INPUT).first.fill(self.opp_full_name)
        return self.opp_full_name

    def select_currency_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_CURRENCY_INPUT, value)

    def select_country_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_COUNTRY_INPUT, value)

    def select_network_manager_organization(self, value):
        self.scroll_into_view(self.ORGANIZATION_DROPDOWN)
        self.select_by_visible_text(self.ORGANIZATION_DROPDOWN, value)

    def enter_short_description_in_opportunity(self, value):
        self.page.locator(self.OPP_SHORT_DESCRIPTION_INPUT).first.fill(value)

    def enter_description_in_opportunity(self, value):
        self.page.locator(self.OPP_DESCRIPTION_INPUT).first.fill(value)

    def select_hq_server_in_opportunity(self, value):
        self.select_by_visible_text(self.OPP_HQ_SERVER_DROPDOWN, value)
        self.page.wait_for_timeout(3000)

    def select_api_key_in_opportunity(self, value):
        self.wait_for_select_options_loaded(self.OPP_API_KEY_DROPDOWN)
        self.select_by_visible_text(self.OPP_API_KEY_DROPDOWN, value)

    def select_learn_app_domain_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DOMAIN_DROPDOWN, value)

    def select_deliver_app_domain_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DOMAIN_DROPDOWN, value)

    def select_learn_app_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_DROPDOWN)
        self.wait_for_select_options_loaded(self.OPP_LEARN_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_LEARN_APP_DROPDOWN, value)

    def select_deliver_app_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_DELIVER_APP_DROPDOWN)
        self.wait_for_select_options_loaded(self.OPP_DELIVER_APP_DROPDOWN)
        self.select_by_visible_text(self.OPP_DELIVER_APP_DROPDOWN, value)

    def enter_learn_app_description_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_DESCRIPTION_INPUT)
        self.page.locator(self.OPP_LEARN_APP_DESCRIPTION_INPUT).first.fill(value)

    def enter_passing_score_in_opportunity(self, value):
        self.scroll_into_view(self.OPP_LEARN_APP_PASSING_SCORE_INPUT)
        self.page.locator(self.OPP_LEARN_APP_PASSING_SCORE_INPUT).first.fill(value)

    def click_submit_btn(self):
        self.scroll_into_view(self.SUBMIT_BUTTON)
        self.click(self.SUBMIT_BUTTON, force=True)

    def click_add_payment_unit_button(self):
        self.click(self.ADD_PAYMENT_UNIT_BUTTON)
        self.page.wait_for_url("**/payment_units/create**")

    def enter_amount_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.AMOUNT_INPUT).first.fill(value)

    def enter_max_daily_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.MAX_DAILY_INPUT).first.fill(value)

    def enter_max_total_in_payment_unit_of_opportunity(self, value):
        self.page.locator(self.MAX_TOTAL_INPUT).first.fill(value)

    def enter_start_date_in_payment_unit_of_opportunity(self, value):
        self.scroll_into_view(self.START_DATE_INPUT)
        self.enter_date(self.START_DATE_INPUT, value)

    def enter_end_date_in_payment_unit_of_opportunity(self, value):
        self.scroll_into_view(self.END_DATE_INPUT)
        self.enter_date(self.END_DATE_INPUT, value)

    def select_required_deliver_units_checkbox(self, required_text):
        section = self.page.locator(self.REQUIRED_DELIVER_UNITS_SECTION).first
        label = section.locator(f"xpath=.//label[normalize-space(.) = '{required_text}']")
        checkbox = label.locator("input")
        if not checkbox.is_checked():
            label.click()

    def verify_payment_unit_present(self, payment_unit_name):
        table = self.page.locator(self.PAYMENT_UNITS_TABLE).first
        rows = table.locator("xpath=.//tbody/tr[not(contains(@class,'detail-row'))]")
        for i in range(rows.count()):
            unit_name_cell = rows.nth(i).locator("xpath=./td[2]")
            if unit_name_cell.inner_text().strip() == payment_unit_name:
                return
        raise AssertionError(f"Payment Unit '{payment_unit_name}' not found in UI table")

    def click_setup_budget_button(self):
        self.click(self.SETUP_BUDGET_BUTTON)
        self.page.wait_for_url("**/finalize/**")

    def enter_max_connect_workers_in_budget(self, value):
        self.page.locator(self.MAX_CONNECT_WORKERS_INPUT).first.fill(value)

    def verify_total_budget_value(self, value):
        self.page.wait_for_timeout(1000)
        actual_value = self.page.locator(self.TOTAL_BUDGET_INPUT).first.input_value()
        assert actual_value == value, f"Expected total budget value to be '{value}', but got '{actual_value}'"

    def fill_opportunity_form(self, data, learn_app, delivery_app, env, network_manager=None):
        env_suffix = f"_{env}" if env == "staging" else ""
        opp_name = self.enter_name_in_opportunity(data["opportunity_name"])
        if network_manager:
            # Currency/country are inherited (read-only) from the Program for managed opportunities.
            self.select_network_manager_organization(network_manager)
        else:
            self.select_currency_in_opportunity(data["currency"])
            self.select_country_in_opportunity(data["country"])
        self.enter_short_description_in_opportunity(data["short_description"])
        self.enter_description_in_opportunity(data["description"])
        self.select_hq_server_in_opportunity(data[f"hq_server{env_suffix}"])
        self.select_api_key_in_opportunity(data[f"api_key{env_suffix}"])
        self.select_learn_app_domain_in_opportunity(data[f"learn_app_domain{env_suffix}"])
        self.select_deliver_app_domain_in_opportunity(data[f"deliver_app_domain{env_suffix}"])
        self.select_learn_app_in_opportunity(learn_app)
        self.select_deliver_app_in_opportunity(delivery_app)
        self.enter_learn_app_description_in_opportunity(data["learn_app_description"])
        self.enter_passing_score_in_opportunity(data["passing_score"])
        self.click_submit_btn()
        return opp_name

    def create_opportunity_in_connect_page(self, data, learn_app, delivery_app, env, network_manager=None):
        self.page.wait_for_timeout(5000)
        try:
            opp_name = self.fill_opportunity_form(data, learn_app, delivery_app, env, network_manager)
        except Exception:
            self.page.reload(wait_until="domcontentloaded", timeout=60000)
            self.page.wait_for_timeout(10000)
            opp_name = self.fill_opportunity_form(data, learn_app, delivery_app, env, network_manager)
        self.page.wait_for_timeout(3000)
        return opp_name

    def create_payment_unit_in_connect_page(self, data, days=7):
        self.click_add_payment_unit_button()
        self.enter_name_in_opportunity(data["payment_unit_name"])
        self.enter_amount_in_payment_unit_of_opportunity(data["amount"])
        self.enter_description_in_opportunity(data["description"])
        self.enter_max_total_in_payment_unit_of_opportunity(data["max_total"])
        self.enter_max_daily_in_payment_unit_of_opportunity(data["max_daily"])
        start, end = self.generate_date_range(days)
        self.enter_start_date_in_payment_unit_of_opportunity(start)
        self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.select_required_deliver_units_checkbox(data["required_deliver_units"])
        self.click_submit_btn()
        self.page.wait_for_timeout(3000)
        self.verify_payment_unit_present(self.opp_full_name)

    def setup_budget_in_connect_page(self, data, days=7):
        self.click_setup_budget_button()
        start, end = self.generate_date_range(days)
        self.enter_start_date_in_payment_unit_of_opportunity(start)
        self.enter_end_date_in_payment_unit_of_opportunity(end)
        self.enter_max_connect_workers_in_budget(data["no_of_connect_workers"])
        self.verify_total_budget_value(data["total_budget_value"])
        self.click_submit_btn()
        self.page.wait_for_timeout(3000)

    def click_opportunity_in_opportunity(self, value):
        self.page.wait_for_timeout(5000)
        try:
            self.select_by_visible_text(self.PAGE_SIZE, "100")
            self.page.wait_for_timeout(10000)
        except Exception:
            print("Dropdown not present")
        self.click_link_by_text(value)
        self.page.wait_for_timeout(3000)
