---
name: qa-ticket-prep
description: Use when preparing a test plan for a software release, or when the QA agent handles a single commcare-connect PR. Triggered by phrases like "create test plan for X release", "generate test cases for these changes", "what should we test for version X", "run PR mode on connect PR 1406", "kickoff plan for epic CCCT-2600", "finalize pending test cases", or when given a milestone, version number, Jira release ticket, Connect PR number or Jira epic.
---

# QA Ticket Prep

## Overview

Four modes. Pick the one that matches the input:

| Input | Mode | Output |
| --- | --- | --- |
| Release version, milestone or Jira release ticket | **Release mode** (below) | Excel test plan for the release |
| One commcare-connect PR number | **PR mode** | Updated scripts + `test_plans/pending/connect-pr-<n>.yaml` + new tests |
| A Jira epic for a new feature, before any PR | **Kickoff mode** | `test_plans/features/<EPIC-KEY>.yaml` |
| "Finalize" + pending file(s) QA has tested | **Finalize mode** | Rows in the master test plan `.xlsx`; pending file removed |

The file formats for PR and kickoff mode are in `test_plans/README.md`. Read it first.

## Release mode

Given a release version or Jira release ticket, fetch all related PRs and tickets, read their content and comments, and produce a structured Excel test plan covering happy path, regression, and edge cases.

## Release mode: workflow

### Step 0 — Identify the Starting Point

**If given a Jira ticket (e.g. QA-8493):**
1. Read the ticket description and comments
2. Extract the release version from the ticket title or description
3. Extract any linked Jira tickets or PR references
4. Proceed to Step 1 using the version found

**If given a version number or milestone directly (e.g. "2.63"):**
- Proceed straight to Step 1

### Step 1 — Find All PRs for the Release

- Identify the GitHub milestone matching the release version
- Fetch all PRs under that milestone (open and closed)
- Note which PRs are **not yet merged** — write test cases for these normally but flag them (see Step 5)

### Step 2 — Read PRs and Linked Tickets

For each PR:
- Read the **title and description** (not review comments)
- Extract any linked Jira ticket keys from the PR body (e.g. CCCT-1234, SAAS-5678, QA-9012)

For each linked Jira ticket:
- Read the **description and comments** — comments often contain scope changes, QA findings, and edge cases that are not in the description

### Step 3 — Cross-Reference Release Notes

- Check the repo's release notes file (e.g. `RELEASES.md`) for the release version
- Identify anything mentioned in the release notes that has **no matching PR in the milestone** — flag these as gaps and note them in the Prerequisites tab

### Step 4 — Categorise Changes

Sort all changes into:
- **New feature** — needs happy path + regression + edge cases
- **Bug fix** — needs reproduction verification + regression check
- **Internal/analytics only** — no user-facing test cases needed; note it was reviewed and skipped

### Step 5 — Write Test Cases

Organise into one Excel tab per workflow/feature area. Each tab has these columns:

| Column | Notes |
|--------|-------|
| Test Case No | Format: TC-[AREA]-[NNN], e.g. TC-FAL-001 |
| Description | One-line summary of what is being tested |
| Steps to Test | Numbered, specific, reproducible steps |
| Expected Outcome | Clear pass condition |
| Status | Pass / Fail / Blocked / N/A — leave **blank** for unmerged PRs |
| Comments / Notes | For unmerged PRs add: "PR #XXXX not yet merged — confirm in build before testing" |

For each feature area cover:
1. **Happy path** — core successful flow end-to-end
2. **Regression** — areas adjacent to the change that could break
3. **Edge cases** — boundary values, offline behaviour, device rotation, upgrade from previous version, multiple simultaneous conditions

### Step 6 — Add a Prerequisites Tab

First tab in the workbook. List any setup required before testing can begin:
- Server-side configuration (e.g. accounts, assigned tasks, job setup)
- Device requirements (e.g. two devices for multi-device tests)
- Network conditions needed (e.g. airplane mode scenarios)
- App version to upgrade FROM for upgrade path tests

## Release mode: output format

- **File type:** Excel (.xlsx)
- **Tab order:** Prerequisites first, then one tab per workflow, then a Regression & Exploratory tab last
- **Naming:** One tab name per feature area (e.g. "Form Attachment Limit", "Push Notifications")
- **Styling:** Frozen header row, alternating row colours, wrapped text in steps/outcome cells

## Release mode: common mistakes

- **Only reading PR descriptions** — ticket comments frequently contain scope changes, discovered edge cases, and "this also covers X" notes that affect what needs testing
- **Skipping unmerged PRs** — write the test cases; leave Status blank and note the PR is unmerged so the tester knows to verify before running
- **Missing release note gaps** — always cross-reference RELEASES.md; features mentioned there without a matching PR may have been merged without a milestone tag or live in a different repo
- **No prerequisites tab** — testers get blocked on setup; document server-side requirements upfront
- **Internal-only changes with test cases** — analytics or dependency upgrades with no user-facing change don't need test cases; note them as reviewed and skipped to avoid noise

## PR mode (one commcare-connect PR)

Run from the dimagi-qa-ccc repo root with the PR number. `gh` must be authenticated.
The Playwright suite in `playwright_web/` is the target; do not use
`ai_testcases/generate_test.py`, which writes Selenium tests for the legacy `tests/web_tests/`.

### Step 1: Read the PR and decide whether to continue

```
gh pr view <n> --repo dimagi/commcare-connect --json number,title,body,headRefName,isDraft,state,labels,files,mergedAt
gh pr diff <n> --repo dimagi/commcare-connect
```

Stop, with a one-line note, when the PR is a draft, is from Dependabot, carries the
`no-qa` label, or only touches docs. Otherwise:

- Copy the PR template's **QA Plan** section verbatim into `qa_plan_from_pr`; treat it as the developer's intent, not as the full test scope.
- Collect Jira keys (e.g. CCCT-1234) from the title, body and branch name. Read each ticket's description **and comments**, and note its parent epic.

### Step 2: Impact check (scenario A: behaviour we already test)

```
cd playwright_web && python -m utils.impact_check --pr <n>
```

It lists locators whose anchor text, id or class disappears in the diff, the page
objects and tests that use them, and page objects that cite a changed Connect file.
Then confirm each hit by reading the diff, and look further for changes no locator
captures: URL or route changes, renamed form fields, new validation, changed defaults
(filters, sorting, page size), permission changes, and changed messages that tests
assert on (`grep` the tests and `test_data/web_test_data.yaml` for the old strings).

For every affected test, **never edit it in place**; the environment a run targets may not
have the PR yet:

1. Copy the test function as `<name>_pr<n>` in the same file and fix the copy. Mark it `@pytest.mark.pending_prod(pr=<n>)`.
2. Mark the original `@pytest.mark.replaced_by_pr(<n>)`. Change nothing else in it.
3. New or changed locators get new keys with a `_pr<n>` suffix in `playwright_web/locators/web_locators.yaml`; old keys stay for the original. Changed expected values get new keys in `test_data/web_test_data.yaml` the same way.
4. If the test already has a `pending_prod` copy from another open PR, update that copy and add a second `pending_prod(pr=<n>)` marker instead of making another copy (a copy then needs both PRs deployed).

Record each one under `updated_scripts` in the pending file, with the reason and the
master-plan row (`TC-...`) whose steps change.

### Step 3: New cases (scenario B: behaviour no script covers)

- If the PR's epic has `test_plans/features/<EPIC-KEY>.yaml`, mark which of its cases this PR delivers (`delivered_by`), automate those, and add anything the plan missed to `new_cases`.
- Otherwise classify the change (feature / bug fix / internal-only) and write cases as in release mode: happy path, regression around the change, edge cases.
- `plan_tab` must be an existing tab of `CCC_Web_Platform_MTP.xlsx` or `CCC_Mobile_App_Regression_MTP.xlsx` (list them with openpyxl). Use placeholder ids `TC-<AREA>-NEW-<k>`; finalize mode assigns real numbers.
- Automate a case when it fits the existing page objects. Mark it `pending_prod(pr=<n>)`, set `automation: automated` and fill in `test`. Use `candidate` when automation is possible but needs new setup or data, and `manual` otherwise.

Write `test_plans/pending/connect-pr-<n>.yaml` in the format from `test_plans/README.md`.
A rerun for the same PR (approval re-check) updates this file and the existing copies; it
does not create new ones.

### Step 4: Code standards (QA reviews every agent PR against these)

- No hardcoded test data in tests or page objects: values, expected strings and lists go in `test_data/web_test_data.yaml`.
- No inline XPaths in page objects: locators live in `web_locators.yaml`, dynamic ones filled in with `.format()`. No absolute or positional XPaths.
- No credentials in code; read them from settings or secrets.
- A test that changes shared data restores it, or says in its docstring why it can't.
- Short code comments, with no run ids or dates.

### Step 5: Verify before handing over

```
cd playwright_web
python -m pytest tests/unit -q
python -m pytest --collect-only -q --ignore=tests/unit
python -m pytest <new and copied tests> --env=stage --deployed-prs=<n>   # only if PR <n> is on staging
```

If the PR's code isn't on staging yet, say so in the summary instead of running the copies.
End with a summary in two lists, **Updated scripts** (each with its reason) and
**New test cases**, which becomes the QA PR description. Work on branch
`qa-agent/connect-pr-<n>`. Commit, push or open a PR only when asked.

## Kickoff mode (Jira epic, before any PR)

Run by QA by hand when an epic for a new feature is ready for development. No GitHub event triggers it.

1. Read the epic, its child tickets, their comments and any linked design docs.
2. Write `test_plans/features/<EPIC-KEY>.yaml`. Use ids `<EPIC-KEY>-NN`, a `plan_tab` per case, and an empty `delivered_by`.
3. Cover the whole feature: happy path, regression on the areas it touches, and edge cases. Each PR in the epic later fills in its part in PR mode.

## Finalize mode (after QA has tested)

Input: one or more `test_plans/pending/connect-pr-<n>.yaml` files whose `status` fields QA has filled in.

1. For each `updated_scripts` entry with a `master_plan_row`, update that row's steps and expected outcome in the right `.xlsx`.
2. Append each `new_cases` entry to its `plan_tab`, continuing that tab's `TC-[AREA]-NNN` numbering. Write the real id back into any feature plan that references the case.
3. Use openpyxl and keep the sheet's existing styles, column order and header row. Don't touch other tabs.
4. Delete the processed pending file(s). Report which rows were added or changed, since the `.xlsx` diff can't be reviewed.

## PR mode: common mistakes

- **Editing an affected test in place.** Prod and parts of staging still run the old behaviour; always copy and mark it.
- **Trusting the impact check alone.** It only sees locator anchors. Defaults, routes, permissions and asserted messages need reading the diff.
- **Writing to the master `.xlsx` in PR mode.** Only finalize mode touches it.
- **Using the legacy generator.** `ai_testcases/` targets the Selenium suite; PR mode writes Playwright tests.
