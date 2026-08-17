import os

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# Stage app "[AV] Case List Map" on connectqa-automation (module 0 = "Case List").
# Copied from connectqa app 6687228a372e411299076007ba256ac2 onto the standard
# automation domain. The prod copy does not exist yet, so there is no prod
# default - override with MAP_APP_ID when one is created.
DEFAULT_MAP_APP_ID = "0c4ed4b5973342e9aaed4ceff42b2389"

# Format-dropdown values that only render on the map, and the Address format they
# all depend on (deleting the Address column auto-removes every geo row).
GEO_FORMAT_VALUES = {"geo-boundary", "geo-boundary-color", "geo-points", "geo-points-colors"}
ADDRESS_FORMAT_VALUE = "address"

# A geo Format option used when adding a property in Map_01.
GEO_BOUNDARY_LABEL = "Geo Boundary (Mobile only)"


class CaseListMapPage(BasePage):
    """CommCare HQ app-builder > module > "Case List" tab: the geo Display
    Properties table (Case List Map cases Map_01 / Map_02).

    The config panel nests several tables, so the Display Properties table is
    always matched by its column headers, never by position. Format is a
    Knockout-bound <select>: setting its value must go through the real UI
    (Playwright select_option fires the native change Knockout listens to);
    assigning .value in JS does not update the model.

    Idempotency: none of these actions click Save, so nothing is persisted -
    discard_changes() reloads the app and restores the live config untouched.
    """

    CASE_LIST_TAB = locators.get("cchq_case_list_map_page", "case_list_tab")
    DISPLAY_PROPERTIES_TABLE = locators.get("cchq_case_list_map_page", "display_properties_table")
    PROPERTY_ROWS = locators.get("cchq_case_list_map_page", "property_rows")
    ADD_PROPERTY_BUTTON = locators.get("cchq_case_list_map_page", "add_property_button")

    # Row-relative locators (see locators file note: LocatorLoader can't carry
    # './/' values). The Format select is the one offering the geo formats; the
    # Property select is select2-backed; Display Text is the row's text input.
    ROW_FORMAT_SELECT = "xpath=.//select[.//option[normalize-space()='Geo Boundary (Mobile only)']]"
    ROW_PROPERTY_SELECT = "xpath=.//select[contains(@class,'select2-hidden-accessible')]"
    ROW_DISPLAY_TEXT = "xpath=.//input[@type='text' and contains(@class,'form-control')]"
    ROW_DELETE_ICON = "xpath=.//i[@title='Delete']"

    @staticmethod
    def module_url(config, app_id=None):
        """Derive the module-0 config URL from the configured cchq login URL.

        cchq_url is '.../a/<domain>/login/'; the app builder lives at
        '.../a/<domain>/apps/view/<app_id>/modules-0/'.
        """
        app_id = app_id or os.getenv("MAP_APP_ID", DEFAULT_MAP_APP_ID)
        base = config.get("cchq_url").split("/login/")[0]
        return f"{base}/apps/view/{app_id}/modules-0/"

    def open(self, config, app_id=None):
        url = self.module_url(config, app_id)
        self._step(f"open Case List Map module {url}")
        self.page.goto(url, wait_until="load")
        self.open_case_list_tab()

    def open_case_list_tab(self):
        """Switch to the module's 'Case List' tab and wait for its config to render."""
        self.click(self.CASE_LIST_TAB)
        self.page.locator(self.DISPLAY_PROPERTIES_TABLE).first.wait_for(state="visible", timeout=30000)
        self.page.wait_for_timeout(1500)

    # --- reads -------------------------------------------------------------
    def _rows(self):
        return self.page.locator(self.PROPERTY_ROWS)

    def read_property_rows(self):
        """Return [{property, format, display_text}, ...] for every data row.

        Read via evaluate against the header-matched table so it is immune to
        the sibling tables nested in the same panel.
        """
        return self.page.evaluate(
            """() => {
                const t = [...document.querySelectorAll('table')].find(x => {
                    const h = [...x.querySelectorAll('thead th')].map(y => y.textContent.trim());
                    return h.includes('Property') && h.includes('Display Text') && h.includes('Format');
                });
                if (!t) return [];
                return [...t.querySelectorAll('tbody tr')].map(r => {
                    const fmt = [...r.querySelectorAll('select')].find(s => /Geo Boundary/.test(s.textContent));
                    const prop = [...r.querySelectorAll('select')].find(s => s.className.includes('select2-hidden-accessible'));
                    const dt = r.querySelector('input.form-control');
                    return {property: prop ? prop.value : null, format: fmt ? fmt.value : null, display_text: dt ? dt.value : null};
                }).filter(row => row.format !== null);
            }"""
        )

    def format_option_labels(self):
        """Labels offered by a Format dropdown (read from the first data row)."""
        return self._rows().first.locator(self.ROW_FORMAT_SELECT).locator("option").all_inner_texts()

    def geo_format_count(self):
        return sum(1 for r in self.read_property_rows() if r["format"] in GEO_FORMAT_VALUES)

    def has_address_property(self):
        return any(r["format"] == ADDRESS_FORMAT_VALUE for r in self.read_property_rows())

    def row_count(self):
        return self._rows().count()

    def _address_row_index(self):
        """Index (within the data rows) of the row whose Format is Address, or -1."""
        rows = self.read_property_rows()
        for i, r in enumerate(rows):
            if r["format"] == ADDRESS_FORMAT_VALUE:
                return i
        return -1

    # --- writes (never saved) ---------------------------------------------
    def add_property(self):
        """Click 'Add Property'; return the new data-row count."""
        before = self.row_count()
        self.click(self.ADD_PROPERTY_BUTTON)
        self.page.wait_for_timeout(500)
        self._rows().nth(before).wait_for(state="visible", timeout=10000)
        return self.row_count()

    def set_last_row_format(self, label):
        """Set the Format of the last data row through the real UI (Knockout)."""
        self._step(f"set last row Format to '{label}'")
        row = self._rows().last
        row.locator(self.ROW_FORMAT_SELECT).select_option(label=label)
        self.page.wait_for_timeout(500)

    def last_row_format_value(self):
        return self.read_property_rows()[-1]["format"]

    def delete_address_property(self):
        """Delete the Address-format row through the UI (drives the geo-row
        auto-removal). Asserts an Address row was actually present to delete."""
        index = self._address_row_index()
        assert index >= 0, "No Address-format property row to delete"
        self._step(f"delete Address-format row (index {index})")
        self._rows().nth(index).locator(self.ROW_DELETE_ICON).click()
        self.page.wait_for_timeout(700)

    def discard_changes(self, config, app_id=None):
        """Reload the app builder to drop every unsaved edit and restore the
        live config. Used instead of a Save/reverse so the shared app stays
        pristine no matter how a test exits."""
        self.open(config, app_id)
