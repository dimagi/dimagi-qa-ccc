"""Opportunity List page (CCCT-2667).

The page is org-scoped and role-aware. Connect renders one of two django-tables2
tables depending on the signed-in org (OpportunityList.get_table_class):

  * program_manager org -> ProgramManagerOpportunityTable  (PM columns)
  * any other org       -> OpportunityTable                (NM columns)

so the column set is a function of *which org is selected*, not of the URL. Every
locator here is derived from the Connect source (opportunities_list.html +
base_table.html + tables.py + filters.py), not guessed against a live page.
"""

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# Common columns rendered for both roles (BaseOpportunityList.Meta.sequence). The
# index, Test/Real (entity_type) and actions columns carry blank headers, so they
# are asserted structurally elsewhere rather than by header text.
# Headers as django-tables2 renders them: it title-cases only the first word of a
# column name, so start_date -> "Start date" (confirmed against the live list page).
COMMON_COLUMNS = ["Opportunity", "Status", "Program", "Start date", "End date"]
# NM view (OpportunityTable) - operational backlog columns.
NM_COLUMNS = COMMON_COLUMNS + [
    "Pending Invites",
    "Inactive Connect Workers",
    "Pending Approvals",
    "Payments Due",
]
# PM view (ProgramManagerOpportunityTable) - delivery/earnings columns.
PM_COLUMNS = COMMON_COLUMNS + [
    "Active Connect Workers",
    "Total Deliveries",
    "Verified Deliveries",
    "Worker Earnings",
]
# Columns whose header is a sort link (everything orderable in BaseOpportunityList).
SORTABLE_COLUMNS = ["Opportunity", "Status", "Program", "Start date", "End date"]

# Kebab menu actions (OpportunityTable/ProgramManagerOpportunityTable.render_actions).
KEBAB_ACTIONS = ["View Opportunity", "View Connect Workers", "View Invoices"]

IS_TEST_OPTIONS = ["Yes", "No"]
STATUS_OPTIONS = ["Active", "Ended", "Inactive"]


class ConnectOpportunityListPage(BasePage):
    HEADING = locators.get("connect_opportunity_list_page", "heading")
    TABLE = locators.get("connect_opportunity_list_page", "table")
    COLUMN_HEADERS = locators.get("connect_opportunity_list_page", "column_headers")
    DATA_ROWS = locators.get("connect_opportunity_list_page", "data_rows")
    EMPTY_TEXT = locators.get("connect_opportunity_list_page", "empty_text")
    SORT_HEADER_BY_LABEL = locators.get("connect_opportunity_list_page", "sort_header_by_label")
    ROW_LINK_BY_NAME = locators.get("connect_opportunity_list_page", "row_link_by_name")
    TEST_ICON_BY_NAME = locators.get("connect_opportunity_list_page", "test_icon_by_name")

    FILTER_BUTTON = locators.get("connect_opportunity_list_page", "filter_button")
    FILTER_BADGE = locators.get("connect_opportunity_list_page", "filter_badge")
    FILTER_MODAL = locators.get("connect_opportunity_list_page", "filter_modal")
    FILTER_APPLY_BTN = locators.get("connect_opportunity_list_page", "filter_apply_btn")
    FILTER_CLOSE_BTN = locators.get("connect_opportunity_list_page", "filter_close_btn")
    FILTER_IS_TEST_SELECT = locators.get("connect_opportunity_list_page", "filter_is_test_select")
    FILTER_STATUS_SELECT = locators.get("connect_opportunity_list_page", "filter_status_select")
    FILTER_PROGRAM_SELECT = locators.get("connect_opportunity_list_page", "filter_program_select")

    PAGE_SIZE_SELECT = locators.get("connect_opportunity_list_page", "page_size_select")
    NEXT_PAGE_BTN = locators.get("connect_opportunity_list_page", "next_page_btn")
    PREV_PAGE_BTN = locators.get("connect_opportunity_list_page", "prev_page_btn")
    PAGE_NUMBER_INPUT = locators.get("connect_opportunity_list_page", "page_number_input")

    KEBAB_TOGGLE_BY_NAME = locators.get("connect_opportunity_list_page", "kebab_toggle_by_name")
    KEBAB_MENU_ITEMS = locators.get("connect_opportunity_list_page", "kebab_menu_items")
    KEBAB_MENU_ITEM_BY_TEXT = locators.get("connect_opportunity_list_page", "kebab_menu_item_by_text")
    STATUS_BADGES = locators.get("connect_opportunity_list_page", "status_badges")
    STATS_LINKS = locators.get("connect_opportunity_list_page", "stats_links")
    COUNT_LINK_BY_HREF = locators.get("connect_opportunity_list_page", "count_link_by_href")

    # -- navigation / structure ------------------------------------------------

    def verify_loaded(self):
        """Wait for the list page. The heading is present for both roles and both
        the populated and empty states, so it is the safest load signal."""
        self.page.locator(self.HEADING).first.wait_for(state="visible", timeout=30000)
        assert "/opportunity" in self.page.url, f"Not on the opportunity list page: {self.page.url}"
        self._step("Opportunity List page loaded")

    def column_headers(self):
        headers = [h.strip() for h in self.page.locator(self.COLUMN_HEADERS).all_inner_texts()]
        self._step(f"Opportunity list columns: {headers}")
        return headers

    def verify_columns(self, expected):
        headers = self.column_headers()
        # Sortable headers append a sort-direction glyph and the tooltip columns
        # carry an info icon, so match on containment rather than equality.
        joined = " | ".join(headers)
        missing = [col for col in expected if col not in joined]
        assert not missing, f"Missing columns {missing} in {headers}"
        self._step(f"All expected columns present: {expected}")
        return headers

    def row_count(self):
        count = self.page.locator(self.DATA_ROWS).count()
        self._step(f"Opportunity rows visible: {count}")
        return count

    def is_empty(self):
        return self.page.locator(self.EMPTY_TEXT).count() > 0

    def first_row_name(self):
        """Name in the first data row - used to pick a real opportunity to act on
        without hard-coding one, keeping the tests independent of seed data."""
        row = self.page.locator(self.DATA_ROWS).first
        row.wait_for(state="visible", timeout=15000)
        name = row.locator("xpath=.//a").first.inner_text().strip()
        self._step(f"First opportunity in list: {name!r}")
        return name

    # -- sorting ----------------------------------------------------------------

    def sortable_headers_present(self):
        """Which of the sortable columns actually expose a sort link."""
        present = [
            col
            for col in SORTABLE_COLUMNS
            if self.page.locator(self.SORT_HEADER_BY_LABEL.format(label=col)).count() > 0
        ]
        self._step(f"Sortable column headers: {present}")
        return present

    def click_sort(self, label):
        """Click a column's sort link and return the resulting ?sort= value.

        sortable_header cycles field -> -field -> (none), navigating each time, so
        the sort parameter in the URL is the observable proof the click took effect.
        """
        self._step(f"Sort by '{label}'")
        self.click(self.SORT_HEADER_BY_LABEL.format(label=label))
        self.page.wait_for_load_state("load")
        self.verify_loaded()
        from urllib.parse import parse_qs, urlparse

        sort = parse_qs(urlparse(self.page.url).query).get("sort", [""])[0]
        self._step(f"URL sort param after click: {sort!r}")
        return sort

    # -- filters ----------------------------------------------------------------

    def open_filter_modal(self):
        self._step("Open filter modal")
        self.click(self.FILTER_BUTTON)
        self.page.locator(self.FILTER_MODAL).first.wait_for(state="visible", timeout=15000)

    def close_filter_modal(self):
        self.click(self.FILTER_CLOSE_BTN)
        self.page.wait_for_timeout(500)

    def filter_fields_present(self):
        """Which filter fields the modal exposes. Program is present only for PM
        orgs that own at least one program (OpportunityListFilterSet.__init__)."""
        fields = {
            "is_test": self.page.locator(f"#{self._raw('filter_is_test_select')}").count() > 0,
            "status": self.page.locator(f"#{self._raw('filter_status_select')}").count() > 0,
            "program": self.page.locator(f"#{self._raw('filter_program_select')}").count() > 0,
        }
        self._step(f"Filter fields present: {fields}")
        return fields

    def _raw(self, key):
        # The select ids are stored as bare ids; strip the loader's leading '#'.
        return locators.get("connect_opportunity_list_page", key).lstrip("#")

    def _select_option_labels(self, select_id):
        options = self.page.locator(f"#{select_id} option").all_inner_texts()
        # Drop the empty/placeholder choice ("---------") that Django adds.
        labels = [o.strip() for o in options if o.strip() and not o.strip().startswith("---")]
        return labels

    def is_test_options(self):
        labels = self._select_option_labels(self._raw("filter_is_test_select"))
        self._step(f"Is Test options: {labels}")
        return labels

    def status_options(self):
        labels = self._select_option_labels(self._raw("filter_status_select"))
        self._step(f"Status options: {labels}")
        return labels

    def program_options(self):
        labels = self._select_option_labels(self._raw("filter_program_select"))
        self._step(f"Program options: {labels}")
        return labels

    def apply_filters(self):
        self._step("Apply filters")
        self.click(self.FILTER_APPLY_BTN)
        self.page.wait_for_load_state("load")
        self.verify_loaded()

    def filter_badge_count(self):
        badge = self.page.locator(self.FILTER_BADGE)
        if badge.count() == 0:
            return 0
        text = badge.first.inner_text().strip()
        return int(text) if text.isdigit() else 0

    # -- pagination -------------------------------------------------------------

    def pagination_visible(self):
        """The pager (and the page-size selector inside it) render only when the
        total row count exceeds DEFAULT_PAGE_SIZE (20)."""
        return self.page.locator(f"#{self._raw('page_size_select')}").count() > 0

    def page_size_options(self):
        labels = [o.strip() for o in self.page.locator(f"#{self._raw('page_size_select')} option").all_inner_texts()]
        self._step(f"Rows-per-page options: {labels}")
        return labels

    def set_page_size(self, size):
        self._step(f"Set rows per page to {size}")
        self.select_by_visible_text(self.PAGE_SIZE_SELECT, str(size))
        self.page.wait_for_load_state("load")
        self.verify_loaded()

    def go_next_page(self):
        self._step("Next page")
        self.click(self.NEXT_PAGE_BTN)
        self.page.wait_for_load_state("load")
        self.verify_loaded()

    # -- row open / kebab -------------------------------------------------------

    def open_opportunity(self, name):
        self._step(f"Open opportunity '{name}'")
        self.click(self.ROW_LINK_BY_NAME.format(name=name))
        self.page.wait_for_load_state("load")

    def open_kebab(self, name):
        self._step(f"Open row menu for '{name}'")
        self.click(self.KEBAB_TOGGLE_BY_NAME.format(name=name))
        self.page.locator(self.KEBAB_MENU_ITEMS).first.wait_for(state="visible", timeout=10000)

    def kebab_options(self, name):
        self.open_kebab(name)
        items = [i.strip() for i in self.page.locator(self.KEBAB_MENU_ITEMS).all_inner_texts() if i.strip()]
        self._step(f"Kebab options for '{name}': {items}")
        return items

    def click_kebab_item(self, name, title):
        self.open_kebab(name)
        self._step(f"Click kebab item '{title}'")
        self.click(self.KEBAB_MENU_ITEM_BY_TEXT.format(title=title))
        self.page.wait_for_load_state("load")

    def has_test_badge(self, name):
        return self.page.locator(self.TEST_ICON_BY_NAME.format(name=name)).count() > 0

    # -- Tier 2: filter behaviour ----------------------------------------------

    def apply_status_filter(self, labels):
        """Select one or more Status values (TomSelect multi) and apply."""
        self.open_filter_modal()
        for label in labels:
            self.select_tomselect_by_label(self._raw("filter_status_select"), label, scope=self.FILTER_MODAL)
        self.apply_filters()

    def apply_program_filter(self, program_label):
        self.open_filter_modal()
        self.select_tomselect_by_label(self._raw("filter_program_select"), program_label, scope=self.FILTER_MODAL)
        self.apply_filters()

    def visible_statuses(self):
        statuses = [s.strip() for s in self.page.locator(self.STATUS_BADGES).all_inner_texts() if s.strip()]
        self._step(f"Visible row statuses: {statuses}")
        return statuses

    def clear_filters(self):
        """Drop all query params by reloading the bare list URL."""
        base = self.page.url.split("?")[0]
        self.page.goto(base)
        self.page.wait_for_load_state("load")
        self.verify_loaded()

    # -- Tier 3: count-cell drill-downs ----------------------------------------

    def count_link_count(self, href_fragment):
        n = self.page.locator(self.COUNT_LINK_BY_HREF.format(frag=href_fragment)).count()
        self._step(f"Count links matching {href_fragment!r}: {n}")
        return n

    def stats_link_count(self):
        return self.page.locator(self.STATS_LINKS).count()

    def open_first_count_link(self, href_fragment):
        self._step(f"Open first count link matching {href_fragment!r}")
        self.click(self.COUNT_LINK_BY_HREF.format(frag=href_fragment))
        self.page.wait_for_load_state("load")

    def apply_is_test_and_status(self, is_test_label, status_labels):
        """OLP_22 - combined filters: is_test (plain Select) + status (TomSelect)."""
        self.open_filter_modal()
        self.select_by_visible_text(self.FILTER_IS_TEST_SELECT, is_test_label)
        for label in status_labels:
            self.select_tomselect_by_label(self._raw("filter_status_select"), label, scope=self.FILTER_MODAL)
        self.apply_filters()

    def managed_create_status(self, config, program_id):
        """OLP_02 - GET the managed opportunity-init URL for the current org and
        return the HTTP status.

        ManagedOpportunityViewMixin.dispatch resolves the program by program_id
        (a real UUID is required - a non-UUID 500s, a missing one redirects), then
        ProgramManagerMixin denies any non-PM org with 403. So a PM org would reach
        the form (200) and an NM org gets 403.
        """
        slug = self.page.url.split("/a/")[1].split("/")[0]
        url = f"{config.get('connect_url')}/a/{slug}/program/{program_id}/opportunity-init"
        response = self.page.goto(url)
        status = response.status if response else None
        self._step(f"Managed create probe for org '{slug}' -> HTTP {status}")
        return status

    def kebab_item_hrefs(self, name):
        """Kebab action titles -> href, read in a single open (no navigation)."""
        self.open_kebab(name)
        links = self.page.locator(self.KEBAB_MENU_ITEMS)
        hrefs = {links.nth(i).inner_text().strip(): links.nth(i).get_attribute("href") for i in range(links.count())}
        self._step(f"Kebab hrefs for '{name}': {hrefs}")
        return hrefs
