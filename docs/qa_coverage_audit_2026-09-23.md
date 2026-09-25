# Connect Web QA Coverage Audit — 2026-09-23

## Purpose

Confirm whether the Connect web-side MTP (`test_plans/CCC_Web_Platform_MTP.xlsx`) is fully
automated, module by module, without relying on the two in-repo trackers:

- the per-sheet **Comments** column, and
- the **"Automation (existing MTP)"** ledger tab.

Both were found to be stale or inconsistent depending on who last touched a given module and
when — several modules the ledger calls "0% automated" turn out to have substantial real
coverage, and at least one module (Opportunity creation) has a Comments column that's simply
never been filled in since the plan's original July import.

## Method

For each module, the real test-case rows in its MTP sheet were cross-referenced against the
**actual current test files** — function names, docstrings, and in several cases the full test
body — rather than trusting either tracker's status column.

A recurring pattern: several modules have real, substantial coverage tracked under a
**different test plan's own numbering**, never cross-referenced back to this MTP sheet:

- **Tasking / Re-Learn Task** → `TC-TTC-*` (type config), `TC-TAS-*` (assignment), `TC-TLV-*`
  (views/filters), `TC-TDL-*` (delete), `TC-PRM-*` (permissions)
- **Connect Messaging** → `TC-CAL-*` (conditional alerts), `TC-BRD-*` (broadcasts),
  `TC-KWD-*` (keywords), `TC-CHN-*` (channels)

This is a bookkeeping gap, not a feature gap — but it means a naive "0 automated" reading from
either tracker is often wrong.

## Headline results

| Module | TCs | Verdict |
|---|---|---|
| Connect Workers page | 45 | Functionally complete (destructive/mobile/data-gated items aside) |
| Visit Verification page | ~35 | Strong coverage, hybrid/data-gated remainder tracked |
| Invoices List page | 40 | 21 done; rest gated on real delivery data (Anshu ask sent) |
| Microplanning | 41 | 27 done; rest gated on map-canvas limits + Anshu data (partially unblocked) |
| **Opportunity List page** | 27 | **27/27 — verified against real assertions, no gaps found** |
| Opportunity dashboard | 47 | 43/47; remaining 4 descoped/cross-referenced/1 to confirm |
| Connect Messaging | 10 | 7/10 solid (device-proven); 3 real gaps (recipient-picker filtering) |
| Programs List page | 16 | 9/16; 6 real gaps (mostly navigation/negative-path) |
| Login page | 9 | 0 dedicated, 3 implicit, 2 genuinely manual, 4 cheap gaps |
| **Opportunity creation** | 28 | 3 solid, 5 unverified, **20 real gaps** (Org Pay cluster = 9 of these) |
| **Re-Learn Task (Tasking)** | 38 | 14 solid, 2 fine-as-is, **21 real gaps** |
| **Delivery Reminder Mails** | 8 | **0/8** — blocked on triggering a scheduled backend job on demand |
| App Credentials | 3 | **0/3** — small, no blockers, just never built |

**Bottom line:** modules built or re-verified in the same session as this audit (Workers, VV,
Invoices, Microplanning) are in good shape, and the modules that got an honest code-level
re-check (Opportunity List page, Opportunity dashboard, Connect Messaging) mostly hold up well
too. The real, non-blocked gap work clusters in two modules nobody had gone back to close since
the original July gap-analysis pass — **Opportunity creation** and **Re-Learn Task / Tasking** —
plus one small greenfield module (**App Credentials**) and one gap blocked on the same
"can't trigger a scheduled job on demand" constraint as the Invoice auto-generation gap
(**Delivery Reminder Mails**).

---

## Per-module detail

### Connect Workers page (45 TCs) — functionally complete

All core test cases automated (Connect_worker_01–15/17, Learn_tab_01/03/04,
Delivery_tab_01–05/09–16, Payment Processing_1–4, plus 6 gap-analysis cases). Remaining items
are deliberate, not oversights:

- **Connect_worker_16** (bulk-delete-all-types) — skipped; destructive, would wipe seeded workers.
- **Learn_tab_02** — needs a live mobile submission mid-test; hybrid flow built and PR'd
  (skip-gated pending seed data).
- **Delivery_tab_06/07** — needs controlled visit data; considered eng-covered.
- 4 partial gap cases (GAP-SRC-W-47/48/49/51/52) — small missing slices, each waiting on
  specific seed data already on the Anshu ask list.

### Visit Verification page (~35 web-relevant TCs)

Strong coverage from the Workers-module migration (VV_1/3/4/5/9/31–34 automated), plus 13
source-derived gap cases (GAP-SRC-W-40–52). Remaining backlog is mobile/hybrid-heavy
(VV_6-30, Payment eligibility) and tracked as in-scope, not deferred.

### Invoices List page (40 TCs) — 21 automated

Full self-contained NM-create → submit → PM-approve → pay lifecycle, plus cancel/reject paths,
all validated headed against staging. Remaining 16 TCs need real approved-delivery data
(Service Delivery invoices, auto-generated invoices) — Anshu has since replied with a
partial unblock (see project memory for the live opportunity ids).

### Microplanning (41 TCs) — 27 automated

All map-click-free structural/read-only cases done. The map itself renders on a Mapbox canvas
with no per-feature DOM access, so work-area selection needed a JS-injection workaround
(built, currently skip-gated on data). Anshu has since seeded a disposable opportunity that
unblocks most of the remainder — see project memory for details.

### Opportunity List page (27 TCs) — 27/27, verified

Read the full test bodies (`test_olp_list_page.py` + `test_olp_list_behaviour.py`) line by
line; every "Automated" comment corresponds to a real, specific assertion — not just a step
that happens to run. Examples: OLP_02 asserts an actual HTTP 403 for NM create attempts;
OLP_16 genuinely navigates away and back to prove filter persistence; OLP_28 proves a
drill-down link actually navigates, not just that it exists. No real gaps found. (OLP_03/21/25
don't exist as rows in the plan — retired IDs, not omissions.)

### Opportunity dashboard (47 TCs) — 43/47

Comments column is empty for every row (an "annotate" commit updated the ledger tab, not this
sheet), but real test function names exist for OD_1–21, 23–29, 31–38, 40, 42–47. Remaining 4:

- **OD_22** (standalone non-program opp) — legitimately descoped (standalone opps no longer exist).
- **OD_30** (24h increment badges) — legitimately descoped, documented in code.
- **OD_39** (Tasks tab columns/filters) — probably covered under the Tasking plan's `TC-TLV-003`,
  just uncredited.
- **OD_41** (per-tab filter persistence) — possibly the same behavior as `GAP-SRC-W-50`
  (already automated in the Workers module) tracked twice under two sheets; needs a 2-minute
  check, not necessarily new work.

### Connect Messaging (10 TCs) — 7/10 solid

Tracked under its own plan (`TC-CAL/BRD/KWD/CHN-*`) across `test_messaging_web.py` (no device)
and `test_messaging_hybrid.py` (real device delivery/answerability, 11 tests). Real gaps:

- **Connect message3/6** — Recipients dropdown disabling all-but-"users" when Connect content
  is selected — not tested at all.
- **Connect message7** — restricting the recipient picker to *active* PID users — not tested.

(The hybrid suite is currently red on prod due to the already-escalated CCCT-2671 messaging
regression — a product/infra issue, not a coverage gap.)

### Programs List page (16 TCs) — 9/16

Automated: PLP_01, 03, 05, 06, 10, 11/17, 12/14/15. Real gaps:

- **PLP_02** — invite-NM action performed but never asserted (no "Invited" status check).
- **PLP_04** — "select any program → land on its own detail page" not covered at all.
- **PLP_07** — the negative precondition (can't create/view opportunities before NM acceptance)
  never tested.
- **PLP_08/09** — landing on the Program's own page / checking opportunity performance from
  a program — not covered anywhere found.
- **PLP_16** — PM seeing the "Applied" status label specifically — only implicitly relied upon.

### Login page (9 TCs) — 0 dedicated

`LoginPage` exists only as **setup infrastructure** used by nearly every test file, never as
its own assertable test.

| TC | Status |
|---|---|
| Login 1 (fields visible) | Not automated |
| Login 2 (input validation) | Not automated |
| Login 3 (correct-credentials login) | Implicitly exercised only |
| Login 4 (SSO) | Implicitly exercised only |
| Login 5 (sign-up option) | Not automated |
| Login 6 (wrong credentials rejected) | Not automated |
| Login 7 (SSO prompt) | Implicitly exercised only |
| Login 8/9 (password reset) | Genuinely manual — needs a real email round-trip |

### Opportunity creation (28 TCs) — 3 solid, 20 real gaps

**Not a regression** — this gap was flagged in the original July "Pass 1" gap-analysis ledger
(4 automated / 22 not-yet-done / 2 manual, almost exactly matching what this audit found
independently) and simply never got the closing pass that Opportunity Dashboard, Opportunity
List, and Programs List each later received.

Automated: Opp_create_04/28 (create), 05 (payment unit page), 21 (budget page).

Exercised but not verified: Opp_create_22–24 (only one HQ server ever used), 25/26 (dropdowns
selected blindly, narrowing never asserted), 27 (only selects an existing credential, doesn't
create one).

Real gaps:
- **Opp_create_01/02/03** — negative/permission cases (NM can't create; PM can't create
  non-managed; legacy-program linking) — no negative-path tests exist.
- **Opp_create_06–09, 14–18** — the entire **Org Pay** feature (per-payment-unit config,
  independent editing, budget recalculation). Confirmed `org_pay` doesn't exist anywhere in
  the codebase. **9 of the 20 gaps are this one cluster.**
- **Opp_create_10–13** — field validation (decimal, long int, negative, special characters).
- **Opp_create_19/20** — worker actually earns/paid the configured amount — needs real mobile
  deliveries + payment verification; closest existing coverage is the Workers module's Payment
  Processing tests, but that's a different angle.

### Re-Learn Task / Tasking (38 TCs) — 14 solid, 21 real gaps

Real coverage exists under the Tasking plan's own IDs (`TC-TTC/TAS/TLV/TDL/PRM-*`) across five
test files, verified by reading the full test bodies.

Confirmed solid: Re-Learn_01, 02, 03, 10, 11, 17, 23, 26, 27, 32, 33, 34, 35, 37.

Sampled-but-fine (same pattern as other modules): Re-Learn_36 (2 filters, not exhaustive
combos).

Probably fine, cross-plan: Re-Learn_16 (Tasks tab on Visit Verification page) likely covered by
`test_vv_05_visit_tabs_render` in the Workers module.

Real gaps:
- **Re-Learn_04/05/07, 20/21** — mandatory-field validation (name/description/task-unit/due-date).
- **Re-Learn_06** — configuring a task type *without* a case property (test always supplies one).
- **Re-Learn_08/09/22** — Cancel/Close dismissal on both the task-type config and
  task-assignment popups.
- **Re-Learn_12–15** — sorting the task **type** list by any of its 4 headers.
- **Re-Learn_18** — the delete button's *disabled state* specifically (existing test checks
  visibility, not the checkbox-driven enable/disable toggle).
- **Re-Learn_19** — structural check of the create-task popup's fields.
- **Re-Learn_24** — viewing an already-submitted task form.
- **Re-Learn_25** — explicitly deferred in the code itself (pending a template-bug verification).
- **Re-Learn_28/29** — filters on the Workers-page Tasks tab specifically (existing coverage is
  for the standalone Task List page, not this tab).
- **Re-Learn_30/31** — filters on the Visit-Verification-page Tasks tab.
- **Re-Learn_38** — sorting the Task List page by header arrows.

### Delivery Reminder Mails (8 TCs) — 0/8

No test file, no page object, nothing references this feature. It's a **scheduled/cron-triggered
backend email job** — same category as the Invoice auto-generation gap. There's no UI button to
"send the reminder now."

The repo already has real IMAP email-reading infrastructure (`utils/email_otp.py`, built for
PersonalID OTP verification) that could verify reminder-mail *content* once one is sent — the
missing piece is a way to **trigger the job on demand**, the same ask pattern as Invoice_21-25.

### App Credentials (3 TCs) — 0/3

No automation exists (the only "credential" hits in the codebase were false positives —
login username/password, unrelated). Small CommCareHQ-side feature (issuing app credentials,
Worker Activity option, profile.xml updates). No blockers — just never built. Should be quick
to close.

---

## Recommended next steps

1. **Opportunity creation — Org Pay cluster** (9 TCs) is the single largest coherent body of
   real, unblocked work. Worth its own dedicated pass.
2. **Re-Learn Task / Tasking gaps** (21 TCs) — mostly small, well-scoped items (validation,
   popup dismissal, sorting) that fit the existing Tasking test-file structure.
3. **App Credentials** (3 TCs) — small, quick win, no blockers.
4. **Login page cheap gaps** (Login 1/2/5/6, 4 TCs) — infrastructure already exists, just needs
   its own dedicated assertions.
5. **Delivery Reminder Mails** — needs an engineering conversation about triggering the
   scheduled job on demand before any automation can start (same ask as Invoice auto-generation).
6. Two quick sanity checks, not full builds: **OD_41** (possible duplicate of `GAP-SRC-W-50`)
   and **Re-Learn_16** (possible duplicate of `test_vv_05_visit_tabs_render`).
7. Ongoing: Invoices (16 TCs) and Microplanning (14 TCs) remainders are progressing as Anshu's
   seed data lands — see the respective project memory files for live status.
