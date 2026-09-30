"""Payment Processing (Payment Processing_1-4) - the Payments tab.

Ported from the Selenium test_payment_processing_01_02_03 suite:
  Payment Processing_1 - the Payments tab shows the payment columns
  Payment Processing_2 - importing a payment reports a success message
  Payment Processing_3 - the worker's Last paid value opens a payment-history popup
  Payment Processing_4 - the payment can be rolled back (Last paid returns to '—')

This test mutates and self-cleans: it imports a payment for the worker, verifies
the history popup, then rolls the payment back so the worker ends as it began.
The import keys on ConnectID username (opportunity/visit_import.bulk_update_payments),
so covid_opp_test / Deb Test 8/12 (accepted, accrued > 0, never paid) is a valid
target on staging - the original Test Opp 151201 no longer exists there.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from flows.workers_setup import open_payments_tab
from pages.connect_workers_page import ConnectWorkersPage


@pytest.fixture(scope="module")
def connect(browser, config, settings):
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        except Exception:
            page.close()
            page = context.new_page()
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        connect_page.wait_for_load_state("load")
        yield connect_page, connect_page.url
    finally:
        context.close()


def test_payment_processing_01_02_03_04(connect, test_data):
    connect_page, opps_url = connect
    data = test_data.get("PAYMENT_PROCESSING_1_2_3")
    opp, worker = data["opportunity_name"], data["worker_name"]
    workers = ConnectWorkersPage(connect_page)

    open_payments_tab(connect_page, opp, opps_url)
    workers.verify_tab_active("Payments")

    # Payment Processing_1
    workers.verify_payments_table_headers_present()

    # Payment Processing_2 - import a payment and confirm the success message.
    workers.make_payment_for_worker(worker, amount=1)

    # Payment Processing_3 - the Last paid value opens the payment-history popup.
    workers.click_last_paid_and_verify_history(worker)

    # Payment Processing_4 - roll the payment back; Last paid returns to '—'.
    workers.rollback_last_payment()
    workers.verify_last_paid_empty(worker)
