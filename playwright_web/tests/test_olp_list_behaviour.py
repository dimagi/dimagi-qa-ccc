"""Opportunity List page - Tier 2 (filter behaviour) + Tier 3 (count drill-downs).

PM-org journey (one login). Assertions are tolerant of how much seed data exists:
filters are checked by "every visible row honours the filter" rather than exact
counts, and drill-down targets are checked by the distinctive sort param the table
renderer appends (stable regardless of URL path naming).

Manual case map: OLP_06/13 (status filter + badge), OLP_14 (multi-select status),
OLP_15 (program filter), OLP_16 (filter persistence), OLP_27/28/29/30 (PM count
drill-downs). NM-only drill-downs (OLP_23/24/26) need an NM session - separate.
"""

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_home_page import ConnectHomePage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def test_olp_list_pm_behaviour(page, test_data, config, settings):
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()

    if olp.row_count() == 0:
        olp._step("No opportunities in PM list - skipping behaviour checks (needs >=1 row)")
        return

    # OLP_07 - pagination moves between pages (only when the list exceeds one page)
    if olp.pagination_visible():
        first_before = olp.first_row_name()
        olp.go_next_page()
        assert olp.first_row_name() != first_before, "Next page should show different rows"
        olp.clear_filters()
    else:
        olp._step("<=20 opportunities - multi-page pagination not exercised (OLP_07)")

    # OLP_06/13 - single status filter: badge shows it is applied, and every
    # visible row carries that status.
    olp.apply_status_filter(["Active"])
    assert olp.filter_badge_count() >= 1, "Filter badge should reflect the applied status"
    assert all(s == "Active" for s in olp.visible_statuses()), olp.visible_statuses()
    olp.clear_filters()

    # OLP_14 - multi-select status
    olp.apply_status_filter(["Active", "Ended"])
    assert all(s in {"Active", "Ended"} for s in olp.visible_statuses()), olp.visible_statuses()
    olp.clear_filters()

    # OLP_15 - program filter (PM only)
    olp.open_filter_modal()
    programs = olp.program_options()
    olp.close_filter_modal()
    if programs:
        olp.apply_program_filter(programs[0])
        assert olp.filter_badge_count() >= 1
        olp.clear_filters()

    # OLP_16 - filters persist across navigate-away-and-back
    olp.apply_status_filter(["Active"])
    applied = olp.filter_badge_count()
    ConnectHomePage(connect_page).click_programs_in_sidebar()
    connect_page.go_back()
    olp.verify_loaded()
    assert olp.filter_badge_count() == applied, "Filters should survive navigate away/back"
    olp.clear_filters()

    # OLP_22 - combined filters (is_test + status) both honoured
    olp.apply_is_test_and_status("No", ["Active"])
    assert olp.filter_badge_count() >= 2, "Both filters should register on the badge"
    assert all(s == "Active" for s in olp.visible_statuses()), olp.visible_statuses()
    olp.clear_filters()

    # OLP_17/18/19/20 - kebab actions link to the right destinations (by href, no nav)
    hrefs = olp.kebab_item_hrefs(olp.first_row_name())
    assert "worker" in (hrefs.get("View Connect Workers") or ""), hrefs
    assert "invoice" in (hrefs.get("View Invoices") or ""), hrefs
    opp_href = hrefs.get("View Opportunity") or ""
    assert "/opportunity/" in opp_href and "worker" not in opp_href and "invoice" not in opp_href, hrefs

    # OLP_28/29/30 - PM count cells drill down to the right pages, keyed by the
    # sort param the renderer appends (Total Deliveries, Verified Deliveries,
    # Worker Earnings). OLP_27 (Active Connect Workers) links to the worker list.
    assert olp.stats_link_count() > 0, "PM rows should expose clickable count cells"
    assert olp.count_link_count("sort=-delivered") > 0, "Total Deliveries drill-down missing"
    assert olp.count_link_count("sort=-approved") > 0, "Verified Deliveries drill-down missing"
    assert olp.count_link_count("sort=-payment_accrued") > 0, "Worker Earnings drill-down missing"

    # Prove one drill-down actually navigates (OLP_28 Total Deliveries -> delivery tab)
    olp.open_first_count_link("sort=-delivered")
    assert "/opportunity/" in connect_page.url, connect_page.url
    olp._step(f"Total Deliveries drill-down landed on: {connect_page.url}")
