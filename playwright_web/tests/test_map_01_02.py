"""Case List Map - geo Display Properties config (web/HQ portion).

Covers the deterministic, HQ-side cases from the "Case List map" tab of the
master plan ("CCC_ Mobile App Regression [Master] [v2]"):

  Map_01  the module's Case List tab offers the geo Display-Property formats, and
          a geo format can be added while an Address column exists
  Map_02  the geo formats depend on an Address column - deleting the Address
          property auto-removes every geo-format row

Both cases mutate the app's Display Properties, so each RESTORES the app by
reloading without saving (nothing is ever persisted - see CaseListMapPage).
The rendering cases (Map_03-06) and the mobile toggle/warning cases (Map_07-11)
are canvas/Maestro work and live elsewhere.
"""
import pytest

from pages.cchq_case_list_map_page import (
    GEO_BOUNDARY_LABEL,
    GEO_FORMAT_VALUES,
    CaseListMapPage,
    resolve_app_id,
)
from pages.cchq_login_page import LoginPage

# Format labels that must be offered on the Case List tab for the map feature.
EXPECTED_GEO_LABELS = [
    "Geo Boundary (Mobile only)",
    "Geo Boundary Color (Mobile only)",
    "Geo Points (Mobile only)",
    "Geo Points Colors (Mobile only)",
]


def _open_case_list_map(page, config, settings):
    LoginPage(page).valid_login_cchq(config, settings)
    screen = CaseListMapPage(page)
    screen.open(config)
    return screen


@pytest.fixture(scope="module")
def case_list_map(browser, config, settings):
    """One CCHQ login for the whole module; each test re-navigates to a clean
    Case List tab with screen.open(config). The app-id guard runs before any
    browser is created, so a skip spins up no session. Retries flaky login once."""
    # "[AV] Case List Map" has a copy on stage and prod; skip only on an
    # environment with no known app id (and no MAP_APP_ID override).
    if not resolve_app_id(config.env):
        pytest.skip(
            f"No '[AV] Case List Map' app id for env '{config.env}'. Set MAP_APP_ID to run here."
        )
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            screen = _open_case_list_map(page, config, settings)
        except Exception:
            page.close()
            page = context.new_page()
            screen = _open_case_list_map(page, config, settings)
        yield screen
    finally:
        context.close()


def test_map_01_add_geo_display_property(case_list_map, config):
    """Map_01 - the Case List tab exposes the geo formats (plus the Address
    format they need), and adding a property with a geo format is accepted while
    an Address column is present. Restores the app afterwards (no save)."""
    screen = case_list_map
    screen.open(config)  # reset to a clean Case List tab
    try:
        # The Format dropdown offers every geo format plus Address.
        labels = screen.format_option_labels()
        for expected in EXPECTED_GEO_LABELS:
            assert expected in labels, f"Format dropdown missing '{expected}'. Offered: {labels}"
        assert "Address" in labels, f"Format dropdown missing 'Address'. Offered: {labels}"

        # Pre-condition for the add: an Address-format column exists.
        assert screen.has_address_property(), (
            "Expected the app to have an Address-format property before adding a geo format"
        )

        # Add a property and set its Format to a geo format - accepted (not
        # auto-removed) because an Address column is present.
        before = screen.row_count()
        after = screen.add_property()
        assert after == before + 1, f"Add Property did not add a row ({before} -> {after})"

        screen.set_last_row_format(GEO_BOUNDARY_LABEL)
        assert screen.last_row_format_value() in GEO_FORMAT_VALUES, (
            f"New row did not keep the geo format; saw {screen.last_row_format_value()!r}"
        )
        assert screen.row_count() == before + 1, (
            "Geo row was removed even though an Address column exists"
        )
    finally:
        screen.discard_changes(config)


def test_map_02_geo_formats_require_address_column(case_list_map, config):
    """Map_02 - geo formats depend on an Address column: deleting the
    Address-format property auto-removes every geo-format row. Restores the app
    afterwards (no save)."""
    screen = case_list_map
    screen.open(config)  # reset to a clean Case List tab
    try:
        assert screen.has_address_property(), (
            "Expected an Address-format property to delete for the dependency check"
        )
        geo_before = screen.geo_format_count()
        assert geo_before > 0, "Expected the app to have geo-format rows before the check"

        screen.delete_address_property()

        assert not screen.has_address_property(), "Address property was not removed"
        assert screen.geo_format_count() == 0, (
            f"Deleting Address should auto-remove all geo rows; "
            f"{screen.geo_format_count()} still present (was {geo_before})"
        )
    finally:
        screen.discard_changes(config)
