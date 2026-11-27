"""LLO Directory - the Organizations and Contacts tabs under Admin.

Product source: commcare_connect/organization (views, forms, filters, tables) and
templates/organization/directory/*. Pages are not org-scoped (/organizations/...),
need the LLO Directory permission, and add/edit forms open in a [role=dialog] modal
that saves over htmx. Staging is ahead of the web MTP sheet (extra columns, checkbox
filters), so the page object reads headers and control types rather than assuming them.
"""

import re
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.helpers import LocatorLoader, with_page_size

locators = LocatorLoader()
L = "connect_llo_directory_page"


def _loc(name):
    return locators.get(L, name)


def _vis(name):
    """Locator `name` restricted to what is on screen (the page also holds hidden dialogs with the same buttons)."""
    return f"{_loc(name)} >> visible=true"


def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


class LLODirectoryPage(BasePage):
    # -- navigation -----------------------------------------------------------

    def host(self):
        parts = urlsplit(self.page.url)
        return f"{parts.scheme}://{parts.netloc}"

    def url(self, path=""):
        return f"{self.host()}/organizations/{path}"

    # The Organizations/Contacts pages intermittently take over Playwright's 30s default to load
    # on staging; a slow page is not a failure, a page that never loads is.
    NAV_TIMEOUT_MS = 90_000

    def goto(self, url):
        self._step(f"goto {url}")
        try:
            response = self.page.goto(url, wait_until="domcontentloaded", timeout=self.NAV_TIMEOUT_MS)
        except PlaywrightError as exc:
            # A modal save ends in an htmx redirect; a goto that lands while it is still navigating is aborted.
            if "ERR_ABORTED" not in str(exc):
                raise
            self.page.wait_for_load_state("load", timeout=self.NAV_TIMEOUT_MS)
            response = self.page.goto(url, wait_until="domcontentloaded", timeout=self.NAV_TIMEOUT_MS)
        self.page.wait_for_load_state("load", timeout=self.NAV_TIMEOUT_MS)
        return response

    def open_organizations(self, query=""):
        self.goto(self.url() + query)
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=self.NAV_TIMEOUT_MS)

    def open_contacts(self, query=""):
        self.goto(self.url("contacts/") + query)
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=self.NAV_TIMEOUT_MS)

    def status_of(self, url, method="GET", fields=None):
        """HTTP status of a same-origin request (follows redirects)."""
        return self.page.evaluate(
            """async ([url, method, fields]) => {
                const opts = {method, credentials: 'same-origin'};
                if (method === 'POST') {
                    const token = (document.querySelector('input[name=csrfmiddlewaretoken]') || {}).value
                        || (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || '';
                    const body = new URLSearchParams(fields || {});
                    opts.body = body;
                    opts.headers = {'X-CSRFToken': token, 'Content-Type': 'application/x-www-form-urlencoded'};
                }
                return (await fetch(url, opts)).status;
            }""",
            [url, method, fields or {}],
        )

    # -- sidebar / tabs / counts -----------------------------------------------------

    def admin_link_present(self):
        return self.page.locator(_loc("admin_directory_link")).count() > 0

    def tab_count(self, which):
        """Number on the 'Organizations N' / 'Contacts N' tab."""
        text = self.page.locator(f"{_loc(f'tab_{which}')} >> visible=true").first.inner_text()
        return int(re.search(r"(\d[\d,]*)", text).group(1).replace(",", ""))

    def result_count(self):
        """Number in the 'N organizations' / 'N contacts' text above the table."""
        text = self.page.locator(_vis("result_count_text")).first.inner_text()
        return int(re.search(r"(\d[\d,]*)", text).group(1).replace(",", ""))

    # -- table ---------------------------------------------------------------------

    def headers(self):
        return [" ".join(h.split()) for h in self.page.locator(_loc("table_headers")).all_inner_texts()]

    def header_matching(self, *candidates):
        """The first header that equals/contains one of `candidates` (envs name some differently)."""
        headers = self.headers()
        for candidate in candidates:
            for h in headers:
                if h == candidate or candidate in h:
                    return h
        return None

    def row_count(self):
        return self.page.locator(_loc("table_rows")).count()

    def rows(self):
        headers = self.headers()
        out = []
        for row in self.page.locator(_loc("table_rows")).all():
            cells = [" ".join(c.split()) for c in row.locator("td").all_inner_texts()]
            out.append(dict(zip(headers, cells)))
        return out

    def column(self, header):
        return [r.get(header, "") for r in self.rows()]

    def has_row(self, name):
        return self.page.locator(_loc("row_by_name").format(name=name)).count() > 0

    def row(self, name):
        return self.page.locator(_loc("row_by_name").format(name=name)).first

    def row_values(self, name):
        headers = self.headers()
        cells = [" ".join(c.split()) for c in self.row(name).locator("td").all_inner_texts()]
        return dict(zip(headers, cells))

    def first_row_name(self):
        return self.page.locator(_loc("table_rows")).first.locator("td").first.inner_text().strip()

    def sort_by(self, header):
        self._step(f"sort by {header}")
        self.click(_loc("header_sort_link").format(header=header))
        self.page.wait_for_load_state("load")

    def sortable(self, header):
        return self.page.locator(_loc("header_sort_link").format(header=header)).count() > 0

    def empty_text_shown(self, text):
        return self.has_text(text)

    def has_text(self, text, timeout=5000):
        try:
            self.page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    def body_text(self):
        return self.page.locator("body").inner_text()

    def hover_status_info(self):
        """Hover the Status info icon; callers wait for the tooltip text (has_text) rather than a fixed pause."""
        self.page.locator(_loc("status_info_icon")).first.hover()

    def has_mailto_link(self, name, email):
        """Whether `name`'s row links its email as a mailto: link."""
        return self.row(name).locator(_loc("mailto_link_by_email").format(email=email)).count() == 1

    def rendered_markup_count(self):
        """Bold elements inside the table cells: names containing <b> must be shown as text, not rendered."""
        return self.page.locator(_loc("table_cell_bold")).count()

    # -- filters --------------------------------------------------------------------

    def search(self, text):
        self.page.locator(_loc("filter_search")).fill(text)
        self.apply_filters()

    def apply_filters(self):
        self._step("Apply filters")
        self.page.locator(_vis("filter_apply")).first.click()
        self.page.wait_for_load_state("load")
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=self.NAV_TIMEOUT_MS)

    def reset_filters(self):
        """Prod has a 'Reset' link; staging has none, so its unfiltered listing is reopened instead."""
        self._step("Reset filters")
        if self.has_reset():
            self.page.locator(_vis("filter_reset")).first.click()
            self.page.wait_for_load_state("load")
        else:
            self.goto(self.url("contacts/") if "/contacts/" in self.page.url else self.url())
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=self.NAV_TIMEOUT_MS)

    def has_reset(self):
        return self.page.locator(_vis("filter_reset")).count() > 0

    def set_filter_multiselect(self, field, labels):
        """TomSelect multi-filter (countries / primary_sectors / status / organization_status)."""
        self.page.evaluate(
            """([id, labels]) => {
                const s = document.querySelector('#' + id);
                const vals = labels.map(l => { const o = [...s.options].find(o => o.text.trim() === l);
                    if (!o) throw new Error('no option ' + l + ' in #' + id); return o.value; });
                s.tomselect.setValue(vals);
            }""",
            [f"id_{field}", labels],
        )

    def set_filter_toggle(self, field, on):
        """Contacts' Main POC / Archived filters: a checkbox on staging, a Yes/No dropdown on prod."""
        element = self.page.locator(f"#id_{field}").first
        tag = element.evaluate("e => e.tagName")
        if tag == "SELECT":
            element.evaluate(
                "(e, on) => { const t = e.tomselect; const v = on ? 'true' : ''; if (t) t.setValue(v); else e.value = v; }",
                on,
            )
        elif element.is_checked() != on:
            element.set_checked(on)

    def filter_toggle_kind(self, field):
        return self.page.locator(f"#id_{field}").first.evaluate("e => e.tagName + ':' + (e.type || '')")

    # -- modals ---------------------------------------------------------------------

    def modal_visible(self):
        return self.page.locator(_vis("modal")).count() > 0

    def edit_url(self, name):
        """The edit form URL behind a row's Edit control (it is an htmx hx-get, not an href)."""
        button = self.page.locator(_loc("edit_button_by_name").format(name=name)).first
        return button.get_attribute("hx-get") or button.get_attribute("href")

    def wait_modal(self, field="name"):
        self.page.locator(_loc("org_field").format(field=field)).wait_for(state="visible", timeout=15000)

    def open_add_org(self):
        self._step("Add Organization")
        self.page.locator(_vis("add_org_button")).first.click()
        self.wait_modal("short_name")

    def open_add_contact(self):
        self._step("Add Contact")
        self.page.locator(_vis("add_contact_button")).first.click()
        self.wait_modal("email")

    def open_edit(self, name):
        self._step(f"Edit {name}")
        self.page.locator(_loc("edit_button_by_name").format(name=name)).first.click()
        self.wait_modal("name" if "contacts" not in self.page.url else "email")

    def modal_value(self, field):
        return self.page.locator(_loc("org_field").format(field=field)).input_value()

    def modal_tomselect_labels(self, field):
        return self.page.evaluate(
            "id => { const s = document.querySelector('[role=dialog] #' + id); const t = s.tomselect;"
            " const v = [].concat(t ? t.getValue() : s.value); return [...s.options].filter(o => v.includes(o.value))"
            ".map(o => o.text.trim()); }",
            f"id_{field}",
        )

    def modal_select_text(self, field):
        return self.page.evaluate(
            "id => { const s = document.querySelector('[role=dialog] #' + id); const o = s.options[s.selectedIndex];"
            " return o ? o.text.trim() : ''; }",
            f"id_{field}",
        )

    def modal_options(self, field):
        return self.page.evaluate(
            "id => [...document.querySelector('[role=dialog] #' + id).options].map(o => o.text.trim())", f"id_{field}"
        )

    def fill_modal(self, **values):
        """Fill any subset of fields in the open modal (org or contact form)."""
        for key, value in values.items():
            if value is None:
                continue
            selector = _loc("org_field").format(field=key)
            element = self.page.locator(selector)
            tag = element.evaluate("e => e.tagName")
            if tag == "SELECT":
                self._set_select(key, value)
            elif tag == "TEXTAREA" and not element.is_visible():
                # Emails and links are tag inputs now (Enter/comma/space per entry) with the real
                # field hidden behind them. These tests feed raw multi-line text to check the
                # server's cleaning and validation, so set the field itself, as fill() used to.
                self._step(f"set hidden #{key} (tag input in front of it)")
                element.evaluate(
                    "(e, v) => { e.value = v; e.dispatchEvent(new Event('input', {bubbles: true})); "
                    "e.dispatchEvent(new Event('change', {bubbles: true})); }",
                    str(value),
                )
            else:
                element.fill(str(value))

    def _set_select(self, field, value):
        self._step(f"select {value!r} in #{field}")
        self.page.evaluate(
            """([id, value]) => {
                const s = document.querySelector('[role=dialog] #' + id);
                const wanted = [].concat(value);
                const slug = v => v.toLowerCase().replace(/[^a-z0-9]+/g, '-');
                const vals = wanted.map(w => { const o = [...s.options].find(o => o.text.trim() === w)
                    || [...s.options].find(o => o.text.trim().toLowerCase() === w.toLowerCase())
                    || [...s.options].find(o => o.text.trim() === slug(w));
                    if (!o) throw new Error('no option ' + w + ' in #' + id); return o.value; });
                if (s.tomselect) s.tomselect.setValue(s.multiple ? vals : vals[0]);
                else { s.value = vals[0]; s.dispatchEvent(new Event('change', {bubbles: true})); }
            }""",
            [f"id_{field}", value],
        )

    def select_by_index(self, field, index):
        self.page.evaluate(
            """([id, index]) => { const s = document.querySelector('[role=dialog] #' + id);
                const vals = [s.options[index].value]; s.tomselect.setValue(s.multiple ? vals : vals[0]); }""",
            [f"id_{field}", index],
        )

    def modal_save(self, server_validated=False):
        if server_validated:
            self.page.evaluate("document.querySelectorAll('form').forEach(f => f.noValidate = true)")
        self._step("Save modal")
        self.page.locator(_vis("modal_save")).first.click()
        self._wait_htmx_idle()

    def _wait_htmx_idle(self, timeout=15000):
        """Wait for the save's htmx request and the swap of its response to finish. Nothing to wait
        for when the browser's own validation blocked the submit (no request was sent)."""
        try:
            self.page.wait_for_function(
                "() => !document.querySelector('.htmx-request, .htmx-swapping, .htmx-settling')", timeout=timeout
            )
        except PlaywrightTimeoutError:
            raise
        except PlaywrightError:
            # A save that ends in an HX-Redirect navigates away mid-wait; the next page's load is the signal.
            self.page.wait_for_load_state("load", timeout=self.NAV_TIMEOUT_MS)

    def wait_modal_closed(self, timeout=15000):
        self.page.wait_for_function(
            "() => ![...document.querySelectorAll('[role=dialog]')].some(d => d.offsetParent !== null)", timeout=timeout
        )
        self.page.wait_for_load_state("load")

    def modal_error_text(self):
        return self.page.locator(_vis("modal_text")).first.inner_text()

    def modal_invalid_fields(self):
        """Names of modal fields the browser flags as invalid (native required/format checks)."""
        return self.page.evaluate(
            "() => [...document.querySelectorAll('[role=dialog] :invalid')].map(e => e.id.replace('id_', ''))"
        )

    def close_modal(self, how):
        if how == "cancel":
            self.page.locator(_vis("modal_cancel")).first.click()
        elif how == "x":
            self.page.locator(_vis("modal_close_x")).first.click()
        elif how == "escape":
            self.page.keyboard.press("Escape")
        elif how == "outside":
            self.page.mouse.click(5, 5)
        # Wait for the dialog to go; if it never does, the caller's own check reports which way failed.
        try:
            self.page.locator(_vis("modal")).first.wait_for(state="hidden", timeout=5000)
        except PlaywrightTimeoutError:
            pass

    # -- high level: organizations -------------------------------------------------------

    def create_org(self, name, short_name, country, sector_index=1, regions="Region X", **extra):
        self.open_organizations()
        self.open_add_org()
        self.fill_modal(name=name, short_name=short_name, regions=regions, **extra)
        self._set_select("countries", [country])
        self.select_by_index("primary_sectors", sector_index)
        self.modal_save()
        self.wait_modal_closed()

    # -- high level: contacts ------------------------------------------------------------

    def create_contact(self, name, org_name, email, title, phone, notes, poc=False):
        self.open_contacts()
        self.open_add_contact()
        self.fill_modal(name=name, title=title, email=email, phone=phone, notes=notes)
        self._set_select("organization", org_name)
        self._set_select("is_main_poc", "Yes" if poc else "No")
        self.modal_save()
        self.wait_modal_closed()

    def open_archive_dialog(self, name):
        """Click a contact's Archive control and wait for the confirm dialog."""
        self.page.locator(_loc("archive_button_by_name").format(name=name)).first.click()
        self.page.locator(_vis("archive_confirm")).first.wait_for(state="visible", timeout=10000)

    def archive_contact(self, name, confirm=True):
        self.open_archive_dialog(name)
        if confirm:
            self.page.locator(_vis("archive_confirm")).first.click()
            self.page.wait_for_load_state("load")
        else:
            self.close_modal("cancel")

    def archive_dialog_text(self):
        return self.page.locator(_vis("modal_text")).first.inner_text()

    def restore_contact(self, name):
        self.page.locator(_loc("restore_button_by_name").format(name=name)).first.click()
        self.page.wait_for_load_state("load")

    def contact_actions(self, name):
        labels = self.row(name).locator("a, button").evaluate_all(
            "els => els.map(e => (e.getAttribute('aria-label') || e.innerText || '').trim())"
        )
        return [l for l in labels if l]

    # -- export --------------------------------------------------------------------------

    def export(self, fmt, timeout=90000):
        """Run Export contacts in `fmt` ('CSV' / 'Excel') and return the downloaded file's path."""
        self._step(f"Export contacts as {fmt}")
        button = self.page.locator(_vis("export_open_button")).first
        try:
            button.wait_for(state="visible", timeout=15000)
        except PlaywrightTimeoutError:
            self._step(f"Export button not found on {self.page.url}; visible controls: "
                       f"{self.page.locator('button:visible, a.button:visible').all_inner_texts()[:20]}")
            raise
        button.click()
        self.page.locator(f"#{_loc('export_format').lstrip('#')}").wait_for(state="visible")
        self.page.locator(_loc("export_format")).select_option(label=fmt)
        self.page.locator(_vis("export_submit")).first.click()
        link = self.page.locator(_vis("export_download_link")).first
        link.wait_for(state="visible", timeout=timeout)
        with self.page.expect_download(timeout=timeout) as dl:
            link.click()
        return dl.value
