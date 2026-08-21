"""Programs List page - Tier 1 (structural / deterministic).

The PM Programs List (program/pm_home.html) is a stack of program cards, not a
table. Create/invite/apply/accept are already exercised by the OLP setup flow via
ConnectProgramsPage; this file asserts the *list page's own* read surface without
creating data, so it stays fast and rerunnable.

Manual case map (CCC Web Platform [Master] sheet, Programs List page):
  PLP_03/10 card summary fields, PLP_05 acceptance funnel, PLP_06 NM statuses,
  PLP_11/17 View Opportunities.
Not on this page (separate program/opportunity dashboard template): PLP_08, PLP_09,
PLP_12, PLP_14, PLP_15 - tracked separately.
"""

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_home_page import ConnectHomePage
from pages.connect_programs_page import ConnectProgramsPage

# Application badge vocabulary from pm_home.html.
APPLICATION_STATUSES = {"Invited", "Applied", "Accepted", "Rejected", "Declined"}


def test_plp_program_manager_list(page, test_data, config, settings):
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    home = ConnectHomePage(connect_page)
    programs = ConnectProgramsPage(connect_page)

    # PLP_03 - land on the programs list
    home.click_programs_in_sidebar()

    if programs.program_cards().count() == 0:
        programs._step("No programs for PM org - skipping (needs >=1 program)")
        return

    name = programs.first_program_name()

    # PLP_03/10 - summary fields, and PLP_05 - the acceptance funnel
    programs.verify_card_summary_fields(name)
    programs.acceptance_funnel(name)

    # PLP_12/14/15 - Recent Activities right panel. Category titles are data-driven
    # ("Pending Review", "Pending Invoices", ...); each row links to its worker/opp
    # destination, so the href proves the drill-down target without navigating away.
    titles = programs.recent_activity_titles()
    for title in titles:
        hrefs = programs.recent_activity_row_hrefs(title)
        assert all(h and "/a/" in h for h in hrefs), f"'{title}' has a row without a valid link: {hrefs}"
    if not titles:
        programs._step("Recent Activities panel empty - skipping PLP_12/14/15")

    # PLP_06 - NM application statuses (View Status renders only with applications)
    if programs.has_view_status(name):
        programs.open_view_status(name)
        statuses = programs.nm_application_statuses(name)
        assert all(s in APPLICATION_STATUSES for s in statuses), f"Unexpected NM status: {statuses}"

        # PLP_11/17 - View Opportunities appears against an accepted NM and jumps
        # to that program's opportunity list.
        if programs.has_view_opportunities(name):
            programs.click_view_opportunities(name)
            assert "/opportunity/" in connect_page.url and "program=" in connect_page.url, connect_page.url
            programs._step(f"View Opportunities landed on: {connect_page.url}")
        else:
            programs._step("No accepted NM - View Opportunities not shown (skipping PLP_11/17)")
    else:
        programs._step("Program has no applications - View Status absent (skipping PLP_06/11/17)")
