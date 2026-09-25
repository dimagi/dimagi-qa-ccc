"""Invoices List page - "All Invoices" and "Payment Report" tabs
(opportunity/invoice_base.html + invoice_list.html + invoice_payment_report.html).

Both tabs render exactly one django-tables2 base-table
(PaymentInvoiceTable / PaymentReportTable), so the same "first base-table on
the page" xpath used elsewhere in the suite applies to either tab.
"""

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# All Invoices columns (PaymentInvoiceTable.Meta.sequence, tables.py).
ALL_INVOICES_COLUMNS = [
    "Amount",
    "Amount (USD)",
    "Rate",
    "Invoice Generation Date",
    "Invoice number",
    "Invoice Status",
    "Invoice Last Updated Date",
    "Payment Date",
    "Invoice Type",
    "Actions",
]
# Payment Report columns (PaymentReportTable, tables.py).
PAYMENT_REPORT_COLUMNS = [
    "Payment Unit",
    "Approved Units",
    "User Payment Accrued",
    "Network Manager Payment Accrued",
]
# report_cards block order (opportunity/views.py::payment_report).
REPORT_CARD_LABELS = [
    "Connect Worker | Total Accrued",
    "Connect Worker | Total Paid",
    "Organization | Total Accrued",
    "Organization | Total Paid",
]


class InvoiceListPage(BasePage):
    TAB_BY_LABEL = locators.get("connect_invoice_list_page", "tab_by_label")
    ACTIVE_TAB_LABEL = locators.get("connect_invoice_list_page", "active_tab_label")
    CREATE_INVOICE_BUTTON = locators.get("connect_invoice_list_page", "create_invoice_button")
    CREATE_INVOICE_MENU_ITEM_BY_TYPE = locators.get("connect_invoice_list_page", "create_invoice_menu_item_by_type")
    TABLE = locators.get("connect_invoice_list_page", "table")
    TABLE_HEADERS = locators.get("connect_invoice_list_page", "table_headers")
    TABLE_ROWS = locators.get("connect_invoice_list_page", "table_rows")
    EMPTY_TEXT = locators.get("connect_invoice_list_page", "empty_text")
    CURRENCY_TOGGLE_LINKS = locators.get("connect_invoice_list_page", "currency_toggle_links")
    REPORT_CARD_AMOUNTS = locators.get("connect_invoice_list_page", "report_card_amounts")
    REPORT_CARD_META = locators.get("connect_invoice_list_page", "report_card_meta")

    # -- structure / tabs --------------------------------------------------------

    def verify_loaded(self):
        self.page.locator(self.TABLE).first.wait_for(state="visible", timeout=20000)
        assert "/invoice" in self.page.url, f"Not on an invoice page: {self.page.url}"
        self._step(f"Invoice page loaded: {self.page.url}")

    def tabs_present(self, labels=("All Invoices", "Payment Report")):
        present = [label for label in labels if self.page.locator(self.TAB_BY_LABEL.format(label=label)).count() > 0]
        self._step(f"Invoice tabs present: {present}")
        return present

    def active_tab(self):
        return self.page.locator(self.ACTIVE_TAB_LABEL).first.inner_text().strip()

    def open_tab(self, label):
        self._step(f"Open '{label}' tab")
        self.click(self.TAB_BY_LABEL.format(label=label))
        self.page.wait_for_load_state("load")

    # -- All Invoices tab ---------------------------------------------------------

    def create_invoice_button_present(self):
        present = self.page.locator(self.CREATE_INVOICE_BUTTON).count() > 0
        self._step(f"'Create Invoice' button present: {present}")
        return present

    def open_create_invoice(self, invoice_type):
        """invoice_type in {'custom', 'service_delivery'}."""
        self._step(f"Create Invoice -> {invoice_type}")
        self.click(self.CREATE_INVOICE_BUTTON)
        self.click(self.CREATE_INVOICE_MENU_ITEM_BY_TYPE.format(type=invoice_type))
        self.page.wait_for_load_state("load")

    def column_headers(self):
        """Full header list, including any blank <th> (e.g. a row-select column) -
        callers that index into a row's <td>s by column name (row_status) need
        position to stay aligned with the real DOM, not a filtered display list."""
        self.page.locator(self.TABLE_HEADERS).first.wait_for(state="visible", timeout=15000)
        headers = [h.strip() for h in self.page.locator(self.TABLE_HEADERS).all_inner_texts()]
        self._step(f"Invoice table columns: {headers}")
        return headers

    def verify_columns(self, expected):
        headers = self.column_headers()
        joined = " | ".join(headers)
        missing = [c for c in expected if c not in joined]
        assert not missing, f"Missing columns {missing}. Present: {headers}"

    def row_count(self):
        return self.page.locator(self.TABLE_ROWS).count()

    def is_empty(self):
        return self.page.locator(self.EMPTY_TEXT).count() > 0

    def row_by_invoice_number(self, invoice_number):
        row = self.page.locator(
            f"(//table[contains(@class,'base-table')])[1]//tbody//tr[contains(.,'{invoice_number}')]"
        ).first
        row.wait_for(state="visible", timeout=15000)
        return row

    def row_status(self, invoice_number):
        headers = self.column_headers()
        col = headers.index("Invoice Status")
        row = self.row_by_invoice_number(invoice_number)
        text = row.locator("xpath=./td").nth(col).inner_text().strip()
        self._step(f"Invoice {invoice_number} status (list): {text!r}")
        return text

    def open_review(self, invoice_number):
        row = self.row_by_invoice_number(invoice_number)
        self._step(f"Open review for invoice {invoice_number}")
        row.locator("xpath=.//a[normalize-space()='Review']").click()
        self.page.wait_for_load_state("load")

    def pay_from_row(self, invoice_number):
        row = self.row_by_invoice_number(invoice_number)
        button = row.locator("xpath=.//button[normalize-space()='Pay']")
        self._step(f"Pay invoice {invoice_number} from the list row")
        try:
            with self.page.expect_navigation(timeout=20000, wait_until="load"):
                button.click()
        except Exception:
            self._step("no redirect followed - response was re-rendered in place")
        self.page.wait_for_load_state("load")

    def wait_for_invoice_row(self, invoice_number, timeout_s=20):
        """Poll for a newly created/updated invoice to appear (page reload after
        an htmx redirect can lag slightly behind the click that triggered it)."""
        import time

        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            if self.page.locator(
                f"(//table[contains(@class,'base-table')])[1]//tbody//tr[contains(.,'{invoice_number}')]"
            ).count() > 0:
                return True
            self.page.wait_for_timeout(1000)
            self.page.reload()
            self.page.wait_for_load_state("load")
        return False

    # -- Payment Report tab --------------------------------------------------------

    def report_cards(self):
        self.page.locator(self.REPORT_CARD_AMOUNTS).first.wait_for(state="visible", timeout=15000)
        amounts = [a.strip() for a in self.page.locator(self.REPORT_CARD_AMOUNTS).all_inner_texts()]
        meta = [m.strip() for m in self.page.locator(self.REPORT_CARD_META).all_inner_texts()]
        self._step(f"Payment report cards: amounts={amounts} meta={meta}")
        return amounts, meta

    def currency_toggle_labels(self):
        links = self.page.locator(self.CURRENCY_TOGGLE_LINKS)
        return [l.strip() for l in links.all_inner_texts()]

    def active_currency(self):
        """Which of the two currency chips currently carries the active style."""
        links = self.page.locator(self.CURRENCY_TOGGLE_LINKS)
        for i in range(links.count()):
            classes = links.nth(i).get_attribute("class") or ""
            if "chip-active" in classes or links.nth(i).get_attribute("aria-current") == "true":
                return links.nth(i).inner_text().strip()
        return None

    def toggle_to_usd(self):
        links = self.page.locator(self.CURRENCY_TOGGLE_LINKS)
        self._step("Toggle Payment Report to USD")
        links.nth(1).click()
        self.page.wait_for_load_state("load")

    def toggle_to_local(self):
        links = self.page.locator(self.CURRENCY_TOGGLE_LINKS)
        self._step("Toggle Payment Report to local currency")
        links.nth(0).click()
        self.page.wait_for_load_state("load")
