"""Solicitations (PM org) - list, the four creation steps, and invitations.

Product source: commcare_connect/solicitation/{views,forms,tables}.py and
templates/solicitation/*. The list is org-scoped (org_pm_required + SOLICITATIONS
switch), each step saves to the draft, and an Active solicitation locks its
criteria/questions (Details stays editable, deadline can only move later).

The org slug is taken from the URL the session is already on, so the pages work
for whichever org the test logged into.
"""

import re
from urllib.parse import urlsplit

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from pages.base_page import BasePage
from utils.helpers import LocatorLoader, with_page_size

locators = LocatorLoader()
L = "connect_solicitations_page"


def _loc(name):
    return locators.get(L, name)


def _id(name):
    """Bare DOM id for a form-field locator (LocatorLoader returns it as '#id')."""
    return _loc(name).lstrip("#")


class SolicitationsPage(BasePage):
    # -- navigation -----------------------------------------------------------

    def org_base(self):
        """https://<host>/a/<org-slug>/ for the org the session is on."""
        parts = urlsplit(self.page.url)
        slug = re.search(r"/a/([^/]+)/", parts.path).group(1)
        return f"{parts.scheme}://{parts.netloc}/a/{slug}"

    def url(self, *segments):
        tail = "/".join(s.strip("/") for s in segments if s)
        return f"{self.org_base()}/solicitations/{tail + '/' if tail else ''}"

    def goto(self, url):
        self._step(f"goto {url}")
        response = self.page.goto(url)
        self.page.wait_for_load_state("load")
        return response

    def open_list(self, page_size=100):
        self.goto(with_page_size(self.url(), page_size))
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=20000)

    def open_list_via_sidebar(self):
        self._step("click Solicitations in the sidebar")
        self.page.locator(f"{_loc('sidebar_link')} >> visible=true").first.click()
        self.page.wait_for_load_state("load")

    def sidebar_has_solicitations(self):
        return self.page.locator(_loc("sidebar_link")).count() > 0

    def sidebar_labels(self):
        return [t.strip() for t in self.page.locator("a").all_inner_texts() if t.strip()]

    # -- list ---------------------------------------------------------------------

    def list_headers(self):
        return [h.strip() for h in self.page.locator(_loc("table_headers")).all_inner_texts()]

    def list_titles(self):
        """Titles in table order (the table is newest-first)."""
        return [r.locator("td").first.inner_text().strip() for r in self.page.locator(_loc("table_rows")).all()]

    def list_row_count(self):
        return self.page.locator(_loc("table_rows")).count()

    def is_list_empty(self):
        return self.page.locator(_loc("empty_text")).count() > 0

    def row(self, title):
        return self.page.locator(_loc("row_by_title").format(title=title)).first

    def row_values(self, title):
        headers = self.list_headers()
        cells = [c.strip() for c in self.row(title).locator("td").all_inner_texts()]
        return dict(zip(headers, cells))

    def has_row(self, title):
        return self.page.locator(_loc("row_by_title").format(title=title)).count() > 0

    def _column_index(self, header):
        return self.list_headers().index(header) + 1

    def title_link_href(self, title):
        link = self.row(title).locator(_loc("row_title_link"))
        return link.first.get_attribute("href") if link.count() else None

    def invited_link_href(self, title):
        col = self._column_index("Invited")
        link = self.row(title).locator(_loc("row_invited_link").format(col=col))
        return link.first.get_attribute("href") if link.count() else None

    def rows_by_status(self, status):
        """Titles of rows whose Status badge reads `status` (Draft/Active/Closed/Cancelled)."""
        col = self._column_index("Status")
        titles = []
        for row in self.page.locator(_loc("table_rows")).all():
            cells = row.locator("td")
            if cells.count() >= col and cells.nth(col - 1).inner_text().strip() == status:
                titles.append(cells.first.inner_text().strip())
        return titles

    def click_new_solicitation(self):
        self.click(_loc("new_button"))
        self.page.wait_for_load_state("load")
        self.page.locator(_loc("form_title")).first.wait_for(state="visible")

    # -- messages / errors ----------------------------------------------------------

    def body_text(self):
        return self.page.locator("body").inner_text()

    def has_text(self, text, timeout=5000):
        try:
            self.page.get_by_text(text, exact=False).first.wait_for(state="visible", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            return False

    # -- stepper ------------------------------------------------------------------

    def stepper_labels(self):
        return [re.sub(r"^\d+\s*", "", t.strip()).strip() for t in self.page.locator(_loc("stepper")).all_inner_texts()]

    def stepper_hrefs(self):
        return {
            re.sub(r"^\d+\s*", "", a.inner_text().strip()).strip(): a.get_attribute("href")
            for a in self.page.locator(_loc("stepper")).all()
        }

    def active_step(self):
        return self.page.locator(_loc("stepper_active")).first.inner_text().strip()

    def go_to_step(self, label):
        self.click(_loc("stepper_by_label").format(label=label))
        self.page.wait_for_load_state("load")

    # -- Details step ---------------------------------------------------------------

    TEXT_FIELDS = {
        "title": "form_title",
        "description": "form_description",
        "budget_min": "form_budget_min",
        "budget_max": "form_budget_max",
        "scale": "form_scale",
        "contact_email": "form_contact_email",
        "start_date": "form_start_date",
        "end_date": "form_end_date",
        "deadline": "form_deadline",
    }
    TOMSELECT_FIELDS = {"currency": "form_currency", "country": "form_country", "program": "form_program",
                        "delivery_type": "form_delivery_type"}

    def set_tomselect(self, select_id, label):
        self._step(f"TomSelect #{select_id} -> '{label}'")
        self.page.wait_for_function("id => !!document.getElementById(id) && !!document.getElementById(id).tomselect",
                                    arg=select_id)
        self.page.evaluate(
            """([id, label]) => {
                const s = document.getElementById(id);
                const o = [...s.options].find(o => o.text.trim() === label)
                       || [...s.options].find(o => o.text.includes(label));
                if (!o) throw new Error('no option ' + label + ' in #' + id);
                s.tomselect.setValue(o.value);
            }""",
            [select_id, label],
        )

    def tomselect_option_labels(self, select_id):
        return self.page.evaluate(
            "id => [...document.getElementById(id).options].map(o => o.text.trim()).filter(t => t && !/^-+$/.test(t))",
            select_id,
        )

    def fill_details(self, **values):
        """Fill any subset of the Details fields. Keys: title, type_label, description,
        budget_min, budget_max, currency, country, scale, contact_email, start_date,
        end_date, deadline, program, delivery_type, public (bool), hide_scores (bool)."""
        for key, field in self.TEXT_FIELDS.items():
            if key in values and values[key] is not None:
                self.page.locator(_loc(field)).fill(str(values[key]))
        if values.get("type_label"):
            self.page.locator(_loc('form_type')).select_option(label=values["type_label"])
        for key, field in self.TOMSELECT_FIELDS.items():
            if values.get(key):
                self.set_tomselect(_id(field), values[key])
        for key, field in (("public", "form_public"), ("hide_scores", "form_hide_scores")):
            if key in values and values[key] is not None:
                box = self.page.locator(_loc(field))
                if box.is_checked() != values[key]:
                    box.set_checked(values[key])

    def details_values(self):
        """Current Details form values (as rendered, for the 'reopen shows saved values' check)."""
        def val(field):
            return self.page.locator(_loc(field)).input_value()

        return {
            "title": val("form_title"),
            "type": val("form_type"),
            "currency": self.page.evaluate("id => document.getElementById(id).tomselect.getValue()", _id("form_currency")),
            "deadline": val("form_deadline"),
            "public": self.page.locator(_loc('form_public')).is_checked(),
            "hide_scores": self.page.locator(_loc('form_hide_scores')).is_checked(),
            "contact_email": val("form_contact_email"),
            "description": val("form_description"),
        }

    def selected_delivery_type(self):
        return self.page.evaluate(
            "id => { const s = document.getElementById(id); const o = s.options[s.selectedIndex]; return o ? o.text.trim() : '' }",
            _id("form_delivery_type"),
        )

    def deadline_value(self):
        return self.page.locator(_loc('form_deadline')).input_value()

    def set_deadline_raw(self, value):
        """Type a value as a user would (fires the input event the whole-hour snap listens to)."""
        field = self.page.locator(_loc('form_deadline'))
        field.fill(value)
        field.dispatch_event("input")

    def save_and_continue(self):
        self._step("Save and continue")
        self.click(_loc("save_and_continue"))
        self.page.wait_for_load_state("load")

    def save_and_continue_server_validated(self):
        """Submit past the browser's own min/max/required checks so the SERVER's validation
        messages are what the test sees (the inputs carry native constraints that would
        otherwise block the submit before it reaches the view)."""
        self._step("Save and continue (browser validation off - server rules under test)")
        self.page.evaluate("document.querySelectorAll('form').forEach(f => f.noValidate = true)")
        self.click(_loc("save_and_continue"))
        self.page.wait_for_load_state("load")

    def save_details_in_place(self):
        self._step("Save (active solicitation details)")
        self.click(_loc("save_button"))
        self.page.wait_for_load_state("load")

    def solicitation_id_from_url(self):
        match = re.search(r"/solicitations/([0-9a-f-]{36})/", self.page.url)
        return match.group(1) if match else None

    def click_cancel(self):
        self.click(_loc("cancel_link"))
        self.page.wait_for_load_state("load")

    def click_back(self):
        self.click(_loc("back_link"))
        self.page.wait_for_load_state("load")

    def has_save_and_continue(self):
        return self.page.locator(_loc("save_and_continue")).count() > 0

    def has_save_button(self):
        return self.page.locator(_loc("save_button")).count() > 0

    # -- formset steps (criteria / questions) ---------------------------------------

    def row_count_in_form(self, prefix):
        return self.page.locator(f"[name^='{prefix}-'][name$='-label'], [name^='{prefix}-'][name$='-text']").count()

    def add_row(self):
        self.click(_loc("add_row_button"))

    def add_criterion(self, index, label, weight, description=None):
        self.add_row()
        self.page.locator(f"#id_criteria-{index}-label").fill(label)
        self.page.locator(f"#id_criteria-{index}-weight").fill(str(weight))
        if description:
            self.page.locator(f"#id_criteria-{index}-description").fill(description)

    def remove_row(self, n):
        """Click the n-th (1-based) visible Remove button."""
        self.click(_loc("remove_row_button").format(n=n))

    def criterion_values(self, index):
        return (
            self.page.locator(f"#id_criteria-{index}-label").input_value(),
            self.page.locator(f"#id_criteria-{index}-weight").input_value(),
        )

    def visible_criterion_labels(self):
        return [
            el.input_value()
            for el in self.page.locator("input[name^='criteria-'][name$='-label']:visible").all()
        ]

    def add_question(self, index, text, type_label, options=None, required=True, criterion=None):
        self.add_row()
        self.page.locator(f"#id_questions-{index}-text").fill(text)
        self.page.locator(f"#id_questions-{index}-question_type").select_option(label=type_label)
        if options is not None:
            self.page.locator(f"#id_questions-{index}-choice_options").fill(options)
        box = self.page.locator(f"#id_questions-{index}-required")
        if box.is_checked() != required:
            box.set_checked(required)
        if criterion:
            self.set_tomselect(f"id_questions-{index}-criterion", criterion)

    def choice_options_visible(self, index):
        return self.page.locator(f"#id_questions-{index}-choice_options").is_visible()

    def select_question_type(self, index, type_label):
        self.page.locator(f"#id_questions-{index}-question_type").select_option(label=type_label)

    def criterion_choices(self, index):
        return self.tomselect_option_labels(f"id_questions-{index}-criterion")

    def visible_question_criterion(self, index):
        return self.page.evaluate(
            "id => { const s = document.getElementById(id); const o = s.options[s.selectedIndex]; return o && o.value ? o.text.trim() : '' }",
            f"id_questions-{index}-criterion",
        )

    def is_read_only(self):
        """Criteria/questions step of an Active solicitation: no add/remove, fields disabled."""
        no_add = self.page.locator(_loc("add_row_button")).count() == 0
        fields = self.page.locator("form input[name^='criteria-'], form input[name^='questions-'], "
                                   "form textarea[name^='questions-'], form select[name^='questions-']")
        disabled = [f.is_disabled() for f in fields.all() if f.get_attribute("type") != "hidden"]
        return no_add and bool(disabled) and all(disabled)

    def locked_hint_present(self):
        return self.page.locator(_loc("locked_hint")).count() > 0

    # -- Review & publish ---------------------------------------------------------

    def review_text(self):
        return self.page.locator("div.container").first.inner_text()

    def publish_disabled(self):
        return self.page.locator(_loc("publish_button")).first.is_disabled()

    def publish_button_present(self):
        return self.page.locator(_loc("publish_button")).count() > 0

    def publish_blockers(self):
        return [t.strip() for t in self.page.locator(_loc("publish_alert_items")).all_inner_texts()]

    def blocker_fix_hrefs(self):
        return [a.get_attribute("href") for a in self.page.locator(_loc("publish_fix_links")).all()]

    def publish(self):
        self._step("Publish")
        self.click(_loc("publish_button"))
        self.page.wait_for_load_state("load")

    def invited_orgs_button_present(self):
        return self.page.locator(_loc("invited_org_button")).count() > 0

    # -- raw requests (server-side guards the UI hides) -----------------------------

    def post_form(self, url, fields):
        """POST urlencoded `fields` to `url` from the page's own session, with its CSRF token.
        Returns (status, final_url)."""
        return self.page.evaluate(
            """async ([url, fields]) => {
                const token = document.querySelector('input[name=csrfmiddlewaretoken]').value;
                const body = new URLSearchParams(fields);
                body.set('csrfmiddlewaretoken', token);
                const r = await fetch(url, {method: 'POST', body, credentials: 'same-origin',
                    headers: {'Content-Type': 'application/x-www-form-urlencoded', 'X-CSRFToken': token},
                    redirect: 'follow'});
                return [r.status, r.url];
            }""",
            [url, fields],
        )

    def get_status(self, url):
        return self.page.evaluate(
            "async url => (await fetch(url, {credentials: 'same-origin', redirect: 'manual'})).status", url
        )

    def status_of(self, url):
        """HTTP status for a GET navigated like a browser (follows redirects)."""
        return self.page.evaluate(
            "async url => (await fetch(url, {credentials: 'same-origin'})).status", url
        )


class SolicitationInvitationsPage(SolicitationsPage):
    """.../solicitations/<id>/invitations/ - table + 'Invite organizations' modal."""

    def verify_loaded(self):
        self.page.locator(_loc("table")).first.wait_for(state="visible", timeout=20000)
        assert "/invitations/" in self.page.url, f"Not on invitations page: {self.page.url}"

    def hint_text(self):
        return self.page.locator(_loc("invitations_hint")).first.inner_text().strip()

    def invited_orgs(self):
        return [
            r.locator("td").nth(2).inner_text().strip() for r in self.page.locator(_loc("invitation_rows")).all()
        ]

    def invitation_table_rows(self):
        headers = [h.strip() for h in self.page.locator(_loc("table_headers")).all_inner_texts()]
        out = []
        for r in self.page.locator(_loc("invitation_rows")).all():
            out.append(dict(zip(headers, [c.strip() for c in r.locator("td").all_inner_texts()])))
        return out

    def is_empty(self):
        return self.page.locator(_loc("invitations_empty")).count() > 0

    def open_invite_modal(self):
        self.click(_loc("invite_plus_button"))
        self.page.locator(_loc('invite_orgs_select')).wait_for(state="attached")
        self.page.wait_for_function(
            "id => !!document.getElementById(id).tomselect", arg=_id("invite_orgs_select")
        )

    def offered_orgs(self):
        return self.tomselect_option_labels(_id("invite_orgs_select"))

    def pick_orgs(self, names):
        for name in names:
            self._step(f"pick org '{name}'")
            self.page.evaluate(
                """([id, name]) => {
                    const s = document.getElementById(id);
                    const o = [...s.options].find(o => o.text.trim() === name);
                    if (!o) throw new Error('org not offered: ' + name);
                    s.tomselect.addItem(o.value);
                }""",
                [_id("invite_orgs_select"), name],
            )

    def submit_invite(self, server_validated=False):
        if server_validated:
            # The select is `required`, so the browser would block an empty submit before the
            # server's own 'This field is required.' message could be seen.
            self.page.evaluate("document.querySelectorAll('form').forEach(f => f.noValidate = true)")
        self.click(_loc("invite_submit"))
        self.page.wait_for_load_state("load")

    def invite(self, names):
        self.open_invite_modal()
        self.pick_orgs(names)
        self.submit_invite()

    def tick_org(self, org):
        self.page.locator(_loc("invitation_row_by_org").format(org=org)).first.locator(
            _loc("invitation_row_checkbox")
        ).check()

    def click_remove_icon(self):
        self.click(_loc("remove_invitations_button"))

    def confirm_modal_visible(self):
        return self.page.locator(_loc("confirm_modal_text")).first.is_visible()

    def confirm_modal_message(self):
        return " ".join(self.page.locator(_loc("confirm_modal_text")).last.inner_text().split())

    def confirm_remove(self):
        self.click(_loc("confirm_remove_button"))
        self.page.wait_for_load_state("load")

    def cancel_remove(self):
        self.click(_loc("confirm_cancel_button"))

    def invite_required_error_shown(self, text="This field is required."):
        return self.has_text(text)
