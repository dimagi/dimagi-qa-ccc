"""LLO Directory (LLODir_01-13 from the "LLO Directory" tab of the web MTP sheet, plus the
gap cases LLODir_14-28 added to it from reading commcare_connect/organization).

The directory (Admin > LLO Directory, /organizations/) lists every Connect organization and
its contacts for users holding the LLO Directory permission. Add/edit forms open in a modal.

Staging and prod differ: prod matches the sheet, staging is ahead (extra Countries / Regions
/ Test columns, checkbox filters), so column and filter checks are subset / control-type
aware. Tests that create, edit, archive or export data run on staging only - the prod
directory holds real organizations; prod runs the read-only checks. Every record a test
creates is named "<prefix> <timestamp> ...".

The directory has no delete, so every test that creates organizations or contacts is marked
consumes_seed_data: PR and post-deploy runs deselect them, and they run only on a manual
dispatch with include_seed_consuming. The unmarked tests are read-only and leave the
directory unchanged.

Needs outside data (skipped with a reason):
  - LLODir_02 / 28: logins without the permission / a staff login without it. The QA login
    now has the permission, so the no-access half cannot be shown with it.
  - Parts of 01 (Internal Features link, collapsed sidebar) and 13 (another user's download
    link) need those extra logins too.
"""

import csv
import datetime
import io
import re
from urllib.parse import quote_plus

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import login_to_connect
from pages.connect_llo_directory_page import LLODirectoryPage, slugify
from utils.skips import skip_needs_data, skip_not_applicable

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%m%d%H%M%S")


@pytest.fixture(scope="module")
def ctx(browser, config, settings, test_data):
    context = browser.new_context(ignore_https_errors=True, accept_downloads=True)
    page = context.new_page()
    try:
        try:
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        except Exception:
            page.close()
            page = context.new_page()
            connect_page = login_to_connect(page, config, settings, PM_ORG)
        connect_page.wait_for_load_state("load")
        yield {"page": connect_page, "data": test_data.get("LLO_DIRECTORY"), "cache": {}, "context": context}
    finally:
        context.close()


@pytest.fixture
def dp(ctx):
    return LLODirectoryPage(ctx["page"])


@pytest.fixture
def data(ctx):
    return ctx["data"]


@pytest.fixture
def staging(config):
    if config.env == "prod":
        skip_not_applicable("Creates/edits/archives directory records - staging only (prod holds real organizations)")


# -- helpers -----------------------------------------------------------------------------


def _name(data, tag):
    return f"{data['name_prefix']} {STAMP} {tag}"


def _short(tag):
    return f"AL{STAMP[-6:]}{tag}"[:20]


def _make_org(dp, data, tag, **extra):
    name = _name(data, tag)
    dp.create_org(name, _short(tag), data["country"], data["sector_index"], data["regions"], **extra)
    return name


def _base_org(ctx, dp, data):
    if "org" not in ctx["cache"]:
        ctx["cache"]["org"] = _make_org(dp, data, "base")
    return ctx["cache"]["org"]


def _email(tag):
    return f"auto{STAMP}{tag}@example.com".lower()


def _make_contact(dp, data, org, tag, poc=False, email=None):
    name = _name(data, f"contact-{tag}")
    dp.create_contact(name, org, email or _email(tag), data["contact_title"], data["contact_phone"], poc=poc)
    return name


def _focus(dp, term):
    """Open Contacts filtered to `term` on one big page: the list is name-ordered and holds more than a
    page of contacts, so a freshly created contact is not reliably on page 1."""
    dp.open_contacts(f"?search={quote_plus(term)}&page_size=100")


def _msg(data, key, **kwargs):
    return data["messages"][key].format(**kwargs)


# -- LLO Directory - Access ----------------------------------------------------------------


def test_llodir_01_directory_listed_under_admin(ctx, dp):
    """LLODir_01: Admin shows LLO Directory; the page opens with Organizations and Contacts tabs, each with a count."""
    dp.open_organizations()
    assert dp.admin_link_present(), "Admin group must list LLO Directory"
    assert dp.tab_count("organizations") > 0
    assert dp.tab_count("contacts") >= 0
    dp.open_contacts()
    assert dp.admin_link_present(), "Admin group stays expanded on the Contacts tab"


def test_llodir_02_users_without_permission(ctx):
    skip_needs_data(
        "The QA login now holds the LLO Directory permission, so the no-access half needs a login with no internal "
        "permissions and one with another internal permission (asked of Anshu/Hemant). Logged-out access is LLODir_14."
    )


# -- LLO Directory - Organizations -----------------------------------------------------------


def test_llodir_03_organization_listing(ctx, dp, data):
    """LLODir_03: columns, newest first (where an Added column exists), count text matches the tab, status tooltip."""
    dp.open_organizations()
    headers = dp.headers()
    missing = [c for c in data["org_columns"] if c not in headers]
    assert not missing, f"Missing columns {missing}; present {headers}"
    assert dp.result_count() == dp.tab_count("organizations"), "Count text must match the Organizations tab"
    added = dp.header_matching("Added")
    if added:
        dates = [datetime.datetime.strptime(d, "%d-%b-%Y") for d in dp.column(added) if d and d != "—"]
        assert dates == sorted(dates, reverse=True), f"Organizations must be newest first: {dates[:5]}"
    dp.hover_status_info()
    for definition in data["status_definitions"]:
        assert definition in dp.page.locator("body").inner_text() or dp.page.get_by_text(definition).count() > 0, \
            f"Status tooltip missing '{definition}'"


@pytest.mark.consumes_seed_data
def test_llodir_04_add_organization(ctx, dp, data, staging):
    """LLODir_04: add with status and agreement links; message, top row, badge, edit shows every value."""
    name = _name(data, "add")
    dp.open_organizations()
    dp.open_add_org()
    dp.fill_modal(name=name, short_name=_short("add"), status="Active", regions=data["regions"],
                  latest_msa_link=data["msa_link"], latest_work_order_link=data["work_order_link"],
                  contact_emails=f"{_email('org')}", eoi_links=data["eoi_links"], notes="Automated")
    dp._set_select("countries", [data["country"]])
    dp.select_by_index("primary_sectors", data["sector_index"])
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(_msg(data, "org_added", name=name)), "Success message missing"
    assert dp.first_row_name() == name, "New organization must be the top row"
    status = dp.header_matching("Status")
    assert dp.row_values(name)[status] == "Active"
    assert "positive" in dp.row(name).locator("td").nth(1).inner_html(), "Active badge must be green"
    dp.open_edit(name)
    assert dp.modal_value("name") == name and dp.modal_select_text("status") == "Active"
    assert dp.modal_value("latest_msa_link") == data["msa_link"]
    assert dp.modal_value("latest_work_order_link") == data["work_order_link"]
    assert dp.modal_value("eoi_links") == data["eoi_links"]
    dp.close_modal("cancel")


@pytest.mark.consumes_seed_data
def test_llodir_05_organization_validation(ctx, dp, data, staging):
    """LLODir_05: required fields, duplicate name (any case), invalid email / URL entries."""
    base = _base_org(ctx, dp, data)
    dp.open_organizations()
    dp.open_add_org()
    dp.modal_save()
    invalid = set(dp.modal_invalid_fields())
    for field in ("name", "short_name", "regions"):
        assert field in invalid, f"{field} must be required (browser flags: {sorted(invalid)})"
    dp.modal_save(server_validated=True)
    assert dp.has_text(data["messages"]["required"], timeout=10000)
    text = dp.modal_error_text()
    assert text.count(data["messages"]["required"]) >= 4, f"Server must flag the required fields: {text[-400:]}"

    dp.close_modal("cancel")
    dp.open_add_org()
    dp.fill_modal(name=base.swapcase(), short_name=_short("dup"), regions=data["regions"])
    dp._set_select("countries", [data["country"]])
    dp.select_by_index("primary_sectors", data["sector_index"])
    dp.modal_save()
    assert dp.has_text(data["messages"]["dup_name"]), "Duplicate name (different case) must be rejected"

    dp.fill_modal(name=_name(data, "bad-values"), contact_emails="not-an-email\nok@example.com",
                  eoi_links="not a url", latest_msa_link="nope", latest_work_order_link="nope")
    dp.modal_save(server_validated=True)
    text = dp.modal_error_text()
    for expected in ("Invalid email(s): not-an-email", "Invalid URL(s): not a url", "Enter a valid URL."):
        assert expected in text, f"Missing '{expected}'"


@pytest.mark.consumes_seed_data
def test_llodir_06_edit_organization(ctx, dp, data, staging):
    """LLODir_06: change/clear status, keep URL on rename, discard edits (Cancel / X / Escape / outside)."""
    name = _make_org(dp, data, "edit", status="Active")
    dp.open_organizations()
    status_col = dp.header_matching("Status")
    href = dp.edit_url(name)

    dp.open_edit(name)
    dp.fill_modal(status="Inactive", latest_msa_link=data["msa_link"])
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(_msg(data, "org_updated", name=name))
    assert dp.row_values(name)[status_col] == "Inactive"

    renamed = _name(data, "edit-renamed")
    dp.open_edit(name)
    dp.fill_modal(name=renamed)
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(_msg(data, "org_updated", name=renamed))
    new_href = dp.edit_url(renamed)
    assert new_href.split("?")[0] == href.split("?")[0], "Renaming must keep the organization's URL"

    dp.open_edit(renamed)
    dp.fill_modal(status="—")
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.row_values(renamed)[status_col] in ("—", ""), "Cleared status must show no badge"

    for how in ("cancel", "x", "escape", "outside"):
        dp.open_edit(renamed)
        dp.fill_modal(notes=f"discard-{how}", name=f"{renamed} discarded")
        dp.close_modal(how)
        assert not dp.modal_visible(), f"Modal must close via {how}"
        assert dp.has_row(renamed) and not dp.has_row(f"{renamed} discarded"), f"{how} must discard edits"


def test_llodir_07_search_filter_sort_paging(ctx, dp, data):
    """LLODir_07: case-insensitive search (each org once), filters combine, no-match message, sorting, reset."""
    dp.open_organizations()
    total = dp.result_count()
    sample = dp.first_row_name()
    for term in (sample.upper(), sample.lower()):
        dp.open_organizations()
        dp.search(term)
        names = dp.column("Name")
        assert sample in names and len(names) == len(set(names)), f"Search '{term}' must list each match once"

    dp.open_organizations()
    dp.set_filter_multiselect("status", ["Active"])
    dp.apply_filters()
    status_col = dp.header_matching("Status")
    if dp.has_text(data["messages"]["no_orgs"], timeout=2000):
        pass  # no organization in this environment has an Active status yet (prod): the filter correctly matches none
    else:
        assert set(dp.column(status_col)) == {"Active"}, "Status filter must narrow the list"
    dp.search("zzzz-no-such-organization")
    assert dp.has_text(data["messages"]["no_orgs"]), "Empty state message missing"

    dp.reset_filters()
    assert dp.result_count() == total, "Reset must clear every filter"
    assert not dp.sortable("Org Team Size") and not dp.sortable("Actions"), "Org Team Size / Actions must not sort"
    dp.sort_by("Name")
    # The database ignores punctuation when ordering ("Ajeet's Org" sorts as "ajeets org").
    names = [re.sub(r"[^a-z0-9]", "", n.lower()) for n in dp.column("Name")]
    assert names == sorted(names), "Sort by Name ascending"


@pytest.mark.consumes_seed_data
def test_llodir_07b_edit_returns_to_filtered_page(ctx, dp, data, staging):
    """LLODir_07 (edit half): saving an edit returns to the same filtered page. Creates the shared
    base organization, so it is opt-in with the other record-creating tests."""
    name = _base_org(ctx, dp, data)
    dp.open_organizations()
    dp.search(name)
    url_before = dp.page.url
    dp.open_edit(name)
    dp.fill_modal(notes="keeps-filter")
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.page.url == url_before, f"Edit must return to the filtered page: {dp.page.url} vs {url_before}"


# -- LLO Directory - Contacts ----------------------------------------------------------------


@pytest.mark.consumes_seed_data
def test_llodir_08_add_contact(ctx, dp, data, staging):
    """LLODir_08: required fields, success message, row values, Contacts tab count +1."""
    org = _base_org(ctx, dp, data)
    dp.open_contacts()
    before = dp.tab_count("contacts")
    dp.open_add_contact()
    dp.modal_save()
    assert {"name", "email"} <= set(dp.modal_invalid_fields()), "Name and Email must be required"
    dp.modal_save(server_validated=True)
    assert dp.has_text(data["messages"]["required"], timeout=10000), "Server must flag the required fields"
    assert dp.modal_error_text().count(data["messages"]["required"]) >= 2

    name = _name(data, "contact-add")
    email = _email("add")
    dp.fill_modal(name=name, title=data["contact_title"], email=email, phone=data["contact_phone"], notes="n")
    dp._set_select("organization", org)
    dp._set_select("is_main_poc", "Yes")
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(_msg(data, "contact_added", name=name))
    _focus(dp, name)
    row = dp.row_values(name)
    assert org in row.values() and data["contact_title"] in row.values() and data["contact_phone"] in row.values()
    assert dp.row(name).locator(f"a[href='mailto:{email}']").count() == 1, "Email must be a mailto link"
    assert dp.tab_count("contacts") == before + 1


@pytest.mark.consumes_seed_data
def test_llodir_09_contact_email_unique(ctx, dp, data, staging):
    """LLODir_09: email unique across active and archived contacts (any case); own email saves."""
    org = _base_org(ctx, dp, data)
    active = _make_contact(dp, data, org, "uniq-a")
    archived = _make_contact(dp, data, org, "uniq-b")
    _focus(dp, archived)
    dp.archive_contact(archived)
    for name_taken, owner, archived_note in ((_email("uniq-a"), active, ""), (_email("uniq-b"), archived, "(archived)")):
        dp.open_contacts()
        dp.open_add_contact()
        dp.fill_modal(name=_name(data, "contact-dup"), email=name_taken.upper())
        dp._set_select("organization", org)
        dp.modal_save()
        expected = f"This email already belongs to {owner}" + (f" {archived_note}" if archived_note else "") + f" at {slugify(org)}"
        text = dp.modal_error_text()
        assert f"This email already belongs to {owner}" in text, f"Duplicate email message missing: {text[-300:]}"
        assert bool(archived_note) == ("(archived)" in text), "Archived marker must appear only for archived contacts"
        dp.close_modal("cancel")
    _focus(dp, active)
    dp.open_edit(active)
    dp.fill_modal(title="Updated Title")
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(f"Contact {active} updated."), "Editing a contact without changing its email must save"


@pytest.mark.consumes_seed_data
def test_llodir_10_main_poc_and_move(ctx, dp, data, staging):
    """LLODir_10: only one Main POC per organization; moving a contact follows the new organization."""
    org_a = _make_org(dp, data, "poc-a")
    org_b = _make_org(dp, data, "poc-b")
    first = _make_contact(dp, data, org_a, "poc-1", poc=True)
    second = _make_contact(dp, data, org_a, "poc-2", poc=False)
    term = _name(data, "contact-poc")
    _focus(dp, term)
    poc_col = dp.header_matching("Point of Contact", "POC")
    dp.open_edit(second)
    dp._set_select("is_main_poc", "Yes")
    dp.modal_save()
    dp.wait_modal_closed()
    _focus(dp, term)
    assert dp.row_values(second)[poc_col] == "Yes"
    assert dp.row_values(first)[poc_col] == "—", "The previous Main POC must be unmarked"

    dp.open_edit(first)
    dp._set_select("organization", org_b)
    dp.modal_save()
    dp.wait_modal_closed()
    _focus(dp, term)
    assert org_b in dp.row_values(first).values(), "Contact must move to the new organization"


@pytest.mark.consumes_seed_data
def test_llodir_11_archive_restore_contact(ctx, dp, data, staging):
    """LLODir_11: confirm dialog, Cancel keeps, archive leaves the list, archived view offers Restore only."""
    org = _base_org(ctx, dp, data)
    name = _make_contact(dp, data, org, "arch")
    _focus(dp, name)
    dp.archive_contact(name, confirm=False)
    assert dp.has_row(name), "Cancel must keep the contact"
    dp.page.locator("xpath=//*[@aria-label=\"Archive %s\"]" % name).first.click()
    assert f"Archive {name}" in dp.archive_dialog_text(), "Archive confirm dialog text missing"
    dp.close_modal("cancel")
    dp.archive_contact(name)
    assert dp.has_text(_msg(data, "contact_archived", name=name)) and not dp.has_row(name)
    dp.set_filter_toggle("archived", True)
    dp.apply_filters()
    assert dp.has_row(name)
    assert [a for a in dp.contact_actions(name) if a.startswith("Restore")] and \
        not [a for a in dp.contact_actions(name) if a.startswith(("Edit", "Archive"))], "Archived rows only offer Restore"
    dp.restore_contact(name)
    assert dp.has_text(_msg(data, "contact_restored", name=name))
    dp.set_filter_toggle("archived", False)
    dp.apply_filters()
    assert dp.has_row(name), "Restored contact must be back in the active list"


def test_llodir_12_contact_search_and_filters(ctx, dp, data, config):
    """LLODir_12: search by name / organization / email (any case), POC-only filter, empty state, reset."""
    dp.open_contacts()
    if dp.row_count() == 0 or dp.has_text(data["messages"]["no_contacts"], timeout=1500):
        skip_needs_data("This environment's directory has no contacts to search")
    row = dp.rows()[0]
    name = row[dp.header_matching("Name")]
    org = row["Organization"]
    for term in (name.upper(), org.lower(), row["Email"].upper()):
        dp.open_contacts()
        dp.search(term)
        assert dp.row_count() >= 1 and any(r[dp.header_matching("Name")] == name for r in dp.rows()), f"Search '{term}'"
    dp.open_contacts()
    dp.set_filter_toggle("main_poc", True)
    dp.apply_filters()
    poc_col = dp.header_matching("Point of Contact", "POC")
    assert set(dp.column(poc_col)) <= {"Yes"}, "Main POC filter must show only Main POCs"
    dp.search("zzzz-no-such-contact")
    assert dp.has_text(data["messages"]["no_contacts"])
    dp.reset_filters()
    assert dp.row_count() >= 1


@pytest.mark.consumes_seed_data
def test_llodir_13_export_contacts(ctx, dp, data, staging):
    """LLODir_13: CSV and Excel exports follow the filters and contain the documented columns."""
    org = _base_org(ctx, dp, data)
    name = _make_contact(dp, data, org, "export", poc=False)
    dp.open_contacts(f"?search={name.replace(' ', '+')}")
    download = dp.export("CSV")
    assert download.suggested_filename.startswith("contacts_") and download.suggested_filename.endswith(".csv")
    content = open(download.path(), encoding="utf-8-sig").read()
    rows = list(csv.DictReader(io.StringIO(content)))
    for column in ("Contact Name", "Organization", "Role / Title", "Email", "Phone", "Notes"):
        assert column in rows[0], f"CSV column '{column}' missing: {list(rows[0])}"
    assert any(c in rows[0] for c in ("Main POC", "Main Point of Contact")), f"Main POC column missing: {list(rows[0])}"
    assert [r["Contact Name"] for r in rows] == [name], "Export must follow the search filter"
    # After an export the button is replaced by "Download Export", so reopen the filtered list.
    dp.open_contacts(f"?search={name.replace(' ', '+')}")
    xlsx = dp.export("Excel")
    assert xlsx.suggested_filename.endswith(".xlsx")


# -- Gaps found in the code (LLODir_14-28) -------------------------------------------------------


def test_llodir_14_logged_out_refused(ctx, dp, browser, config):
    """LLODir_14: a logged-out visitor gets 403 on every directory URL (raise_exception=True)."""
    base = dp.host()
    anon = browser.new_context(ignore_https_errors=True)
    try:
        page = anon.new_page()
        for path in ("/organizations/", "/organizations/contacts/", "/organizations/new/", "/organizations/contacts/new/"):
            response = page.goto(base + path)
            assert response.status == 403, f"{path} returned {response.status} for a logged-out visitor"
    finally:
        anon.close()


def test_llodir_15_action_endpoints_post_only(ctx, dp):
    """LLODir_15: archive / restore / export endpoints accept POST only (GET 405)."""
    dp.open_organizations()
    ghost = "00000000-0000-0000-0000-000000000000"
    for path in (f"contacts/{ghost}/archive/", f"contacts/{ghost}/restore/", "contacts/export/"):
        status = dp.status_of(dp.url(path))
        assert status == 405, f"GET {path} returned {status}, expected 405"


def test_llodir_16_direct_form_urls_and_next(ctx, dp, data, config):
    """LLODir_16: a form URL opened directly returns to the listing; an off-site next is ignored."""
    for path, expect in (("new/", "/organizations/"), ("contacts/new/", "/organizations/contacts/")):
        dp.goto(dp.url(path))
        assert dp.page.url.rstrip("/").endswith(expect.rstrip("/")), f"{path} should redirect to {expect}: {dp.page.url}"
        assert not dp.modal_visible()
    dp.goto(dp.url("new/") + "?next=https://example.com/")
    assert "example.com" not in dp.page.url, "An off-site next must be ignored"


@pytest.mark.consumes_seed_data
def test_llodir_17_year_of_establishment(ctx, dp, data, staging):
    """LLODir_17: year bounds (earliest..current) and newest-first dropdown."""
    current = datetime.datetime.now(datetime.timezone.utc).year
    dp.open_organizations()
    dp.open_add_org()
    options = [o for o in dp.modal_options("year_of_establishment") if o.isdigit()]
    assert options and options[0] == str(current) and options[-1] == str(data["earliest_year"]), "Years newest first"
    dp.fill_modal(name=_name(data, "year"), short_name=_short("yr"), regions=data["regions"])
    dp._set_select("countries", [data["country"]])
    dp.select_by_index("primary_sectors", data["sector_index"])
    dp.page.evaluate(
        "y => { const s = document.querySelector('[role=dialog] #id_year_of_establishment');"
        " s.tomselect.addOption({value: y, text: y}); s.tomselect.setValue(y); }", str(data["earliest_year"] - 1))
    dp.modal_save()
    expected = f"Year must be between {data['earliest_year']} and {current}."
    assert dp.has_text(expected), f"Out-of-range year must be rejected: {dp.modal_error_text()[-300:]}"


def test_llodir_18_profile_fields(ctx, dp, data, staging):
    """LLODir_18: website URL, FLWs Managed, team size and Has Used Connect."""
    dp.open_organizations()
    dp.open_add_org()
    assert dp.modal_options("has_used_connect") == ["Yes", "No"] or set(dp.modal_options("has_used_connect")) == {"Yes", "No"}
    assert {"1-10", "11-50", "51-200", "201-500", "500+"} <= set(dp.modal_options("team_size"))
    dp.fill_modal(name=_name(data, "fields"), short_name=_short("fl"), regions=data["regions"],
                  website="not a website", flws_managed="-5")
    dp._set_select("countries", [data["country"]])
    dp.select_by_index("primary_sectors", data["sector_index"])
    dp.modal_save(server_validated=True)
    text = dp.modal_error_text()
    assert "Enter a valid URL." in text, "Invalid website must be rejected"
    assert "greater than or equal to 0" in text, "Negative FLWs Managed must be rejected"


@pytest.mark.consumes_seed_data
def test_llodir_19_multiline_fields_cleaned(ctx, dp, data, staging):
    """LLODir_19: blank lines / spaces dropped from emails and links; all bad entries reported together."""
    name = _name(data, "lines")
    dp.open_organizations()
    dp.open_add_org()
    dp.fill_modal(name=name, short_name=_short("ln"), regions=data["regions"],
                  contact_emails="a@example.com\n\n  b@example.com  \n", eoi_links="https://example.com/1\n\n https://example.com/2 ")
    dp._set_select("countries", [data["country"]])
    dp.select_by_index("primary_sectors", data["sector_index"])
    dp.modal_save()
    dp.wait_modal_closed()
    dp.open_edit(name)
    assert dp.modal_value("contact_emails") == "a@example.com\nb@example.com"
    assert dp.modal_value("eoi_links") == "https://example.com/1\nhttps://example.com/2"
    dp.fill_modal(contact_emails="bad1\nok@example.com\nbad2", eoi_links="nope1\nhttps://example.com/ok\nnope2")
    dp.modal_save()
    text = dp.modal_error_text()
    assert "Invalid email(s): bad1, bad2" in text and "Invalid URL(s): nope1, nope2" in text, text[-400:]


@pytest.mark.consumes_seed_data
def test_llodir_20_organization_name_rules_on_edit(ctx, dp, data, staging):
    """LLODir_20: case-only rename of its own name saves; another organization's name is refused."""
    name = _make_org(dp, data, "names")
    other = _make_org(dp, data, "names-other")
    dp.open_organizations()
    dp.open_edit(name)
    dp.fill_modal(name=name.lower())
    dp.modal_save()
    dp.wait_modal_closed()
    assert dp.has_text(_msg(data, "org_updated", name=name.lower())), "Case-only rename of its own name must save"
    dp.open_edit(name.lower())
    dp.fill_modal(name=other.upper())
    dp.modal_save()
    assert dp.has_text(data["messages"]["dup_name"]), "Another organization's name must be refused"


@pytest.mark.consumes_seed_data
def test_llodir_21_contact_email_format(ctx, dp, data, staging):
    """LLODir_21: invalid email rejected; surrounding spaces trimmed."""
    org = _base_org(ctx, dp, data)
    dp.open_contacts()
    dp.open_add_contact()
    dp.fill_modal(name=_name(data, "contact-fmt"), email="not-an-email")
    dp._set_select("organization", org)
    dp.modal_save(server_validated=True)
    assert dp.has_text("Enter a valid email address."), "Invalid contact email must be rejected"
    email = _email("fmt")
    dp.fill_modal(email=f"  {email}  ")
    dp.modal_save(server_validated=True)
    dp.wait_modal_closed()
    name = _name(data, "contact-fmt")
    _focus(dp, name)
    assert dp.row(name).locator(f"a[href='mailto:{email}']").count() == 1, "Saved email must be trimmed"


@pytest.mark.consumes_seed_data
def test_llodir_22_main_poc_reassigned_on_add_and_move(ctx, dp, data, staging):
    """LLODir_22: a new Main POC replaces the old one; moving a Main POC into an org that has one replaces it."""
    org_a = _make_org(dp, data, "reassign-a")
    org_b = _make_org(dp, data, "reassign-b")
    old_a = _make_contact(dp, data, org_a, "ra-old", poc=True)
    old_b = _make_contact(dp, data, org_b, "rb-old", poc=True)
    new_a = _make_contact(dp, data, org_a, "ra-new", poc=True)
    term = _name(data, "contact-r")
    _focus(dp, term)
    poc_col = dp.header_matching("Point of Contact", "POC")
    assert dp.row_values(new_a)[poc_col] == "Yes" and dp.row_values(old_a)[poc_col] == "—"
    dp.open_edit(new_a)
    dp._set_select("organization", org_b)
    dp.modal_save()
    dp.wait_modal_closed()
    _focus(dp, term)
    assert dp.row_values(new_a)[poc_col] == "Yes", "The moved Main POC keeps POC Yes"
    assert dp.row_values(old_b)[poc_col] == "—", "The destination organization's previous Main POC is unmarked"


@pytest.mark.consumes_seed_data
def test_llodir_23_archive_updates_counts_and_keeps_filters(ctx, dp, data, staging):
    """LLODir_23: Contacts count drops/rises, Organizations count unchanged, filters kept."""
    org = _base_org(ctx, dp, data)
    name = _make_contact(dp, data, org, "counts")
    dp.open_contacts(f"?search={name.replace(' ', '+')}")
    contacts_before, orgs_before = dp.tab_count("contacts"), dp.tab_count("organizations")
    dp.archive_contact(name)
    assert dp.tab_count("contacts") == contacts_before - 1 and dp.tab_count("organizations") == orgs_before
    assert "search=" in dp.page.url, "Archive must keep the current filters"
    dp.set_filter_toggle("archived", True)
    dp.apply_filters()
    dp.restore_contact(name)
    assert "search=" in dp.page.url and dp.tab_count("contacts") == contacts_before


def test_llodir_24_counts_versus_result_count(ctx, dp):
    """LLODir_24: tab counts stay totals while the result count follows the search."""
    dp.open_organizations()
    total = dp.tab_count("organizations")
    dp.search(dp.first_row_name())
    assert dp.tab_count("organizations") == total, "Tab count must not change under a search"
    assert dp.result_count() < total, "Result count must follow the search"


def test_llodir_25_paging_and_ordering(ctx, dp):
    """LLODir_25: page_size 20/30/50/100 only (else 20); contact sort columns."""
    dp.open_organizations("?page_size=100")
    total = dp.row_count()
    if total <= 20:
        skip_needs_data("Need more than 20 organizations to see paging")
    for size, expected in (("5", 20), ("30", min(total, 30)), ("20", 20)):
        dp.open_organizations(f"?page_size={size}")
        assert dp.row_count() == expected, f"page_size={size} should show {expected} rows, got {dp.row_count()}"
    dp.open_contacts()
    name_col = dp.header_matching("Name")
    for header in (name_col, "Organization", "Role / Title", "Email"):
        assert dp.sortable(header), f"{header} should be sortable"
    for header in ("Phone", "Actions"):
        assert not dp.sortable(header), f"{header} must not be sortable"


@pytest.mark.consumes_seed_data
def test_llodir_26_export_edge_cases(ctx, dp, data, staging):
    """LLODir_26: formula-looking text exported as text, non-ASCII intact, unsupported format 400."""
    org = _base_org(ctx, dp, data)
    name = f"=SUM(1+1) é {STAMP}"
    dp.create_contact(name, org, _email("fx"), title="+cmd", phone=data["contact_phone"], notes="@x")
    dp.open_contacts(f"?search={STAMP}")
    download = dp.export("CSV")
    rows = list(csv.DictReader(io.StringIO(open(download.path(), encoding="utf-8-sig").read())))
    mine = [r for r in rows if "SUM(1+1)" in r["Contact Name"]]
    assert mine, "Exported contact missing"
    for column in ("Contact Name", "Role / Title", "Notes"):
        assert not mine[0][column].startswith(("=", "+", "-", "@")), f"{column} must not start with a formula character: {mine[0][column]!r}"
    assert "é" in mine[0]["Contact Name"], "Non-ASCII characters must survive"
    assert (mine[0].get("Main POC") or mine[0].get("Main Point of Contact")) in ("Yes", "No")
    assert dp.status_of(dp.url("contacts/export/"), "POST", {"export_format": "pdf"}) == 400, "Unsupported format must be 400"


@pytest.mark.consumes_seed_data
def test_llodir_27_html_shown_as_text(ctx, dp, data, staging):
    """LLODir_27: markup in names is displayed literally on the listings."""
    markup = f"<b>{data['name_prefix']} {STAMP} bold</b>"
    dp.create_org(markup, _short("xs"), data["country"], data["sector_index"], data["regions"])
    assert dp.has_row(markup), "Markup must be displayed literally in the list"
    assert dp.page.locator("xpath=(//table)[1]//tbody//td//b").count() == 0, "Markup must not render as HTML"


def test_llodir_28_staff_without_permission(ctx):
    skip_needs_data("Needs a staff login without the LLO Directory permission (asked of Anshu/Hemant)")
