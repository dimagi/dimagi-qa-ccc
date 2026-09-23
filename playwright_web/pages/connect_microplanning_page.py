"""Microplanning ("View Progress Map") - MicroplanningPage (the map + filter/
assignment sidebars) and CoverageProgressPage (its "Coverage" -> see more page).

The map itself renders on a Mapbox canvas with no per-feature DOM access, so
these page objects only ever touch the surrounding sidebars/forms/tables -
never map-canvas content. Selecting an individual work area (clicking a map
feature) is out of scope here for the same reason; every method below reaches
its target through a dropdown/toggle/button instead.
"""

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# WorkAreaStatus.choices (microplanning/models.py) - the MTP's plan wording is
# slightly off ("Not Started" isn't a real status; "Expected visit count" is
# short for "Expected Visit Count Reached"), so this list follows the product.
WORK_AREA_STATUS_OPTIONS = [
    "Unassigned",
    "Not Visited",
    "Visited",
    "Request for Inaccessible",
    "Expected Visit Count Reached",
    "Inaccessible",
    "Excluded",
]


class MicroplanningPage(BasePage):
    PAGE_TITLE = locators.get("connect_microplanning_page", "page_title")
    METRIC_CARD_LABELS = locators.get("connect_microplanning_page", "metric_card_labels")
    FILTER_STATUS_SELECT = locators.get("connect_microplanning_page", "filter_status_select")
    FILTER_ASSIGNEE_SELECT = locators.get("connect_microplanning_page", "filter_assignee_select")
    FILTER_START_DATE = locators.get("connect_microplanning_page", "filter_start_date")
    FILTER_END_DATE = locators.get("connect_microplanning_page", "filter_end_date")
    FILTER_UNASSIGNED_SELECT = locators.get("connect_microplanning_page", "filter_unassigned_select")
    SHOW_VISITS_TOGGLE = locators.get("connect_microplanning_page", "show_visits_toggle")
    DOWNLOAD_BUTTON = locators.get("connect_microplanning_page", "download_button")
    ENTER_ASSIGNMENT_MODE_LINK = locators.get("connect_microplanning_page", "enter_assignment_mode_link")
    EXIT_ASSIGNMENT_MODE_LINK = locators.get("connect_microplanning_page", "exit_assignment_mode_link")
    UNASSIGNED_ONLY_TOGGLE = locators.get("connect_microplanning_page", "unassigned_only_toggle")
    ASSIGNMENT_GROUP_SELECT = locators.get("connect_microplanning_page", "assignment_group_select")
    ASSIGNMENT_ASSIGNEE_SELECT = locators.get("connect_microplanning_page", "assignment_assignee_select")
    FLW_SUMMARY_SECTION = locators.get("connect_microplanning_page", "flw_summary_section")
    FLW_SUMMARY_VIEW_BY_FLW_BTN = locators.get("connect_microplanning_page", "flw_summary_view_by_flw_btn")
    FLW_SUMMARY_VIEW_VISITS_BTN = locators.get("connect_microplanning_page", "flw_summary_view_visits_btn")
    SELECT_WORK_AREA_SECTION = locators.get("connect_microplanning_page", "select_work_area_section")
    MODIFY_WORK_AREA_BUTTON = locators.get("connect_microplanning_page", "modify_work_area_button")
    MODIFY_WORK_AREA_MODAL = locators.get("connect_microplanning_page", "modify_work_area_modal")

    # -- Microplanning_01/30: land + opp-card metrics --------------------------------

    def verify_loaded(self):
        self.page.locator(self.PAGE_TITLE).first.wait_for(state="visible", timeout=20000)
        assert "/microplanning/" in self.page.url, f"Not on the microplanning page: {self.page.url}"
        self._step("Microplanning page loaded")

    def opp_card_metric_labels(self):
        labels = [l.strip() for l in self.page.locator(self.METRIC_CARD_LABELS).all_inner_texts() if l.strip()]
        self._step(f"Opp-card metric labels: {labels}")
        return labels

    # -- Microplanning_03/04/06/07/12/13/14: filter sidebar --------------------------

    def filter_fields_present(self):
        # Locator constants already carry the LocatorLoader '#' prefix.
        present = {
            "status": self.page.locator(self.FILTER_STATUS_SELECT).count() > 0,
            "assignee": self.page.locator(self.FILTER_ASSIGNEE_SELECT).count() > 0,
            "start_date": self.page.locator(self.FILTER_START_DATE).count() > 0,
            "end_date": self.page.locator(self.FILTER_END_DATE).count() > 0,
            "show_visits_toggle": self.page.locator(self.SHOW_VISITS_TOGGLE).count() > 0,
        }
        self._step(f"Filter Map Work Areas fields present: {present}")
        return present

    def _select_option_labels(self, select_selector):
        options = self.page.locator(f"{select_selector} option").all_inner_texts()
        return [o.strip() for o in options if o.strip() and not o.strip().startswith("---")]

    def status_filter_options(self):
        labels = self._select_option_labels(self.FILTER_STATUS_SELECT)
        self._step(f"Work Area Status options: {labels}")
        return labels

    def unassigned_filter_present(self):
        """'Show Only Unassigned' in the filter sidebar renders as a checkbox
        toggle (WorkAreaMapFilterSet.unassigned_only), not a Yes/No/Unknown
        dropdown as the plan text implies - confirmed live 2026-09-23."""
        present = self.page.locator(self.FILTER_UNASSIGNED_SELECT).count() > 0
        self._step(f"'Show Only Unassigned' filter checkbox present: {present}")
        return present

    def date_field_type(self, selector):
        return self.page.locator(selector).first.get_attribute("type")

    def download_button_present(self):
        return self.page.locator(self.DOWNLOAD_BUTTON).count() > 0

    def click_download(self):
        self._step("Download work area summary")
        with self.page.expect_download() as dl_info:
            self.click(self.DOWNLOAD_BUTTON)
        return dl_info.value

    # -- Microplanning_18/21: assignment mode entry/exit -----------------------------

    def enter_assignment_mode(self):
        self._step("Enter assignment mode")
        self.click(self.ENTER_ASSIGNMENT_MODE_LINK)
        self.page.wait_for_load_state("load")
        assert "assignment_mode=1" in self.page.url, f"Did not enter assignment mode: {self.page.url}"

    def exit_assignment_mode(self):
        self._step("Exit assignment mode")
        self.click(self.EXIT_ASSIGNMENT_MODE_LINK)
        self.page.wait_for_load_state("load")

    def toggle_show_only_unassigned(self):
        self._step("Toggle 'Show only unassigned Work Areas'")
        self.click(self.UNASSIGNED_ONLY_TOGGLE)

    def unassigned_toggle_state(self):
        return self.page.locator(self.UNASSIGNED_ONLY_TOGGLE).first.get_attribute("aria-checked")

    # -- Microplanning_22/25/27/28/29: assignment-mode panels ------------------------

    def assignment_group_options(self):
        labels = self._select_option_labels(self.ASSIGNMENT_GROUP_SELECT)
        self._step(f"'Select Work Areas to Assign' group options: {labels}")
        return labels

    def assignment_assignee_options(self):
        labels = self._select_option_labels(self.ASSIGNMENT_ASSIGNEE_SELECT)
        self._step(f"'Select new Assignee' options: {labels}")
        return labels

    def select_assignee_for_flw_summary(self, label):
        self.select_by_visible_text(self.ASSIGNMENT_ASSIGNEE_SELECT, label)
        self._step(f"Selected assignee '{label}' for FLW summary")

    def flw_summary_visible(self):
        return self.page.locator(self.FLW_SUMMARY_SECTION).first.is_visible()

    def flw_summary_text(self):
        return self.page.locator(self.FLW_SUMMARY_SECTION).first.inner_text()

    def open_flw_summary_by_flw(self):
        self._step("Open 'View summary by FLW'")
        self.click(self.FLW_SUMMARY_VIEW_BY_FLW_BTN)
        self.page.wait_for_load_state("load")

    def open_flw_summary_visits(self):
        self._step("Open FLW summary 'View Visits'")
        self.click(self.FLW_SUMMARY_VIEW_VISITS_BTN)
        self.page.wait_for_load_state("load")

    # -- Microplanning_16/17: select/modify a single work area (non-assignment-mode) -
    # No map click needed: mapController()'s single-select state (`selectedFeature`)
    # is set entirely client-side by its 'click' handler on the Mapbox canvas
    # ('workareas-fill' layer, map_handler.html), with no DOM/dropdown equivalent
    # outside assignment mode. Rather than guess at a pixel coordinate (unproven,
    # depends on current pan/zoom/render), this drives the same Alpine state a real
    # click would set, using a real work area id fetched from the same
    # group_work_areas endpoint the assignment-mode group dropdown already calls -
    # so the id/status/counts are real product data, not fabricated.

    def _option_values(self, select_selector):
        """<option value> attributes (real pks), skipping the empty placeholder -
        option *text* isn't what the assignment endpoints below take."""
        options = self.page.locator(f"{select_selector} option").all()
        return [v for v in (o.get_attribute("value") for o in options) if v]

    def fetch_a_real_work_area(self, host, org_slug, opp_id):
        """A real WorkArea record (id/building_count/expected_visit_count/status)
        via the same authenticated session. Tries every assignee's own work areas
        (get_flw_work_areas_for_assignment) rather than assuming work area groups
        exist - Microplanning_02 (create groups) is a separate, not-yet-automated,
        mutating case, so this opportunity may have zero groups."""
        assignee_ids = self._option_values(self.ASSIGNMENT_ASSIGNEE_SELECT)
        for assignee_id in assignee_ids:
            url = f"{host}/a/{org_slug}/microplanning/{opp_id}/assignment/flw_work_areas/{assignee_id}/"
            resp = self.page.request.get(url)
            assert resp.ok, f"GET {url} -> {resp.status}"
            work_areas = resp.json()["work_areas"]
            if work_areas:
                self._step(f"Fetched real work area {work_areas[0]} (assignee {assignee_id})")
                return work_areas[0]
        return None

    def select_work_area_via_js(self, work_area):
        """Set mapController()'s selectedFeature directly - the same effect a real
        canvas click on this feature would have, without depending on map render
        state. Requires window.Alpine (Alpine.js exposes it globally by default)."""
        self._step(f"Select work area {work_area['id']} (JS, no map click)")
        self.page.evaluate(
            """(wa) => {
                const el = document.querySelector('[x-data="mapController()"]');
                const data = window.Alpine.$data(el);
                data.selectedFeature = {
                    expected_visit_count: wa.expected_visit_count,
                    building_count: wa.building_count,
                    status: wa.status,
                    _id: wa.id,
                };
            }""",
            work_area,
        )

    def select_work_area_section_text(self):
        self.page.locator(self.SELECT_WORK_AREA_SECTION).first.wait_for(state="visible", timeout=10000)
        return self.page.locator(self.SELECT_WORK_AREA_SECTION).first.inner_text()

    def open_modify_work_area_modal(self):
        self._step("Open 'Modify Work Area'")
        self.click(self.MODIFY_WORK_AREA_BUTTON)
        self.page.locator(self.MODIFY_WORK_AREA_MODAL).first.wait_for(state="visible", timeout=10000)

    def modify_work_area_modal_text(self):
        return self.page.locator(self.MODIFY_WORK_AREA_MODAL).first.inner_text()

    # -- Microplanning_31: nav to the Coverage Progress Tracker ----------------------

    def open_coverage_progress(self):
        self._step("Open Coverage (see more)")
        self.click_link_by_text("Coverage")
        self.page.wait_for_load_state("load")


class CoverageProgressPage(BasePage):
    """The opp card's "Coverage / See more" destination (Microplanning_31/35-40 +
    the unnumbered "download core metrics file" row)."""

    PAGE_TITLE = locators.get("connect_coverage_progress_page", "page_title")
    WARD_SATURATION_LABEL = locators.get("connect_coverage_progress_page", "ward_saturation_label")
    DATE_FROM = locators.get("connect_coverage_progress_page", "date_from")
    DATE_TO = locators.get("connect_coverage_progress_page", "date_to")
    APPLY_BUTTON = locators.get("connect_coverage_progress_page", "apply_button")
    SECTION_HEADING_BY_TEXT = locators.get("connect_coverage_progress_page", "section_heading_by_text")
    DOWNLOAD_BUTTON_IN_SECTION = locators.get("connect_coverage_progress_page", "download_button_in_section")
    TABLE_BY_SECTION = locators.get("connect_coverage_progress_page", "table_by_section")

    def verify_loaded(self):
        self.page.locator(self.PAGE_TITLE).first.wait_for(state="visible", timeout=20000)
        assert "/coverage_progress/" in self.page.url, f"Not on the coverage progress page: {self.page.url}"
        self._step("Coverage Progress Tracker page loaded")

    def ward_saturation_text(self):
        """The percentage lives in a sibling <div> next to the label <p>, so read
        the whole containing block rather than the label element alone."""
        label = self.page.locator(self.WARD_SATURATION_LABEL).first
        return label.evaluate("el => el.parentElement.innerText").strip()

    def section_present(self, text):
        return self.page.locator(self.SECTION_HEADING_BY_TEXT.format(text=text)).count() > 0

    def section_table_headers(self, text):
        table = self.page.locator(self.TABLE_BY_SECTION.format(text=text)).first
        table.wait_for(state="visible", timeout=15000)
        headers = [h.strip() for h in table.locator("thead th").all_inner_texts() if h.strip()]
        self._step(f"'{text}' table headers: {headers}")
        return headers

    def download_from_section(self, text):
        # Two "Download" dropdowns exist on the page (Core Metrics + Metrics by
        # Work Area Group); the CSV link must be scoped to the same button's own
        # dropdown container, not just "the first CSV link in the DOM".
        self._step(f"Download '{text}' file")
        button = self.page.locator(self.DOWNLOAD_BUTTON_IN_SECTION.format(text=text)).first
        container = button.locator("xpath=..")
        with self.page.expect_download() as dl_info:
            button.click()
            container.locator("xpath=.//a[normalize-space()='CSV']").first.click()
        return dl_info.value

    def apply_date_filter(self, start_iso, end_iso):
        self._step(f"Apply date filter {start_iso}..{end_iso}")
        self.enter_date(self.DATE_FROM, start_iso)
        self.enter_date(self.DATE_TO, end_iso)
        self.click(self.APPLY_BUTTON)
        self.page.wait_for_load_state("load")
