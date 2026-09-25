"""Invoice create + review form (opportunity/invoice_create.html and
invoice_detail.html both render AutomatedPaymentInvoiceForm through the same
crispy layout, so one page object covers both - only the action bar at the
bottom differs, and only invoice_detail.html has one).

Status workflow (opportunity/utils/invoice.py::InvoiceWorkflow), for reference:
  pending_nm_review -> pending_pm_review (NM submits) or cancelled_by_nm (NM cancels)
  pending_pm_review -> ready_to_pay (PM approves) or rejected_by_pm (PM rejects)
  ready_to_pay      -> rejected_by_pm (PM can still reject before paying)
  (paid is reached only via the separate Pay action/invoice_pay view)
"""

from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# get_status_display() label strings (InvoiceStatus, opportunity/models.py).
STATUS_LABELS = {
    "pending_nm_review": "Pending Network Manager Review",
    "pending_pm_review": "Pending Program Manager Review",
    "cancelled_by_nm": "Cancelled by Network Manager",
    "ready_to_pay": "Ready to Pay",
    "rejected_by_pm": "Rejected by Program Manager",
    "paid": "Paid",
    "archived": "Archived",
}


class InvoiceFormPage(BasePage):
    INVOICE_NUMBER = locators.get("connect_invoice_form_page", "invoice_number_field")
    DATE = locators.get("connect_invoice_form_page", "date_field")
    TITLE = locators.get("connect_invoice_form_page", "title_field")
    START_DATE = locators.get("connect_invoice_form_page", "start_date_field")
    END_DATE = locators.get("connect_invoice_form_page", "end_date_field")
    AMOUNT = locators.get("connect_invoice_form_page", "amount_field")
    AMOUNT_USD = locators.get("connect_invoice_form_page", "amount_usd_field")
    USD_CURRENCY_CHECKBOX = locators.get("connect_invoice_form_page", "usd_currency_checkbox")
    DATE_OF_EXPENSE = locators.get("connect_invoice_form_page", "date_of_expense_field")
    DESCRIPTION = locators.get("connect_invoice_form_page", "description_field")
    STATUS_FIELD = locators.get("connect_invoice_form_page", "status_field")
    SUBMIT_BUTTON = locators.get("connect_invoice_form_page", "submit_button")
    EXCHANGE_RATE_DISPLAY = locators.get("connect_invoice_form_page", "exchange_rate_display")
    BACK_TO_INVOICES = locators.get("connect_invoice_form_page", "back_to_invoices_link")
    DOWNLOAD_LINK = locators.get("connect_invoice_form_page", "download_link")
    READ_ONLY_BADGE = locators.get("connect_invoice_form_page", "read_only_badge")
    PAID_BADGE = locators.get("connect_invoice_form_page", "paid_badge")
    CANCEL_LINK = locators.get("connect_invoice_form_page", "cancel_action_link")
    SUBMIT_TO_PM_LINK = locators.get("connect_invoice_form_page", "submit_to_pm_link")
    REJECT_LINK = locators.get("connect_invoice_form_page", "reject_action_link")
    APPROVE_LINK = locators.get("connect_invoice_form_page", "approve_action_link")
    PAY_BUTTON = locators.get("connect_invoice_form_page", "pay_button")
    MODAL_BY_NAME = locators.get("connect_invoice_form_page", "modal_by_name")
    MODAL_CONFIRM_BUTTON = locators.get("connect_invoice_form_page", "modal_confirm_button")
    MODAL_CLOSE_BUTTON = locators.get("connect_invoice_form_page", "modal_close_button")
    FIELD_ERROR_TEXT = locators.get("connect_invoice_form_page", "field_error_text")

    # -- create ---------------------------------------------------------------

    def verify_create_loaded(self, service_delivery):
        field = self.START_DATE if service_delivery else self.DATE_OF_EXPENSE
        self.page.locator(field).first.wait_for(state="visible", timeout=15000)
        self._step(f"Invoice create form loaded (service_delivery={service_delivery}): {self.page.url}")

    def invoice_number(self):
        return self.page.locator(self.INVOICE_NUMBER).first.input_value().strip()

    def generation_date(self):
        return self.page.locator(self.DATE).first.input_value().strip()

    def fill_custom_invoice(self, amount, date_of_expense, justification):
        self.type(self.AMOUNT, str(amount))
        self.enter_date(self.DATE_OF_EXPENSE, date_of_expense)
        self.type(self.DESCRIPTION, justification)

    def submit(self):
        self._step("Submit invoice create form")
        with self.page.expect_navigation(wait_until="load"):
            self.click(self.SUBMIT_BUTTON)

    def field_errors(self):
        return [e.strip() for e in self.page.locator(self.FIELD_ERROR_TEXT).all_inner_texts() if e.strip()]

    def toggle_usd_currency(self, checked):
        box = self.page.locator(self.USD_CURRENCY_CHECKBOX).first
        if box.is_checked() != checked:
            box.click()

    def exchange_rate_preview_text(self):
        self.page.locator(self.EXCHANGE_RATE_DISPLAY).first.wait_for(state="visible", timeout=10000)
        return self.page.locator(self.EXCHANGE_RATE_DISPLAY).first.inner_text().strip()

    # -- review / detail --------------------------------------------------------

    def verify_review_loaded(self):
        self.page.locator(self.STATUS_FIELD).first.wait_for(state="visible", timeout=15000)
        self._step(f"Invoice review page loaded: {self.page.url}")

    def status_field_value(self):
        return self.page.locator(self.STATUS_FIELD).first.input_value().strip()

    def is_read_only(self):
        """Every field on the review page carries the readonly attribute except
        the one carve-out (service-delivery description while pending_nm_review
        and viewed by NM, see forms.py prepare_fields)."""
        return self.page.locator(self.AMOUNT).first.get_attribute("readonly") is not None

    def is_field_editable(self, field_selector):
        return self.page.locator(field_selector).first.get_attribute("readonly") is None

    def read_only_badge_present(self):
        return self.page.locator(self.READ_ONLY_BADGE).count() > 0

    def paid_badge_present(self):
        return self.page.locator(self.PAID_BADGE).count() > 0

    def available_actions(self):
        actions = {
            "Cancel": self.CANCEL_LINK,
            "Submit to Program Manager": self.SUBMIT_TO_PM_LINK,
            "Reject": self.REJECT_LINK,
            "Approve for Payment Processing": self.APPROVE_LINK,
            "Pay": self.PAY_BUTTON,
        }
        present = [name for name, sel in actions.items() if self.page.locator(sel).count() > 0]
        self._step(f"Available review-page actions: {present}")
        return present

    def click_back_to_invoices(self):
        self._step("Back to Invoices")
        self.click(self.BACK_TO_INVOICES)
        self.page.wait_for_load_state("load")

    # -- NM: submit / cancel -----------------------------------------------------

    def submit_to_program_manager(self):
        """Confirmed live (2026-09-23): unlike Cancel/Reject, "Submit to Program
        Manager" opens a "Certify and submit invoice" modal (showSubmitModal)
        with a required certification checkbox gating its confirm button - not
        reflected in the checked-out product repo's invoice_form_handler.html,
        which shows a plain submitInvoice() call with no modal. A successful
        submit lands on the All Invoices list, not back on this review page."""
        self._step("Open 'Submit to Program Manager' certify modal")
        self.click(self.SUBMIT_TO_PM_LINK)
        modal = self.page.locator(self.MODAL_BY_NAME.format(name="showSubmitModal")).first
        modal.wait_for(state="visible", timeout=10000)
        modal.locator("xpath=.//input[@type='checkbox']").first.check()
        self._step("Confirm 'Certify & Submit'")
        with self.page.expect_navigation(wait_until="load", timeout=20000):
            modal.locator("xpath=.//button[contains(normalize-space(),'Certify')]").first.click()

    def open_cancel_modal(self):
        self._step("Open cancel-invoice modal")
        self.click(self.CANCEL_LINK)
        self.page.locator(self.MODAL_BY_NAME.format(name="showCancelModal")).first.wait_for(
            state="visible", timeout=10000
        )

    def close_cancel_modal(self):
        self.click(self.MODAL_CLOSE_BUTTON.format(name="showCancelModal"))
        self.page.wait_for_timeout(500)

    def confirm_cancel(self):
        self._step("Confirm cancel invoice")
        self.click_and_await_redirect(self.MODAL_CONFIRM_BUTTON.format(name="showCancelModal"))

    # -- PM: approve / reject / pay -----------------------------------------------

    def approve_for_payment_processing(self):
        self._step("Approve for Payment Processing")
        self.click_and_await_redirect(self.APPROVE_LINK)

    def open_reject_modal(self):
        self._step("Open reject-invoice modal")
        self.click(self.REJECT_LINK)
        self.page.locator(self.MODAL_BY_NAME.format(name="showRejectModal")).first.wait_for(
            state="visible", timeout=10000
        )

    def close_reject_modal(self):
        self.click(self.MODAL_CLOSE_BUTTON.format(name="showRejectModal"))
        self.page.wait_for_timeout(500)

    def confirm_reject(self):
        self._step("Confirm reject invoice")
        self.click_and_await_redirect(self.MODAL_CONFIRM_BUTTON.format(name="showRejectModal"))

    def pay(self):
        self._step("Pay invoice (from review page)")
        self.click_and_await_redirect(self.PAY_BUTTON)

    def modal_message(self, modal_name):
        modal = self.page.locator(self.MODAL_BY_NAME.format(name=modal_name)).first
        return modal.inner_text().strip()
