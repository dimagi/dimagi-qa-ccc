# Test plans

| Path | What it is | Who writes it |
| --- | --- | --- |
| `CCC_Web_Platform_MTP.xlsx`, `CCC_Mobile_App_Regression_MTP.xlsx` | Master test plans | QA, via the skill's finalize mode |
| `pending/connect-pr-<n>.yaml` | Test cases drafted for one commcare-connect PR, waiting for QA to test it | The QA agent (skill PR mode) |
| `features/<EPIC-KEY>.yaml` | Test plan for a new feature, written before any PR exists | QA, via the skill's kickoff mode |

The master plans are binary, so the agent never edits them directly: two agent PRs
touching the same `.xlsx` would always conflict and could not be reviewed as a diff.
Each PR gets its own YAML file instead, and finalize mode moves the tested cases into
the right `.xlsx` tab once, after QA has run them.

## `pending/connect-pr-<n>.yaml`

```yaml
connect_pr: 1406
title: Clear work areas when an opportunity is re-planned
jira: [CCCT-2649]
epic: CCCT-2600            # null when the ticket has no epic
feature_plan: features/CCCT-2600.yaml   # null when there is no kickoff plan
classification: feature    # feature | bug_fix | internal_only
qa_plan_from_pr: |         # the PR template's "QA Plan" section, verbatim
  ...

# Scenario A: existing scripts this PR breaks or changes
updated_scripts:
  - original: playwright_web/tests/test_olp_04.py::test_olp_04_verify_opportunity_details_in_dashboard
    copy: playwright_web/tests/test_olp_04.py::test_olp_04_verify_opportunity_details_in_dashboard_pr1406
    reason: Work area column removed from the dashboard (opportunity_dashboard.html)
    locators_added: [opportunity_dashboard_page.work_area_summary_pr1406]
    master_plan_row: TC-OLP-004   # row finalize mode updates, if the case's steps change

# Scenario B: behaviour no existing script covers
new_cases:
  - id: TC-MAP-NEW-1         # placeholder; finalize mode assigns the real TC-[AREA]-NNN
    plan_tab: Microplanning   # existing tab in the web or mobile master plan
    feature_case: CCCT-2600-03   # case id in the feature plan this PR delivers, if any
    description: Re-planning clears existing work areas
    steps:
      - Open an opportunity with work areas assigned
      - Re-run planning
    expected: Previous work areas are gone; new ones are listed
    automation: automated    # automated | candidate | manual
    test: playwright_web/tests/test_map_03.py::test_replan_clears_work_areas
    status: ""               # QA fills in: Pass | Fail | Blocked | N/A

skipped:                     # reviewed and deliberately not tested, with the reason
  - Dependency bump in pyproject.toml, no user-facing change
```

Every test the agent adds or copies carries `@pytest.mark.pending_prod(pr=<n>)`, and
every original a copy replaces carries `@pytest.mark.replaced_by_pr(<n>)`; see
`playwright_web/utils/pr_gating.py` for how each run picks between them.

## `features/<EPIC-KEY>.yaml`

```yaml
epic: CCCT-2600
title: Microplanning v2
written: 2026-10-22
cases:
  - id: CCCT-2600-03
    plan_tab: Microplanning
    description: Re-planning clears existing work areas
    steps: [...]
    expected: ...
    delivered_by: [1406]     # Connect PRs that implement this case; filled in by PR mode
    automation: automated
```

A feature split across several tasks or PRs shares this one plan. Each PR's agent run
fills `delivered_by` for the cases that PR implements, automates those, and lists any
behaviour the plan missed as `new_cases` in its pending file.
