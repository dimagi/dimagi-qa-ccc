"""Navigation helpers for the Invoices List page module.

Entry to invoices is the opportunity dashboard's hamburger menu ("View
Invoices"), same as every other opportunity sub-page - there is no dashboard
stat panel for it (unlike workers/deliver/payments).

Role (Network Manager vs Program Manager) is NOT a UI toggle here: Connect
derives request.is_opportunity_pm from the URL's org slug matching the
opportunity's owning Program org (see opportunity/views.py, users/middleware.py).
So reaching the same opportunity as a different org is a matter of navigating
to that org's own URL for the same opp_id - confirmed live (probe against
staging 2026-09-23): the PM_Automation_01-owned "Invoice Opp" (which has the
"Network Manager" org as its NM partner) is reachable under BOTH org slugs for
the same opp_id, and the "Create Invoice"
button is correctly present only under the network-manager slug. This avoids
the fragile UI org-switcher entirely (ConnectHomePage.select_organization_from_list
depends on a page having exactly one 'fa-chevron-down' icon, which the invoice
list page's own "Create Invoice" dropdown chevron collides with).
"""

from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage
from utils.helpers import with_page_size


def open_invoice_opportunity(connect_page, name):
    """Open the dedicated invoice opportunity `name` (exact match) from the PM's
    list. Returns (host, pm_slug, opp_id), or None if it is not in the list so the
    caller can skip with a clear data-problem message instead of acting on some
    other opportunity."""
    connect_page.goto(with_page_size(connect_page.url))
    connect_page.wait_for_load_state("load")
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()
    if not olp.has_opportunity(name, exact=True):
        return None
    olp.open_opportunity(name, exact=True)
    dash = OpportunityDashboardPage(connect_page)
    dash.verify_loaded()
    return dash.base_url_parts()


def open_invoice_list(connect_page, host, org_slug, opp_id):
    """Reach a given org's view of an opportunity's Invoices List (All Invoices
    tab). Returns the OpportunityDashboardPage positioned there."""
    dash = OpportunityDashboardPage(connect_page)
    dash.goto_opp(host, org_slug, opp_id)
    dash.click_hamburger_item("View Invoices")
    return dash
