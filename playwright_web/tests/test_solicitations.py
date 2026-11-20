"""Solicitations (Solicitations_01-16 - the "Solicitations" tab of the web MTP sheet),
plus gaps found by reading commcare_connect/solicitation (views/forms/tables/tasks).

A Program-Manager org admin builds a solicitation in four saved steps (Details ->
Evaluation criteria -> Questions -> Review & publish), publishes it, and invites
organizations. Everything a test needs it creates itself through the UI, titled
"<prefix> <timestamp> <tag>", so nothing depends on seeded solicitations. Because
the suite creates (and never deletes) solicitations and invites real staging orgs,
the whole module is staging-only.

One shared module-scoped login. Active solicitations (private / public) are built
lazily once and reused by the invitation tests (they cannot be deleted, and
publishing is the slow part).

Needs outside data (skip until seeded - see the asks in the PR):
  - Solicitations_04: an Active solicitation with invitations and applications in every status
    (set SOLICITATIONS.counts_* in the test data once seeded).
  - Solicitations_15: needs the marketplace "Invited" section (not in the repo / not found on staging)
    plus invited and non-invited org member logins.
Solicitations_02 covers the non-PM-org admin half only (PM-org member login not configured).
Solicitations_05 / 16 verify a solicitation seeded by 16 itself (closing at the next whole hour); they
pass on the first run after that deadline. Cancelled has no UI/view to set it, so it is checked only if present.

Code-derived gap tests (not in the sheet): whole-hour deadline snap, server-side
publish/locked-step/invitation-delete guards, question->criterion scoping, title
HTML-escaping, list pagination, invitations ordered by organization name.
"""

import datetime
import uuid

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_solicitations_page import SolicitationInvitationsPage, SolicitationsPage
from utils.skips import skip_blocked, skip_needs_data, skip_not_applicable

STAMP = datetime.datetime.now(datetime.timezone.utc).strftime("%m%d-%H%M%S")


@pytest.fixture(autouse=True)
def staging_only(config):
    if config.env == "prod":
        skip_not_applicable(
            "Solicitations is not live on prod (SOLICITATIONS switch off: /a/pm_automation_01/solicitations/ is 404, "
            "checked 2026-11-20); the module also creates solicitations and invites real orgs - staging only"
        )


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
        yield {"page": connect_page, "data": test_data.get("SOLICITATIONS"), "cache": {}}
    finally:
        context.close()


@pytest.fixture
def sp(ctx):
    return SolicitationsPage(ctx["page"])


@pytest.fixture
def inv(ctx):
    return SolicitationInvitationsPage(ctx["page"])


@pytest.fixture
def data(ctx):
    return ctx["data"]


# -- helpers -----------------------------------------------------------------------


def _title(data, tag):
    return f"{data['title_prefix']} {STAMP} {tag}"


def _deadline(days=10, hours=0):
    """Whole-hour UTC datetime-local value, always in the future."""
    when = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days, hours=hours)
    return when.strftime("%Y-%m-%dT%H:00")


def _complete_details(data, title, **overrides):
    values = dict(
        title=title,
        type_label="Request for Proposals",
        description=data["description"],
        budget_min=data["budget_min"],
        budget_max=data["budget_max"],
        currency=data["currency"],
        country=data["country"],
        scale=data["scale"],
        contact_email=data["contact_email"],
        deadline=_deadline(),
    )
    values.update(overrides)
    return values


def _new_details_page(sp):
    sp.open_list()
    sp.click_new_solicitation()


def _build_draft(sp, data, tag, public=False, **overrides):
    """Create a complete draft (details, criteria 60+40, one question) and stop on Review & publish."""
    title = _title(data, tag)
    _new_details_page(sp)
    sp.fill_details(**_complete_details(data, title, public=public, **overrides))
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()
    assert sol_id, f"Details did not save: {sp.page.url}"
    sp.add_criterion(0, "Quality", 60, "What good looks like")
    sp.add_criterion(1, "Cost", 40)
    sp.save_and_continue()
    sp.add_question(0, "Describe your approach", "Free text", criterion="Quality")
    sp.save_and_continue()
    assert "/publish/" in sp.page.url, f"Questions did not save: {sp.page.url}"
    return sol_id, title


def _build_active(sp, data, tag, public):
    sol_id, title = _build_draft(sp, data, tag, public=public)
    sp.publish()
    return sol_id, title, sp.page.url


def _active(ctx, sp, data, public):
    key = "public" if public else "private"
    if key not in ctx["cache"]:
        sol_id, title, _ = _build_active(sp, data, f"active-{key}", public)
        ctx["cache"][key] = (sol_id, title)
    return ctx["cache"][key]


def _invitations_url(sp, sol_id):
    return sp.url(sol_id, "invitations")


# -- Solicitations Dashboard ------------------------------------------------------------


def test_solicitations_01_list_page(ctx, sp, data):
    """Solicitations_01: sidebar item below Programs; columns; draft/active title links;
    active Invited count opens the invitations page."""
    page = ctx["page"]
    page.goto(sp.org_base() + "/opportunity/")
    page.wait_for_load_state("load")
    labels = sp.sidebar_labels()
    assert "Solicitations" in labels and "Programs" in labels, f"Sidebar: {labels}"
    assert labels.index("Programs") < labels.index("Solicitations"), "Solicitations must sit below Programs"
    sp.open_list_via_sidebar()
    assert sp.url() in page.url or page.url.rstrip("/").endswith("/solicitations")

    headers = sp.list_headers()
    missing = [c for c in data["list_columns"] if c not in headers]
    assert not missing, f"Missing columns {missing}; present {headers}"

    if sp.is_list_empty():
        assert sp.has_text(data["messages"]["empty_list"])
        skip_needs_data("Org has no solicitations, so title/Invited links cannot be checked")

    drafts = sp.rows_by_status("Draft")
    actives = sp.rows_by_status("Active")
    if drafts:
        assert "/details/" in (sp.title_link_href(drafts[0]) or ""), "Draft title must open Details"
    if actives:
        assert "/details/" in (sp.title_link_href(actives[0]) or ""), "Active title must open Details"
        invited = sp.invited_link_href(actives[0])
        assert invited and "/invitations/" in invited, "Active Invited count must open Invited organizations"


def test_solicitations_02_users_without_access(ctx, sp, data):
    """Solicitations_02 (non-PM org half): in an org that is not a Program Manager org there is no
    Solicitations item and both the list and /new/ URLs are 404. The PM-org *member* (non-admin)
    half needs a second login that is not configured; it hits the same org_pm_required check."""
    page = ctx["page"]
    pm_base = sp.org_base()
    other = pm_base.rsplit("/a/", 1)[0] + f"/a/{data['non_pm_org_slug']}"
    try:
        page.goto(other + "/opportunity/")
        page.wait_for_load_state("load")
        assert not sp.sidebar_has_solicitations(), "Non-PM org must not show a Solicitations item"
        for path in ("/solicitations/", "/solicitations/new/"):
            status = sp.status_of(other + path)
            assert status == 404, f"{other + path} returned {status}, expected 404"
    finally:
        page.goto(pm_base + "/opportunity/")
        page.wait_for_load_state("load")


def test_solicitations_03_other_org_solicitation_not_found(ctx, sp):
    """Solicitations_03 (variant): every step URL of a solicitation this org does not own
    is 404. A solicitation id that exists in another org is not available, so a random id
    stands in - the views resolve it through the same org-scoped queryset."""
    ghost = str(uuid.uuid4())
    sp.open_list()
    for step in ("details", "criteria", "questions", "publish", "invitations"):
        status = sp.status_of(sp.url(ghost, step))
        assert status == 404, f"{step} for a foreign/unknown solicitation returned {status}, expected 404"
    assert not sp.has_row(ghost)


def test_solicitations_04_responses_and_invited_counts(ctx, sp, data, config):
    """Solicitations_04: Responses counts submitted + under review + awarded only (not draft/withdrawn/rejected),
    Invited equals the invited organizations, and neither count is multiplied by the other.
    Needs an Active solicitation seeded by an applicant org's applications (see counts_* in the test data)."""
    title = env_value(data, "counts_solicitation_title", config)
    if not title:
        skip_needs_data("SOLICITATIONS.counts_solicitation_title_staging is not set - needs the seeded solicitation")
    sp.open_list()
    if not sp.has_row(title):
        skip_needs_data(f"Seeded solicitation '{title}' is not in this org's list")
    values = sp.row_values(title)
    assert values["Invited"] == str(data["counts_expected_invited"]), values
    assert values["Responses"] == str(data["counts_expected_responses"]), values


def _closing_rows(sp, data, status):
    marker = f"{data['title_prefix']} {data['closing_marker']} "
    return [t for t in sp.rows_by_status(status) if t.startswith(marker)]


def _seed_closing(sp, data):
    """Publish a solicitation whose deadline is the next whole hour (>= 4 minutes away), titled with its own id."""
    now = datetime.datetime.now(datetime.timezone.utc)
    deadline = (now + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    if deadline - now < datetime.timedelta(minutes=4):
        deadline += datetime.timedelta(hours=1)
    stamp = deadline.strftime("%Y-%m-%dT%H:00")
    _new_details_page(sp)
    sp.fill_details(**_complete_details(data, _title(data, "closing-temp"), deadline=stamp))
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()
    title = f"{data['title_prefix']} {data['closing_marker']} {sol_id}"
    sp.go_to_step("Details")
    sp.fill_details(title=title)
    sp.save_and_continue()
    sp.add_criterion(0, "Quality", 100)
    sp.save_and_continue()
    sp.add_question(0, "Describe your approach", "Free text")
    sp.save_and_continue()
    sp.publish()
    return title, deadline


def test_solicitations_05_closed_and_cancelled_not_editable(ctx, sp, data):
    """Solicitations_05: a Closed row shows the badge, its title and Invited count are not links, and its
    details and invitations URLs are 404. Closed rows come from the solicitation seeded by Solicitations_16.
    Cancelled has no UI or view to set it (closure_reason is not wired up), so it is only checked when a
    Cancelled row exists."""
    sp.open_list()
    closed = _closing_rows(sp, data, "Closed")
    if not closed:
        skip_needs_data("No Closed solicitation yet - Solicitations_16 seeds one that closes at the next whole hour")
    for title in closed:
        sol_id = title.rsplit(" ", 1)[1]
        assert sp.row_values(title)["Status"] == "Closed"
        assert sp.title_link_href(title) is None, f"Closed title '{title}' must not be a link"
        assert sp.invited_link_href(title) is None, f"Closed Invited count of '{title}' must not be a link"
        for step in ("details", "invitations"):
            assert sp.status_of(sp.url(sol_id, step)) == 404, f"Closed solicitation {step} URL must be 404"
    for title in sp.rows_by_status("Cancelled"):
        assert sp.title_link_href(title) is None and sp.invited_link_href(title) is None, \
            f"Cancelled '{title}' must not have links"


# -- Create Solicitation --------------------------------------------------------------------


def test_solicitations_06_create_through_all_steps(ctx, sp, data):
    """Solicitations_06: all four steps, stepper, defaults, program->delivery type, messages, Review."""
    title = _title(data, "full-flow")
    sp.open_list()
    sp.click_new_solicitation()

    # Stepper: all four steps, later ones are not links before the first save.
    assert sp.stepper_labels() == data["steps"]
    assert all(h is None for h in sp.stepper_hrefs().values()), "Steps must not link before Details is saved"
    assert sp.active_step() == "Details"
    assert sp.page.locator("#id_public").is_checked() is False, "Public must default OFF"
    assert sp.page.locator("#id_hide_scores_until_submit").is_checked() is True, "Hide scores must default ON"
    assert sp.page.locator("xpath=//*[normalize-space()='Time is in UTC.']").count() > 0

    # Picking a program fills its delivery type (when the program has one).
    programs = sp.tomselect_option_labels("id_program")
    if programs:
        sp.set_tomselect("id_program", programs[0])
        sp.page.wait_for_timeout(500)
        filled = sp.selected_delivery_type()
        print(f"Program '{programs[0]}' -> delivery type '{filled}'")

    sp.fill_details(**_complete_details(data, title, public=True, hide_scores=False,
                                        start_date="2027-01-10", end_date="2027-06-10"))
    sp.save_and_continue()
    assert sp.has_text(data["messages"]["saved"]), "Details save message missing"
    assert sp.active_step() == "Evaluation criteria"
    sol_id = sp.solicitation_id_from_url()
    assert all(h for h in sp.stepper_hrefs().values()), "All steps link once Details is saved"

    sp.click_back()
    assert "/details/" in sp.page.url, "Back must return to Details"
    sp.go_to_step("Evaluation criteria")

    sp.add_criterion(0, "Quality", 70, "Guidance")
    sp.add_criterion(1, "Cost", 30)
    sp.save_and_continue()
    assert sp.has_text(data["messages"]["saved"]) and sp.active_step() == "Questions"

    for i, qtype in enumerate(data["question_types"]):
        opts = "Option A\nOption B" if qtype == "Choice" else None
        sp.add_question(i, f"Question {i + 1} {qtype}", qtype, options=opts, required=(i % 2 == 0),
                        criterion="Quality" if i == 0 else None)
    sp.save_and_continue()
    assert sp.has_text(data["messages"]["saved"]) and sp.active_step() == "Review & publish"

    text = sp.review_text()
    for expected in (title, data["currency"], data["country"], data["contact_email"], data["description"],
                     "Public (any organization can see and apply)", "Quality", "70%", "Cost", "30%",
                     "Scored under: Quality", "Required", "Optional", "Option A", "Option B"):
        assert expected in text, f"Review missing '{expected}'"
    positions = [text.index(f"Question {i + 1} {t}") for i, t in enumerate(data["question_types"])]
    assert positions == sorted(positions), "Questions must be listed in the order they were added"
    for qtype in data["question_types"]:
        assert qtype in text, f"Question type badge '{qtype}' missing on Review"
    ctx["cache"]["full_flow"] = sol_id

    # Newest first: the solicitation just created heads the list.
    sp.open_list()
    assert sp.list_titles()[0] == title, f"Newest solicitation must be first, got {sp.list_titles()[:3]}"


def test_solicitations_07_partial_draft_saves_and_resumes(ctx, sp, data):
    """Solicitations_07: only Title/Type/Currency/Deadline saves as Draft; Cancel/Back don't
    save the current step; reopening shows the saved values and toggles."""
    title = _title(data, "partial")
    deadline = _deadline(days=12)
    _new_details_page(sp)
    sp.fill_details(title=title, type_label="Expression of Interest", currency=data["currency"],
                    deadline=deadline, public=True, hide_scores=False)
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()
    assert sol_id, "A draft with only the required fields must save (Scope/Email/Country are optional)"

    # Back from criteria leaves without saving a half-filled row.
    sp.add_criterion(0, "Unsaved", 10)
    sp.click_back()
    sp.go_to_step("Evaluation criteria")
    assert sp.visible_criterion_labels() == [], "Back must not save the current step"
    sp.click_cancel()
    assert sp.page.url.rstrip("/").endswith("/solicitations")

    sp.open_list()
    assert sp.row_values(title)["Status"] == "Draft"
    sp.page.goto(sp.url(sol_id, "details"))
    values = sp.details_values()
    assert values["title"] == title and values["type"] == "eoi"
    assert values["public"] is True and values["hide_scores"] is False
    assert values["deadline"] == deadline, f"Deadline round-trip: {values['deadline']} vs {deadline}"
    assert values["description"] == "" and values["contact_email"] == ""


def test_solicitations_08_validation(ctx, sp, data):
    """Solicitations_08: budget/date/weight/choice validation and choice-options visibility."""
    msgs = data["messages"]
    title = _title(data, "validation")
    _new_details_page(sp)
    sp.fill_details(**_complete_details(data, title, budget_min="500", budget_max="100",
                                        start_date="2027-05-01", end_date="2027-05-01"))
    sp.save_and_continue()
    assert sp.has_text(msgs["budget"]), "Budget rule missing"
    assert sp.has_text(msgs["dates"]), "Date rule missing"
    assert sp.solicitation_id_from_url() is None, "Invalid details must not save"

    sp.fill_details(budget_min="100", budget_max="500", start_date="2027-05-01", end_date="2027-06-01")
    sp.save_and_continue()
    assert sp.solicitation_id_from_url()

    # Criterion weights: -1, 100.01, 12.345, blank label (server rules; browser checks bypassed).
    for label, weight, expected in (
        ("W", "-1", "greater than or equal to 0"),
        ("W", "100.01", "less than or equal to 100"),
        ("W", "12.345", "decimal places"),
        ("", "10", "This field is required"),
    ):
        sp.page.goto(sp.page.url if "/criteria/" in sp.page.url else sp.url(sp.solicitation_id_from_url(), "criteria"))
        sp.page.wait_for_load_state("load")
        sp.add_criterion(0, label, weight)
        sp.save_and_continue_server_validated()
        assert sp.has_text(expected), f"Weight '{weight}' / label '{label}': expected '{expected}'"
        assert "/criteria/" in sp.page.url, "Invalid criterion must stay on the step"

    sp.page.goto(sp.url(sp.solicitation_id_from_url(), "criteria"))
    sp.add_criterion(0, "Valid", 100)
    sp.save_and_continue()

    # Choice question: needs an option; options box only for Choice; dropped for other types.
    sp.add_question(0, "Pick", "Choice", options="")
    assert sp.choice_options_visible(0)
    sp.save_and_continue_server_validated()
    assert sp.has_text(msgs["choice"])
    sp.select_question_type(0, "Number")
    assert not sp.choice_options_visible(0), "Options box must be hidden for non-choice types"
    sp.page.locator("#id_questions-0-choice_options").evaluate("e => e.value = 'stale'")
    sp.save_and_continue()
    assert "/publish/" in sp.page.url
    sp.go_to_step("Questions")
    assert sp.page.locator("#id_questions-0-choice_options").input_value() == "", \
        "Options must be dropped when the type is not Choice"


def test_solicitations_09_removing_criteria_and_questions(ctx, sp, data):
    """Solicitations_09: removed rows are deleted on save and stay removed after a failed save;
    removing a criterion leaves its linked question with no criterion."""
    _new_details_page(sp)
    sp.fill_details(**_complete_details(data, _title(data, "removal")))
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()

    sp.add_criterion(0, "Alpha", 30)
    sp.add_criterion(1, "Beta", 30)
    sp.add_criterion(2, "Gamma", 40)
    sp.save_and_continue()
    sp.add_question(0, "Linked to Alpha", "Free text", criterion="Alpha")
    sp.save_and_continue()

    # Remove Beta and save -> gone.
    sp.page.goto(sp.url(sol_id, "criteria"))
    sp.remove_row(2)
    sp.save_and_continue()
    sp.page.goto(sp.url(sol_id, "criteria"))
    assert sp.visible_criterion_labels() == ["Alpha", "Gamma"], sp.visible_criterion_labels()

    # Remove Gamma but make the save fail (blank label on Alpha): Gamma must stay removed.
    sp.remove_row(2)
    sp.page.locator("#id_criteria-0-label").fill("")
    sp.save_and_continue_server_validated()
    assert "/criteria/" in sp.page.url
    assert "Gamma" not in sp.visible_criterion_labels(), "Removed row reappeared after a failed save"

    # Remove the linked criterion (Alpha) -> its question keeps no criterion.
    sp.page.goto(sp.url(sol_id, "criteria"))
    sp.remove_row(1)
    sp.save_and_continue()
    sp.page.goto(sp.url(sol_id, "questions"))
    assert sp.visible_question_criterion(0) == "", "Question must lose its criterion when the criterion is removed"


def test_solicitations_10_publish_blocked_until_complete(ctx, sp, data):
    """Solicitations_10: each blocker listed with a Fix link; Publish disabled; 99.99% still blocked;
    publishes at exactly 100% (checked via the build in the publish tests)."""
    title = _title(data, "blocked")
    _new_details_page(sp)
    past = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=2)).strftime("%Y-%m-%dT%H:00")
    sp.fill_details(title=title, type_label="Request for Proposals", currency=data["currency"], deadline=past)
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()
    sp.add_criterion(0, "Only", 90)
    sp.save_and_continue()
    sp.go_to_step("Review & publish")

    assert data["messages"]["publish_blocked_heading"] in sp.body_text()
    blockers = " | ".join(sp.publish_blockers())
    for expected in ("Scope of work is required", "Contact email is required", "Country is required",
                     "application deadline must be in the future", "must total 100%"):
        assert expected in blockers, f"Missing blocker '{expected}' in: {blockers}"
    hrefs = sp.blocker_fix_hrefs()
    assert any("/details/" in h for h in hrefs) and any("/criteria/" in h for h in hrefs), hrefs
    assert sp.publish_disabled(), "Publish must be disabled while blocked"

    # Fix details; 33.33 x 3 = 99.99% must still block.
    sp.page.goto(sp.url(sol_id, "details"))
    sp.fill_details(description=data["description"], contact_email=data["contact_email"],
                    country=data["country"], deadline=_deadline())
    sp.save_and_continue()
    sp.page.goto(sp.url(sol_id, "criteria"))
    sp.remove_row(1)
    # Row 1 ("Only") is removed but keeps index 0; new rows continue from index 1.
    sp.add_criterion(1, "A", "33.33")
    sp.add_criterion(2, "B", "33.33")
    sp.add_criterion(3, "C", "33.33")
    sp.save_and_continue()
    sp.go_to_step("Review & publish")
    assert sp.publish_disabled(), "99.99% must still block publishing"
    assert "99.99%" in " | ".join(sp.publish_blockers())


def test_solicitations_11_publish_and_edit_active(ctx, sp, data):
    """Solicitations_11: publish public (back to list) and private (to Invited organizations);
    criteria/questions read-only; Details editable; deadline can only be extended."""
    msgs = data["messages"]
    pub_id, pub_title, final_url = _build_active(sp, data, "active-public", public=True)
    assert sp.has_text(msgs["published"])
    assert final_url.rstrip("/").endswith("/solicitations"), f"Public publish should return to the list: {final_url}"
    ctx["cache"]["public"] = (pub_id, pub_title)

    priv_id, priv_title, final_url = _build_active(sp, data, "active-private", public=False)
    assert sp.has_text(msgs["published"])
    assert f"/{priv_id}/invitations/" in final_url, f"Private publish should open invitations: {final_url}"
    ctx["cache"]["private"] = (priv_id, priv_title)

    for step in ("criteria", "questions"):
        sp.page.goto(sp.url(pub_id, step))
        assert sp.is_read_only(), f"{step} must be read-only once published"
        assert sp.locked_hint_present()

    sp.page.goto(sp.url(pub_id, "details"))
    assert sp.has_save_button() and not sp.has_save_and_continue()
    sp.page.locator("#id_description").fill("")
    sp.save_details_in_place()
    assert "/details/" in sp.page.url, "Blank Scope of work must be rejected on an active solicitation"
    sp.fill_details(description="Updated scope of work")

    sp.fill_details(deadline=_deadline(days=1))  # earlier than the published 10 days out
    sp.save_details_in_place()
    assert sp.has_text(msgs["deadline_extend_only"]), "Moving the deadline earlier must be refused"

    sp.fill_details(deadline=_deadline(days=20), description="Updated scope of work")
    sp.save_details_in_place()
    assert sp.page.url.rstrip("/").endswith("/solicitations"), "Valid Details edit on an active solicitation saves to the list"
    assert sp.has_text(msgs["saved"])


# -- Invite Organizations ----------------------------------------------------------------------


def _invitation_orgs(ctx, data, config):
    return env_value(data, "invite_orgs", config)


def test_solicitations_12_invite_organizations(ctx, inv, data, config):
    """Solicitations_12: hint, empty state, invite two orgs, table columns, dropdown rules,
    required error. (Invitation emails need an org member inbox - not checked here.)"""
    sol_id, _ = _active(ctx, inv, data, public=False)
    orgs = _invitation_orgs(ctx, data, config)
    inv.page.goto(_invitations_url(inv, sol_id))
    inv.verify_loaded()
    assert "private" in inv.hint_text().lower()
    assert inv.is_empty() and data["messages"]["no_invites"] in inv.body_text()

    inv.open_invite_modal()
    offered = inv.offered_orgs()
    assert "PM_Automation_01" not in offered, "The solicitation's own org must not be offered"
    inv.submit_invite(server_validated=True)
    assert inv.invite_required_error_shown(), "Inviting with nothing picked must show 'This field is required.'"

    inv.page.goto(_invitations_url(inv, sol_id))
    inv.invite(orgs)
    assert inv.has_text("Invited 2 organization(s)."), "Invite success message missing"
    rows = inv.invitation_table_rows()
    assert sorted(r["Organization"] for r in rows) == sorted(orgs), rows
    for r in rows:
        assert r["Invited by"] and r["Invited on"], f"Invited by / Invited on missing: {r}"

    inv.open_invite_modal()
    assert not set(orgs) & set(inv.offered_orgs()), "Already-invited orgs must not be offered again"


def test_solicitations_13_remove_invitations(ctx, inv, data, config):
    """Solicitations_13: confirm text, Cancel keeps, Remove deletes only the ticked org, org can be re-invited."""
    sol_id, _ = _active(ctx, inv, data, public=False)
    orgs = _invitation_orgs(ctx, data, config)
    inv.page.goto(_invitations_url(inv, sol_id))
    inv.verify_loaded()
    if not set(orgs) <= set(inv.invited_orgs()):
        inv.invite([o for o in orgs if o not in inv.invited_orgs()])
    target, keep = orgs[0], orgs[1]

    inv.tick_org(target)
    inv.click_remove_icon()
    assert inv.confirm_modal_visible(), "Confirm text 'Remove 1 invitation(s)? ...' missing"
    assert "Remove 1 invitation(s)?" in inv.confirm_modal_message(), inv.confirm_modal_message()
    inv.cancel_remove()
    assert target in inv.invited_orgs(), "Cancel must keep the invitation"

    inv.click_remove_icon()
    inv.confirm_remove()
    assert inv.has_text("Removed 1 invitation(s)."), "Removal message missing"
    assert target not in inv.invited_orgs() and keep in inv.invited_orgs()

    inv.invite([target])
    assert target in inv.invited_orgs(), "A removed org must be invitable again"


def test_solicitations_14_where_invitations_are_available(ctx, inv, data):
    """Solicitations_14: active public and private have the button and page; drafts have neither (404)."""
    pub_id, _ = _active(ctx, inv, data, public=True)
    inv.page.goto(inv.url(pub_id, "details"))
    assert inv.invited_orgs_button_present(), "Active public solicitation needs the Invited organizations button"
    inv.page.goto(_invitations_url(inv, pub_id))
    inv.verify_loaded()
    assert "public" in inv.hint_text().lower()

    priv_id, _ = _active(ctx, inv, data, public=False)
    inv.page.goto(inv.url(priv_id, "details"))
    assert inv.invited_orgs_button_present()

    draft_id, _ = _build_draft(inv, data, "draft-no-invites")
    inv.page.goto(inv.url(draft_id, "details"))
    assert not inv.invited_orgs_button_present(), "Drafts must not show the Invited organizations button"
    assert inv.status_of(_invitations_url(inv, draft_id)) == 404, "A draft's invitations URL must be 404"


# -- Marketplace & deadline -----------------------------------------------------------------------


def test_solicitations_15_invited_section_in_marketplace(ctx):
    skip_blocked(
        "No marketplace/'Invited' section exists in commcare-connect main (the invite email still carries "
        "'TODO: link to the solicitation once invited organizations can view it (CCCT-2618)'); also needs "
        "invited / non-invited org member logins"
    )


def test_solicitations_16_closes_at_deadline(ctx, sp, data):
    """Solicitations_16: after its deadline an active solicitation shows Closed, cannot be edited and its
    invitations cannot be managed (title / Invited not links, URLs 404); drafts and future-deadline
    solicitations are unchanged. Deadlines are whole-hour and must be in the future to publish, so the
    test seeds one closing at the next hour and verifies it on a later run (a Closed row appears as soon as
    the clock passes the deadline - the model checks the clock, so the hourly sweep task is not needed)."""
    sp.open_list()
    closed = _closing_rows(sp, data, "Closed")
    if not closed:
        pending = _closing_rows(sp, data, "Active")
        if not pending:
            title, deadline = _seed_closing(sp, data)
            skip_needs_data(f"Seeded '{title}' closing {deadline:%H:%M} UTC - re-run after the deadline")
        skip_needs_data(f"Waiting for the deadline of {pending[0]} (Active) - re-run after it passes")
    title = closed[0]
    sol_id = title.rsplit(" ", 1)[1]
    assert sp.row_values(title)["Status"] == "Closed"
    assert sp.title_link_href(title) is None and sp.invited_link_href(title) is None
    for step in ("details", "criteria", "questions", "publish", "invitations"):
        assert sp.status_of(sp.url(sol_id, step)) == 404, f"Closed solicitation {step} URL must be 404"
    # Unchanged: a draft and an active future-deadline solicitation.
    drafts = sp.rows_by_status("Draft")
    assert drafts, "Drafts must stay Draft"
    future_id, future_title = _active(ctx, sp, data, public=True)
    sp.open_list()
    assert sp.row_values(future_title)["Status"] == "Active", "A future-deadline solicitation must stay Active"


# -- Gaps found in the code (not in the sheet) ------------------------------------------------------


def test_solicitations_gap_deadline_snaps_to_whole_hour(ctx, sp, data):
    """forms.SNAP_TO_WHOLE_HOUR: picking any minute on the deadline snaps it to :00."""
    _new_details_page(sp)
    deadline = _deadline(days=5)
    sp.set_deadline_raw(deadline[:14] + "37")
    assert sp.deadline_value().endswith(":00"), f"Deadline minutes must snap to :00, got {sp.deadline_value()}"


def test_solicitations_gap_publish_blocked_server_side(ctx, sp, data):
    """SolicitationPublishView.post re-checks publish_errors: a forced POST to a blocked draft must not publish."""
    _new_details_page(sp)
    sp.fill_details(title=_title(data, "forced-publish"), type_label="Request for Proposals",
                    currency=data["currency"], deadline=_deadline())
    sp.save_and_continue()
    sol_id = sp.solicitation_id_from_url()
    sp.go_to_step("Review & publish")
    assert sp.publish_disabled()
    status, _ = sp.post_form(sp.url(sol_id, "publish"), {})
    assert status == 200, f"Forced publish should re-render the page (200), got {status}"
    sp.open_list()
    assert sp.row_values(_title(data, "forced-publish"))["Status"] == "Draft", "Blocked draft must not become Active"


def test_solicitations_gap_locked_steps_reject_post(ctx, sp, data):
    """SolicitationFormSetStepView.form_valid raises PermissionDenied once the structure is locked."""
    sol_id, _ = _active(ctx, sp, data, public=True)
    sp.page.goto(sp.url(sol_id, "criteria"))
    status, _ = sp.post_form(
        sp.url(sol_id, "criteria"),
        {"criteria-TOTAL_FORMS": "1", "criteria-INITIAL_FORMS": "0", "criteria-MIN_NUM_FORMS": "0",
         "criteria-MAX_NUM_FORMS": "1000", "criteria-0-label": "Sneaky", "criteria-0-weight": "10"},
    )
    assert status == 403, f"Editing criteria of an active solicitation must be 403, got {status}"
    sp.page.goto(sp.url(sol_id, "criteria"))
    assert "Sneaky" not in sp.page.locator("body").inner_text()


def test_solicitations_gap_invitation_delete_guards(ctx, inv, data):
    """SolicitationInvitationDeleteView: POST only (GET 405), and ids that are not this solicitation's -> 400."""
    sol_id, _ = _active(ctx, inv, data, public=False)
    inv.page.goto(_invitations_url(inv, sol_id))
    inv.verify_loaded()
    delete_url = inv.url(sol_id, "invitations/delete")
    assert inv.status_of(delete_url) == 405, "Delete endpoint must only accept POST"
    status, _ = inv.post_form(delete_url, {"invitation_ids": "999999999"})
    assert status == 400, f"A foreign/unknown invitation id must be rejected with 400, got {status}"


def test_solicitations_gap_question_criterion_scoped(ctx, sp, data):
    """QuestionForm: the Criterion dropdown only offers this solicitation's own criteria."""
    _new_details_page(sp)
    sp.fill_details(**_complete_details(data, _title(data, "criterion-scope")))
    sp.save_and_continue()
    sp.add_criterion(0, "Scope One", 50)
    sp.add_criterion(1, "Scope Two", 50)
    sp.save_and_continue()
    sp.add_row()
    assert sorted(sp.criterion_choices(0)) == ["Scope One", "Scope Two"], sp.criterion_choices(0)


def test_solicitations_gap_title_html_escaped(ctx, sp, data):
    """A title containing markup is shown as text on the list (no injected element)."""
    markup = f"<b>{data['title_prefix']} {STAMP} bold</b>"
    _new_details_page(sp)
    sp.fill_details(title=markup, type_label="Expression of Interest", currency=data["currency"],
                    deadline=_deadline())
    sp.save_and_continue()
    sp.open_list()
    assert sp.has_row(markup), "Markup title must be displayed literally"
    assert sp.page.locator("table tbody td b").count() == 0, "Title markup must not be rendered as HTML"


def test_solicitations_gap_list_pagination(ctx, sp):
    """get_validated_page_size: page_size must be one of 20/30/50/100; anything else falls back to 20."""
    sp.open_list(page_size=100)
    total = sp.list_row_count()
    if total <= 20:
        skip_needs_data(f"Only {total} solicitations - need more than 20 to see a second page")
    sp.open_list(page_size=5)
    assert sp.list_row_count() == 20, f"Invalid page_size must fall back to 20 rows, got {sp.list_row_count()}"
    sp.open_list(page_size=30)
    assert sp.list_row_count() == min(total, 30)


def test_solicitations_gap_invitations_sorted_by_org_name(ctx, inv, data):
    """SolicitationInvitationsView orders the table by organization name."""
    sol_id, _ = _active(ctx, inv, data, public=False)
    inv.page.goto(_invitations_url(inv, sol_id))
    inv.verify_loaded()
    names = inv.invited_orgs()
    if len(names) < 2:
        skip_needs_data("Needs at least two invited orgs (run Solicitations_12/13 first)")
    assert names == sorted(names, key=str.lower), f"Invitations must be ordered by organization name: {names}"
