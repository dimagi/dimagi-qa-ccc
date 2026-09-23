"""Navigation helpers for the Invoices List page module.

Entry to invoices is the opportunity dashboard's hamburger menu ("View
Invoices"), same as every other opportunity sub-page - there is no dashboard
stat panel for it (unlike workers/deliver/payments).

Role (Network Manager vs Program Manager) is NOT a UI toggle here: Connect
derives request.is_opportunity_pm from the URL's org slug matching the
opportunity's owning Program org (see opportunity/views.py, users/middleware.py).
So reaching the same opportunity as a different org is a matter of navigating
to that org's own URL for the same opp_id - confirmed live (probe against
staging 2026-09-23): the PM_Automation_01-owned "Demo Opportunity_<date>" flood
(created by the OLP journey tests, which always invite the "Network Manager"
org as NM partner - flows/olp_setup.py:create_program_with_nm_handshake) is
reachable under BOTH org slugs for the same opp_id, and the "Create Invoice"
button is correctly present only under the network-manager slug. This avoids
the fragile UI org-switcher entirely (ConnectHomePage.select_organization_from_list
depends on a page having exactly one 'fa-chevron-down' icon, which the invoice
list page's own "Create Invoice" dropdown chevron collides with).
"""

from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def pick_pm_opportunity(connect_page):
    """Open the PM's opportunity list (page_size=100, same fix as the workers
    module needed - the list has no search and floods with OLP-created demo
    opportunities) and open its first row. Returns (host, pm_slug, opp_id, name).
    """
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()
    base = connect_page.url.split("?")[0]
    connect_page.goto(f"{base}?page_size=100")
    connect_page.wait_for_load_state("load")
    olp.verify_loaded()
    name = olp.first_row_name()
    olp.open_opportunity(name)
    dash = OpportunityDashboardPage(connect_page)
    dash.verify_loaded()
    host, pm_slug, opp_id = dash.base_url_parts()
    return host, pm_slug, opp_id, name


def open_invoice_list(connect_page, host, org_slug, opp_id):
    """Reach a given org's view of an opportunity's Invoices List (All Invoices
    tab). Returns the OpportunityDashboardPage positioned there."""
    dash = OpportunityDashboardPage(connect_page)
    dash.goto_opp(host, org_slug, opp_id)
    dash.click_hamburger_item("View Invoices")
    return dash
