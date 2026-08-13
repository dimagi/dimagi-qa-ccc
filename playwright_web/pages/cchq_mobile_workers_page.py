from pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader()

# Statuses the "PersonalID Status" column is allowed to show.
VALID_PERSONALID_STATUSES = {"Active", "Not Linked", "Inactive"}


class MobileWorkersPage(BasePage):
    """Users > Mobile Workers page on CommCare HQ.

    Covers the Personal ID link/unlink admin surface (test cases PID_56-59):
    the "PersonalID Status" column, the "Unlink PersonalID" action, and its
    confirmation modal.
    """

    WORKER_TABLE = locators.get("cchq_mobile_workers_page", "worker_table")
    STATUS_HEADER = locators.get("cchq_mobile_workers_page", "personalid_status_header")
    STATUS_LABELS = locators.get("cchq_mobile_workers_page", "personalid_status_labels")
    UNLINK_BUTTON = locators.get("cchq_mobile_workers_page", "unlink_button")
    LINK_BUTTON = locators.get("cchq_mobile_workers_page", "link_button")
    UNLINK_MODAL = locators.get("cchq_mobile_workers_page", "unlink_modal")
    UNLINK_MODAL_TITLE = locators.get("cchq_mobile_workers_page", "unlink_modal_title")
    UNLINK_MODAL_CANCEL = locators.get("cchq_mobile_workers_page", "unlink_modal_cancel")
    UNLINK_MODAL_CONFIRM = locators.get("cchq_mobile_workers_page", "unlink_modal_confirm")

    @staticmethod
    def mobile_workers_url(config):
        """Derive the Mobile Workers URL from the configured cchq login URL.

        cchq_url is '.../a/<domain>/login/'; the workers list lives at
        '.../a/<domain>/settings/users/commcare/'.
        """
        cchq_url = config.get("cchq_url")
        base = cchq_url.split("/login/")[0]
        return f"{base}/settings/users/commcare/"

    def open(self, config):
        url = self.mobile_workers_url(config)
        self._step(f"open mobile workers page {url}")
        self.page.goto(url, wait_until="load")
        # Worker rows are rendered client-side (knockout) - wait for the table.
        self.page.locator(self.WORKER_TABLE).first.wait_for(state="visible", timeout=30000)
        self.page.wait_for_timeout(3000)

    # --- PID_56: PersonalID Status column present with valid values ---
    def verify_personalid_status_column_present(self):
        assert self.is_displayed(self.STATUS_HEADER), (
            "'PersonalID Status' column header not found on Mobile Workers page"
        )
        self._step("PersonalID Status column present")

    def get_visible_personalid_statuses(self):
        labels = self.page.locator(self.STATUS_LABELS)
        values = []
        for i in range(labels.count()):
            el = labels.nth(i)
            if el.is_visible():
                values.append(el.inner_text().strip())
        return values

    def verify_personalid_statuses_are_valid(self):
        statuses = self.get_visible_personalid_statuses()
        assert statuses, "No PersonalID status values rendered in the column"
        invalid = [s for s in statuses if s not in VALID_PERSONALID_STATUSES]
        assert not invalid, f"Unexpected PersonalID status value(s): {invalid}"
        self._step(f"PersonalID statuses valid: {sorted(set(statuses))}")

    # --- PID_57: Unlink PersonalID action present for linked (Active) workers ---
    def verify_unlink_button_present(self):
        count = self.page.locator(self.UNLINK_BUTTON).count()
        assert count > 0, "No 'Unlink PersonalID' action button found for any worker"
        self._step(f"found {count} 'Unlink PersonalID' action button(s)")

    # --- Row lookup by a human identifier (username or first name text) ---
    def _worker_row(self, identifier):
        row = self.page.locator(self.WORKER_TABLE).locator(
            "tbody tr", has_text=identifier
        ).first
        assert row.count() > 0, f"No mobile-worker row matching '{identifier}'"
        return row

    # --- PID_58: clicking Unlink shows the confirmation modal (Cancel/Unlink) ---
    def open_unlink_confirmation_for_first_worker(self):
        self._step("click first 'Unlink PersonalID' action")
        self.page.locator(self.UNLINK_BUTTON).first.click()
        # One hidden modal is pre-rendered per worker; wait for the one that opened.
        title = self.page.locator(self.UNLINK_MODAL_TITLE).locator("visible=true").first
        title.wait_for(state="visible", timeout=10000)

    def verify_unlink_confirmation_modal(self):
        title = self.page.locator(self.UNLINK_MODAL_TITLE).locator("visible=true").first
        assert title.is_visible(), "Unlink confirmation modal title not visible"
        modal = self.page.locator(self.UNLINK_MODAL).locator("visible=true").first
        body = modal.inner_text()
        assert "unlink the PersonalID account for this mobile worker" in body, (
            f"Confirmation message not found in modal. Got: {body[:200]}"
        )
        assert self.page.locator(self.UNLINK_MODAL_CANCEL).locator("visible=true").count() > 0, (
            "'Cancel' option missing from unlink modal"
        )
        assert self.page.locator(self.UNLINK_MODAL_CONFIRM).locator("visible=true").count() > 0, (
            "'Unlink' confirm option missing from unlink modal"
        )
        self._step("unlink confirmation modal shows message + Cancel/Unlink options")

    def cancel_unlink(self):
        self._step("click Cancel on unlink modal (non-destructive)")
        self.page.locator(self.UNLINK_MODAL_CANCEL).locator("visible=true").first.click()
        self.page.wait_for_timeout(1000)

    # --- PID_59 (destructive): unlink ONE dedicated worker, by identifier. ---
    def open_unlink_confirmation_for_worker(self, identifier):
        """Open the unlink modal for a specific worker (username or first name),
        so an automated unlink never touches an unrelated worker."""
        self._step(f"click 'Unlink PersonalID' for worker '{identifier}'")
        row = self._worker_row(identifier)
        row.locator("xpath=.//button[contains(normalize-space(),'Unlink PersonalID')]").first.click()
        self.page.locator(self.UNLINK_MODAL_TITLE).locator("visible=true").first.wait_for(
            state="visible", timeout=10000
        )

    def worker_personalid_status(self, identifier):
        """PersonalID status label for a worker, or None if that worker row is
        not present on the page (used to skip PID_59 gracefully)."""
        row = self.page.locator(self.WORKER_TABLE).locator(
            "tbody tr", has_text=identifier
        ).first
        if row.count() == 0:
            return None
        labels = row.locator("span.label")
        for i in range(labels.count()):
            if labels.nth(i).is_visible():
                return labels.nth(i).inner_text().strip()
        return None

    def confirm_unlink(self):
        self._step("click Unlink to confirm (DESTRUCTIVE - unlinks the worker)")
        self.page.locator(self.UNLINK_MODAL_CONFIRM).locator("visible=true").first.click()
        self.page.wait_for_timeout(2000)
