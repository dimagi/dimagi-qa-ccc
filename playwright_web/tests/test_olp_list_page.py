"""Opportunity List page - Tier 1 (structural / deterministic) - CCCT-2667.

These cover the parts of the list page that do not depend on live counts: the
heading, the role-specific column set, sortable headers, the filter modal and its
option lists, the kebab actions, row navigation and the rows-per-page control.
Behaviour that needs seeded data in specific states (ordering correctness, filters
actually filtering, count drill-downs) is Tier 2/3 and lives in follow-up files.

One login per role, then many assertions - the same journey shape the tasking
suite uses - because the CCHQ -> Connect OAuth handshake is the expensive step.

Manual case map (CCC Web Platform [Master] sheet):
  OLP_01/04 landing, OLP_05 columns+sort, OLP_08 row open, OLP_09 filter modal,
  OLP_10 is-test options, OLP_11 status options, OLP_12 program options,
  OLP_17 kebab actions, OLP_07 pagination control.
"""

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_opportunity_list_page import (
    IS_TEST_OPTIONS,
    KEBAB_ACTIONS,
    NM_COLUMNS,
    PM_COLUMNS,
    SORTABLE_COLUMNS,
    STATUS_OPTIONS,
    ConnectOpportunityListPage,
)


def test_olp_list_program_manager_view(page, test_data, config, settings):
    """PM org: PM column set, sortable headers, filter modal (incl. Program),
    kebab actions and the rows-per-page control."""
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    olp = ConnectOpportunityListPage(connect_page)

    # OLP_01/04 - landing
    olp.verify_loaded()

    # OLP_05 (PM) - the program-manager column set
    olp.verify_columns(PM_COLUMNS)

    # OLP_05 - every common column offers a sort link
    assert olp.sortable_headers_present() == SORTABLE_COLUMNS

    # OLP_09/10/11/12 - filter modal and its option lists (Program present for PM)
    olp.open_filter_modal()
    fields = olp.filter_fields_present()
    assert fields["is_test"] and fields["status"], f"Missing core filter fields: {fields}"
    assert fields["program"], "PM view should expose the Program filter"
    assert set(IS_TEST_OPTIONS).issubset(set(olp.is_test_options()))
    assert olp.status_options() == STATUS_OPTIONS
    assert olp.program_options(), "Program filter should list at least one program for a PM org"
    olp.close_filter_modal()

    # OLP_17 - kebab actions (needs at least one opportunity)
    if olp.row_count() > 0:
        name = olp.first_row_name()
        assert olp.kebab_options(name) == KEBAB_ACTIONS
    else:
        olp._step("No opportunities in PM list - skipping kebab assertion (needs >=1 row)")

    # OLP_07 - rows-per-page control (only rendered when the list exceeds 20 rows)
    if olp.pagination_visible():
        assert olp.page_size_options() == ["20", "30", "50", "100"]
    else:
        olp._step("Pagination not shown (<=20 opportunities) - rows-per-page control absent by design")


def test_olp_list_network_manager_view(page, test_data, config, settings):
    """NM org: NM column set and a filter modal without the Program field."""
    nm_org = test_data.get("OLP_1")["network_manager"]
    connect_page = login_to_connect(page, config, settings, nm_org)
    olp = ConnectOpportunityListPage(connect_page)

    # OLP_01/04 - landing
    olp.verify_loaded()

    # OLP_05 (NM) - the network-manager column set
    olp.verify_columns(NM_COLUMNS)

    # OLP_09 - filter modal; Program filter is omitted for an org that owns no
    # programs (OpportunityListFilterSet.__init__), which is the NM case.
    olp.open_filter_modal()
    fields = olp.filter_fields_present()
    assert fields["is_test"] and fields["status"], f"Missing core filter fields: {fields}"
    assert not fields["program"], "NM view should not expose the Program filter"
    assert olp.status_options() == STATUS_OPTIONS
    olp.close_filter_modal()

    # OLP_23/24/26 - NM count cells drill down to the right pages (by sort param:
    # inactive workers -> worker list; payments due -> payments tab). Checked
    # before the row-open navigation so both run off the same login.
    if olp.row_count() > 0:
        assert olp.stats_link_count() > 0, "NM rows should expose clickable count cells (Pending Invites)"
        assert olp.count_link_count("sort=last_active") > 0, "Inactive Connect Workers drill-down missing"
        assert olp.count_link_count("sort=-total_paid") > 0, "Payments Due drill-down missing"

    # OLP_08 - selecting an opportunity opens its dashboard
    if olp.row_count() > 0:
        name = olp.first_row_name()
        olp.open_opportunity(name)
        assert "/opportunity/" in connect_page.url
        olp._step(f"Landed on opportunity page: {connect_page.url}")
    else:
        olp._step("No opportunities in NM list - skipping row-open assertion (needs >=1 row)")

    # OLP_02 (NM cannot create an opportunity) is left manual: the only create path
    # is the program-scoped ManagedOpportunityInit, which resolves the program in
    # setup() before the ProgramManagerMixin permission check - so a clean 403 needs
    # a real program slug the NM org can reference, and this NM org has no program
    # data on staging (a bogus slug 500s). Not worth a fragile, data-seeded probe.
