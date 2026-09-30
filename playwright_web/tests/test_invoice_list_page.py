"""Invoices List page (Invoice_01-29, Invoice List_30-37 - CCC_Web_Platform_MTP.xlsx).

Entry is the PM's own opportunity list, opening the dedicated "Invoice Opp"
(INVOICE_LIST.opportunity_name) by exact name; the module skips with a clear
message if it is missing. Role (Network Manager vs Program Manager) is reached by opening the SAME
opp_id under a different org slug, not a UI org-switch - confirmed live against
staging 2026-09-23: an opportunity owned by PM_Automation_01 with "Network
Manager" as its NM partner resolves under both org slugs, and the "Create
Invoice" button (NM-only, invoice_list.html) is present/absent exactly as
expected on each. This also sidesteps ConnectHomePage.select_organization_from_list, whose
generic 'fa-chevron-down' locator collides with the invoice list's own "Create
Invoice" dropdown chevron.

The whole custom-invoice lifecycle (create -> submit -> PM review -> approve ->
pay, plus the cancel and reject side-paths) is self-contained: NM creates the
invoice and PM acts on it within the same run, so none of it needs seeded data.
Because it creates (and pays) invoices, every test that mutates invoice state is
skipped on prod - only the read-only checks run there.

Deferred - need real approved-delivery data (not yet seeded):
  - Invoice_18/19/20/29: Service Delivery invoice creation, its auto-populated
    line items (CompletedWork rows) and their download.
  - Invoice_21-25: automatic monthly invoice generation (a scheduled task, not
    something a test can trigger on demand).
  - Invoice_26/27: "reuse a cancelled/rejected invoice's line items" only means
    something for a Service Delivery invoice - same data gate as above. (What
    IS covered here is the weaker, data-agnostic half of that intent: nothing
    blocks creating a fresh invoice after a prior one was cancelled/rejected.)

One shared module-scoped login/session; tests run in file order, each
continuing from where the previous left off (mirrors the MTP's own
"cont to above TC" steps) - there is no xdist in this suite, so this is safe. If
the test that creates an invoice fails, the tests that continue from it skip
(see _require_invoice) instead of failing with a KeyError.
"""

import datetime

import pytest

from flows.invoices_setup import open_invoice_list, open_invoice_opportunity
from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_invoice_form_page import InvoiceFormPage
from pages.connect_invoice_list_page import InvoiceListPage

# The runner's clock can sit a day either side of the server's (timezone), so the
# expense date is yesterday (never "in the future" for the server) and the
# generation-date check accepts +/-1 day around today.
_TODAY = datetime.date.today()
EXPENSE_DATE = (_TODAY - datetime.timedelta(days=1)).isoformat()
ACCEPTED_GENERATION_DATES = {
    (_TODAY + datetime.timedelta(days=d)).isoformat() for d in (-1, 0, 1)
}

# Tests that create or change invoices: never run against prod.
non_prod_only = pytest.mark.usefixtures("non_prod")


@pytest.fixture
def non_prod(config):
    if config.env == "prod":
        pytest.skip("Creates/approves/pays invoices - never run on prod")


@pytest.fixture(scope="module")
def ctx(browser, config, settings, test_data):
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
        invoice_list = test_data.get("INVOICE_LIST")
        opp_name = env_value(invoice_list, "opportunity_name", config)
        opened = open_invoice_opportunity(connect_page, opp_name) if opp_name else None
        if not opened:
            pytest.skip(
                f"Invoice opportunity {opp_name!r} (INVOICE_LIST.opportunity_name) not found in the PM's "
                "opportunity list - check the name in web_test_data.yaml / that the opp still exists"
            )
        host, pm_slug, opp_id = opened
        state = {
            "connect_page": connect_page,
            "host": host,
            "pm_slug": pm_slug,
            "nm_slug": invoice_list["network_manager_slug"],
            "opp_id": opp_id,
            "opp_name": opp_name,
            "invoices": {},
        }
        yield state
    finally:
        context.close()


def _as_nm(ctx):
    return open_invoice_list(ctx["connect_page"], ctx["host"], ctx["nm_slug"], ctx["opp_id"])


def _as_pm(ctx):
    return open_invoice_list(ctx["connect_page"], ctx["host"], ctx["pm_slug"], ctx["opp_id"])


def _require_invoice(ctx, key):
    """Invoice number an earlier test stored under `key`, or skip this test."""
    number = ctx["invoices"].get(key)
    if not number:
        pytest.skip(f"No '{key}' invoice - the earlier test that creates it did not complete")
    return number


def _create_custom_invoice(ctx, test_data, amount=None):
    """NM creates a Custom invoice and submit()s it, then opens its review page
    (status pending_nm_review). Returns the invoice_number.

    Confirmed live (2026-09-23): a successful create redirects to the All
    Invoices list, not straight to the review page - the deployed build differs
    here from the checked-out product repo's InvoiceCreateView, which appeared
    to imply a review redirect."""
    data = test_data.get("INVOICE_CUSTOM")
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_create_invoice("custom")
    form = InvoiceFormPage(ctx["connect_page"])
    form.verify_create_loaded(service_delivery=False)
    invoice_number = form.invoice_number()
    form.fill_custom_invoice(amount or data["amount"], EXPENSE_DATE, data["justification"])
    form.submit()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_review(invoice_number)
    form.verify_review_loaded()
    return invoice_number


# -- Invoice_01/02: land, tabs, create-button role gating, columns (read-only) --


def test_invoice_01_nm_lands_on_list_with_tabs_and_create_button(ctx, test_data):
    tabs = test_data.get("INVOICE_LIST")["tabs"]
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    present = invoices.tabs_present(tabs)
    assert present == tabs, f"Missing tabs: {present}"
    assert invoices.active_tab() == tabs[0]
    assert invoices.create_invoice_button_present(), "NM should see the 'Create Invoice' button"


def test_invoice_01_pm_does_not_see_create_button(ctx):
    _as_pm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert not invoices.create_invoice_button_present(), "PM should not see 'Create Invoice' (view-enforced too)"


def test_invoice_02_all_invoices_columns(ctx, test_data):
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.verify_columns(test_data.get("INVOICE_LIST")["all_invoices_columns"])


def test_invoice_03_payment_report_cards_and_columns(ctx, test_data):
    data = test_data.get("INVOICE_LIST")
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_tab(data["tabs"][1])
    invoices.verify_columns(data["payment_report_columns"])
    amounts, meta = invoices.report_cards()
    expected = data["report_card_count"]
    assert len(amounts) == expected, f"Expected {expected} report cards, got {amounts}"
    assert len(meta) == expected, f"Expected {expected} report card labels, got {meta}"


def test_invoice_04_usd_toggle(ctx, test_data):
    data = test_data.get("INVOICE_LIST")
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_tab(data["tabs"][1])
    before = invoices.active_currency()
    invoices.toggle_to_usd()
    after_usd = invoices.active_currency()
    assert after_usd and "USD" in after_usd, f"USD pill did not become active: {after_usd!r}"
    assert data["usd_url_param"] in ctx["connect_page"].url
    invoices.toggle_to_local()
    after_local = invoices.active_currency()
    assert after_local == before, f"Local-currency pill did not re-activate: {after_local!r} vs {before!r}"


# -- Invoice_07/17: create-form validation (no invoice ends up created) --------------


@non_prod_only
def test_invoice_07_mandatory_fields_validation(ctx):
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.open_create_invoice("custom")
    form = InvoiceFormPage(ctx["connect_page"])
    form.verify_create_loaded(service_delivery=False)
    create_url = ctx["connect_page"].url
    # amount/date_of_expense/description(Justification) are all required=True for
    # a Custom invoice (forms.py prepare_fields) - Django renders that as an HTML5
    # `required` attribute, so an empty submit is blocked client-side (native
    # "Please fill out this field" validation), never reaching the server.
    for label, selector in (("Amount", form.AMOUNT), ("Date of expense", form.DATE_OF_EXPENSE), ("Justification", form.DESCRIPTION)):
        field = ctx["connect_page"].locator(selector).first
        validity = field.evaluate("el => ({valid: el.checkValidity(), valueMissing: el.validity.valueMissing})")
        assert validity["valueMissing"] or not validity["valid"], f"{label} field is not marked required: {validity}"
    ctx["connect_page"].locator(form.SUBMIT_BUTTON).first.click()
    ctx["connect_page"].wait_for_timeout(500)
    assert ctx["connect_page"].url == create_url, "Blank submit should not have navigated/created the invoice"


@non_prod_only
def test_invoice_17_future_date_of_expense_rejected(ctx, test_data):
    data = test_data.get("INVOICE_CUSTOM")
    future = (datetime.date.today() + datetime.timedelta(days=test_data.get("INVOICE_VALIDATION")["future_days_ahead"])).isoformat()
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.open_create_invoice("custom")
    form = InvoiceFormPage(ctx["connect_page"])
    form.verify_create_loaded(service_delivery=False)
    form.fill_custom_invoice(data["amount"], future, data["justification"])
    form.submit()
    errors = " | ".join(form.field_errors())
    expected = test_data.get("INVOICE_LIST")["future_date_error_text"]
    assert expected in errors.lower(), f"Expected a future-date error, got: {errors!r}"
    assert "/invoice/create/" in ctx["connect_page"].url, "A rejected submit should stay on the create form"


# -- Invoice_06: USD exchange-rate preview (create form, not submitted) --------------


def test_invoice_06_usd_exchange_rate_preview(ctx, test_data):
    data = test_data.get("INVOICE_CUSTOM")
    _as_nm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.open_create_invoice("custom")
    form = InvoiceFormPage(ctx["connect_page"])
    form.verify_create_loaded(service_delivery=False)
    form.type(form.AMOUNT, str(data["amount"]))
    ctx["connect_page"].wait_for_timeout(800)  # convert() is debounced 300ms + an htmx round trip
    preview = form.exchange_rate_preview_text()
    expected = test_data.get("INVOICE_LIST")["exchange_rate_preview_text"]
    assert expected in preview, f"Unexpected exchange-rate preview: {preview!r}"


# -- Invoice_05/08/13 + List_31/09/12/14/List_37/List_32/15/List_36/16/28: -----------
# the approve-and-pay happy path for one Custom invoice, start to finish.


@non_prod_only
def test_invoice_05_create_custom_invoice(ctx, test_data):
    invoice_number = _create_custom_invoice(ctx, test_data)
    form = InvoiceFormPage(ctx["connect_page"])
    assert invoice_number, "Invoice ID should be auto-generated"
    assert form.generation_date() in ACCEPTED_GENERATION_DATES, (
        f"Generation date {form.generation_date()!r} should default to today (+/-1 day for timezone)"
    )
    ctx["invoices"]["approve_and_pay"] = invoice_number


@non_prod_only
def test_invoice_08_status_pending_nm_review_on_create(ctx, test_data):
    _require_invoice(ctx, "approve_and_pay")
    form = InvoiceFormPage(ctx["connect_page"])  # still on the review page from the previous test
    assert form.status_field_value() == test_data.get("INVOICE_STATUS")["pending_nm_review"]


@non_prod_only
def test_invoice_13_nm_cannot_edit_custom_invoice(ctx, test_data):
    _require_invoice(ctx, "approve_and_pay")
    actions = test_data.get("INVOICE_LIST")["actions"]
    form = InvoiceFormPage(ctx["connect_page"])
    assert form.is_read_only(), "Custom-invoice review page should render every field read-only"
    assert set(form.available_actions()) == {actions["cancel"], actions["submit_to_pm"]}


@non_prod_only
def test_invoice_16_28_back_to_invoices_button(ctx, test_data):
    number = _require_invoice(ctx, "approve_and_pay")
    data = test_data.get("INVOICE_LIST")
    form = InvoiceFormPage(ctx["connect_page"])
    form.click_back_to_invoices()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert invoices.active_tab() == data["tabs"][0]
    assert invoices.row_status(number) == test_data.get("INVOICE_STATUS")["pending_nm_review"]
    type_label = data["custom_invoice_type_label"]
    assert type_label in invoices.row_by_invoice_number(number).inner_text(), (
        f"Custom invoice should show Invoice Type '{type_label}'"
    )
    invoices.open_review(number)


@non_prod_only
def test_invoice_09_12_list31_submit_to_program_manager(ctx, test_data):
    number = _require_invoice(ctx, "approve_and_pay")
    # Confirmed live: a successful submit lands on the All Invoices list, not
    # back on the review page (see InvoiceFormPage.submit_to_program_manager).
    form = InvoiceFormPage(ctx["connect_page"])  # positioned on the invoice's review page
    form.submit_to_program_manager()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert invoices.row_status(number) == test_data.get("INVOICE_STATUS")["pending_pm_review"]


@non_prod_only
def test_invoice_14_list37_pm_readonly_review(ctx, test_data):
    number = _require_invoice(ctx, "approve_and_pay")
    actions = test_data.get("INVOICE_LIST")["actions"]
    _as_pm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_review(number)
    form = InvoiceFormPage(ctx["connect_page"])
    form.verify_review_loaded()
    assert form.is_read_only()
    assert form.read_only_badge_present()
    assert form.available_actions() == [actions["reject"], actions["approve"]]


@non_prod_only
def test_invoice_list32_pm_approve_for_payment_processing(ctx, test_data):
    number = _require_invoice(ctx, "approve_and_pay")
    actions = test_data.get("INVOICE_LIST")["actions"]
    # Approve (unlike Submit) has no confirm modal and, like every other action
    # here, redirects to the list rather than staying on the review page.
    form = InvoiceFormPage(ctx["connect_page"])  # still on the PM review page
    form.approve_for_payment_processing()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert invoices.row_status(number) == test_data.get("INVOICE_STATUS")["ready_to_pay"]
    invoices.open_review(number)
    form.verify_review_loaded()
    assert form.available_actions() == [actions["reject"], actions["pay"]]


@non_prod_only
def test_invoice_15_list36_pm_pay(ctx, test_data):
    number = _require_invoice(ctx, "approve_and_pay")
    form = InvoiceFormPage(ctx["connect_page"])  # on the review page (reopened above)
    form.pay()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert invoices.row_status(number) == test_data.get("INVOICE_STATUS")["paid"]
    invoices.open_review(number)
    form.verify_review_loaded()
    assert form.paid_badge_present()


# -- Invoice_10/11 + Invoice_26: cancel, and re-creating after a cancel --------------


@non_prod_only
def test_invoice_10_11_cancel_invoice(ctx, test_data):
    data = test_data.get("INVOICE_LIST")
    status = test_data.get("INVOICE_STATUS")
    invoice_number = _create_custom_invoice(ctx, test_data)
    form = InvoiceFormPage(ctx["connect_page"])

    form.open_cancel_modal()
    message = form.modal_message(data["modals"]["cancel"])
    assert data["irreversible_modal_text"] in message

    # Invoice_11: Close backs out - no status change.
    form.close_cancel_modal()
    assert form.status_field_value() == status["pending_nm_review"]
    assert data["actions"]["cancel"] in form.available_actions()

    # Invoice_10: Cancel Invoice confirms the cancellation (redirects to the list).
    form.open_cancel_modal()
    form.confirm_cancel()
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    assert invoices.row_status(invoice_number) == status["cancelled_by_nm"]
    invoices.open_review(invoice_number)
    form.verify_review_loaded()
    assert form.available_actions() == [], "A cancelled invoice should show no NM/PM actions"
    ctx["invoices"]["cancelled"] = invoice_number


@non_prod_only
def test_invoice_26_create_invoice_after_a_cancelled_one(ctx, test_data):
    cancelled = _require_invoice(ctx, "cancelled")
    invoice_number = _create_custom_invoice(ctx, test_data)
    form = InvoiceFormPage(ctx["connect_page"])
    assert form.status_field_value() == test_data.get("INVOICE_STATUS")["pending_nm_review"]
    assert invoice_number != cancelled
    ctx["invoices"]["after_cancel"] = invoice_number


# -- Invoice List_33/34/35 + Invoice_27: reject, and re-creating after a reject ------


@non_prod_only
def test_invoice_list33_34_35_pm_reject_invoice(ctx, test_data):
    data = test_data.get("INVOICE_LIST")
    status = test_data.get("INVOICE_STATUS")
    invoice_number = _create_custom_invoice(ctx, test_data)
    form = InvoiceFormPage(ctx["connect_page"])
    form.submit_to_program_manager()  # -> lands on the (NM) list

    _as_pm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    invoices.open_review(invoice_number)
    form.verify_review_loaded()

    form.open_reject_modal()
    message = form.modal_message(data["modals"]["reject"])
    assert data["irreversible_modal_text"] in message

    # List_34: Close backs out - no status change.
    form.close_reject_modal()
    assert form.status_field_value() == status["pending_pm_review"]

    # List_33/35: Reject Invoice confirms the rejection (redirects to the list).
    form.open_reject_modal()
    form.confirm_reject()
    invoices.verify_loaded()
    assert invoices.row_status(invoice_number) == status["rejected_by_pm"]
    ctx["invoices"]["rejected"] = invoice_number


@non_prod_only
def test_invoice_27_create_invoice_after_a_rejected_one(ctx, test_data):
    rejected = _require_invoice(ctx, "rejected")
    invoice_number = _create_custom_invoice(ctx, test_data)
    form = InvoiceFormPage(ctx["connect_page"])
    assert form.status_field_value() == test_data.get("INVOICE_STATUS")["pending_nm_review"]
    assert invoice_number != rejected
    ctx["invoices"]["after_reject"] = invoice_number


# -- Invoice List_30: PM sees the invoices created in this run ------------------------


@non_prod_only
def test_invoice_list30_pm_sees_all_invoices(ctx):
    created = ctx["invoices"]
    if not created:
        pytest.skip("No invoices were created in this run - nothing to look for in the PM's list")
    _as_pm(ctx)
    invoices = InvoiceListPage(ctx["connect_page"])
    invoices.verify_loaded()
    missing = {key: number for key, number in created.items() if not invoices.has_invoice(number)}
    assert not missing, f"Invoices created in this run are missing from the PM's list: {missing}"
