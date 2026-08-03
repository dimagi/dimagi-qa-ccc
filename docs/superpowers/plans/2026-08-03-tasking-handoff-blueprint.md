# Tasking Automation — Handoff Blueprint (2026-08-03)

Ticket: **CCCT-2658** — automate the Connect web tasking / re-learn workflow.

Plan workbook: `Tasking_Workflow_Automation_Test_Plan.xlsx`. **It is not in the
repo** — never committed, not ignored, not present anywhere in the tree. Earlier
revisions of this document said it was at the repo root; it is not, so the "43
cases" denominator used below cannot be checked against anything. Treat totals as
unverified until the workbook is committed.

**Updated 2026-08-03 (later session).** Everything in §4 of the previous revision
is done, and J2/J3/J4 plus the mobile chain have now run green on staging.

---

## 1. What is built, and what is actually proven

### Verified green (assertions passed in a real run)

Every row below passed on staging on 2026-08-03. Nothing in the suite is
"written but unrun" any more.

| Test | Cases | Evidence |
|---|---|---|
| `tests/unit/` (20 tests) | — | Local, <1s |
| `test_olp_01_02_03.py` (+ `flows/tasking_config.py`) | **TTC-002**, TTC-004, IMP-004 | 185s |
| `test_task_type_config.py` (J1) | TTC-001, 004, 005, 006, TAS-005 | 81s, first try |
| `test_task_assignment_lifecycle.py` (J2) | TAS-001, 002, 004(pos), 006, 007, TLV-001, TDL-001, 002 | 71s, after 3 fixes |
| `test_task_views_filters.py` (J3) | TLV-002, 003, 004, 005(basic) | 76s, after 2 fixes |
| `test_task_permissions.py` (J4) | PRM-001, 002, 003 | 72s, first try |
| `test_e2e_relearn_lifecycle.py` + `worker_relearn_task.yaml` | **E2E-001, E2E-005, E2E-006**, TAS-001, TAS-009, TDL-003 | 7m05s |

The hybrid pass covers the whole chain: web assigns → device signs in (2.63.4) →
Connect access granted on a clean install → deliver app downloaded → **blocking
warning visible** → re-learn form completed → **Connect's task-completion push
arrives** → warning gone, replaced by "All required tasks have been completed" on
**both** the delivery-progress card and the app home tile → web reads **Complete**
→ no Edit control and a disabled checkbox on the completed row → the same type is
re-assignable, and that leftover is deleted.

**27 distinct case ids now pass.** The denominator is unverified (see the missing
workbook above), so quote the 27, not a fraction.

### Not covered, by decision or still to do

- **TTC-003** dropped: the hybrid test proves slug integrity more strongly, since a
  slug that stopped matching the HQ task unit id makes completion impossible.
- **TLV-006 and IMP-003** stay skipped behind `TASKING.switch_enabled: false` (no
  access to the `worker_visits_tasks` waffle switch). **IMP-002** dropped.
- **E2E-002 / E2E-003** still to add, as a pair, to the mobile chain.
- **OCS/chatbot task types** deferred: the automation user needs an OCS account.

### Bugs found and fixed in our own code

- Create Task modal contains a hidden **"Connect OCS account"** submit button
  (`form="ocs-connect-form"`) inside `#create-task-form`; the Save locator now
  excludes `@form` buttons. Would have broken J2 too.
- Connect answers task create/edit/delete with **HX-Redirect**, so
  `wait_for_load_state("load")` returned against the doomed page. Fixed with
  `BasePage.click_and_await_redirect`.
- Success-banner checks read the *first* banner and picked up a stale
  "Successfully deleted…". Now filtered by expected text, and on failure they
  print every message on the page.
- `delete_tasks_for_workers` clicked a disabled Delete when only completed rows
  existed (their checkboxes are disabled). Now no-ops.
- `parse_org_and_opp` assumed numeric opportunity ids; staging uses UUIDs.
- Runner now retries once when BrowserStack returns build status `error`
  ("Could not start a session") — seen twice in ~12 runs. `failed` is never retried.

Found by finally running J2–J4 and the mobile chain (all test-side, **no product
bugs**):

- Due dates render via `DMYTColumn` → `utils.tables.DATE_FORMAT` (`"%d-%b-%Y"`,
  e.g. `10-Aug-2026`), or `DATE_TIME_FORMAT` for an aware datetime. The assertion
  had guessed five other formats and matched none of them.
- **Duplicate assignment is not an inline form error.** `CreateTaskForm` validates
  fine — it only excludes already-assigned types from the dropdown when the view
  knows the worker up front, which it does not for a freshly opened modal.
  `AssignedTask.assign` raises `TaskAlreadyAssignedError`, the view flashes a
  Django error and **still answers with HX-Redirect**, so the modal closes and the
  reason appears in a `bg-message-error` banner on the reloaded list. Assert the
  counts too: a banner only proves a message was shown.
- J2 had **no cleanup at all** (J3/J4 both have `finally` blocks), so its own
  failure left a pending task that blocked every later run on the duplicate
  constraint. It now pre-cleans before taking the metric baseline.
- J2's closing check assumed a clean opportunity: "no row for this worker" can
  never hold on the static one, which accumulates undeletable completed rows.
- The **Workers > Tasks tab is a `GroupedTable`**: `header_columns` are only index,
  status and name, and each task is a sibling `<tr x-show="open" x-cloak>`. The
  header row must be clicked or the task columns are simply not in the visible text.
- The **per-worker Tasks drill-down 404s** without `?user=<ConnectUser.user_id>`
  (`WorkerPageView`: "A valid worker must be specified."), and the test never
  passed one, so it waited on rows on a 404 page. The Tasks tab cannot supply the
  id either — its name column is a plain `UserInfoColumn`; every `?user=` link in
  the product points at `user_visits_list`. Read it from the **Delivery tab**,
  which uses `GroupedByWorkerMixin` and does wrap the name in a link.
- `apply_env_overrides` treated any line without a colon as the end of the `env:`
  block, and a bare `#` comment qualifies — so a key declared below a comment was
  appended *and* left in place. Python's YAML keeps the last duplicate silently;
  BrowserStack rejects the suite with 422
  `[BROWSERSTACK_INVALID_TESTSUITE] Invalid YAML syntax`. Fixed, with a regression
  test. Upload failures now surface BrowserStack's response body, which is the only
  place that reason appears.

---

## 2. Project structure

Worktree: **`C:\dqccc-tasking`**, branch **`feature/tasking-web-automation`**,
**12 commits ahead of origin** as of this revision. Draft **PR #23** is open
against `main` but its head is far behind local. **Nothing may be pushed without
Nitin saying so at that moment.**

```
dimagi-qa-ccc/
├── app/app-cccStaging-release.apk        # 2.63.4 (was 3-Apr build; updated)
├── maestro_mobile/
│   ├── flows/
│   │   ├── shared_login_signup.yaml      # phone + name entry (reused)
│   │   ├── login_signup_success.yaml     # BROKEN on 2.63.4 (see §4)
│   │   ├── login_account_locked.yaml     # BROKEN on 2.63.4
│   │   └── worker_relearn_task.yaml      # NEW, green
│   └── scripts/run_on_browserstack.py    # --flows / --env / run_flows() / retry
├── playwright_web/
│   ├── conftest.py                       # + pytest_html_results_summary hook
│   ├── pytest.ini                        # initial_sort, render_collapsed pinned
│   ├── flows/
│   │   ├── olp_setup.py                  # reusable OLP setup; master app names
│   │   ├── tasking_static.py             # require_static_opp / login_to_connect
│   │   └── mobile_runner.py              # bridge to the BrowserStack runner
│   ├── pages/
│   │   ├── base_page.py                  # + click_and_await_redirect, TomSelect
│   │   ├── connect_task_types_page.py
│   │   ├── connect_assigned_tasks_page.py
│   │   └── connect_workers_page.py       # invite + async polling
│   ├── locators/web_locators.yaml        # tasking sections appended
│   └── tests/
│       ├── unit/                         # 19 tests incl. maestro env injection
│       ├── test_task_type_config.py              # J1  GREEN
│       ├── test_task_assignment_lifecycle.py     # J2  GREEN
│       ├── test_task_views_filters.py            # J3  GREEN
│       ├── test_task_permissions.py              # J4  GREEN
│       ├── test_e2e_relearn_lifecycle.py         # hybrid GREEN
│       └── test_setup_tasking_opportunity.py     # SETUP_TASKING=1 only
└── test_data/web_test_data.yaml          # TASKING + TASKING_HYBRID blocks
```

### Environment facts

- Staging: `connect-staging.dimagi.com`, HQ `staging.commcarehq.org/a/connectqa-automation`.
- Masters (selected **by name**, partial match): **`[Master] Learn App`**,
  **`[Master] Delivery App`** (`29c90dd686f649e394b974c9c3ba8975`). Both released.
- **Year-long opportunity** (reuse until LDVP exists):
  `Demo Opportunity_31-Jul-2026 : 18:39`, org `pm_automation_01`,
  opp `9d533d0d-b835-488a-8726-7d2aac52df95`, deliver app copy
  `6b7240a9db5741f49c5e91bd224b3140`, 365-day window, task type
  `Relearn Task Unit` (slug `relearn_task`) active.
- **Mobile worker**: `+7426` + `3119728` (= `+74263119728`),
  PersonalID name `Relearn Task User`, backup code `123456`. Learning and the
  assessment are already complete, so the worker is delivering.
- Task units in both apps: `relearn_task` ("Relearn Task Unit") and
  `relearn_task_2` ("Relearn Task Unit 2"), each with a Name question plus a
  label-only note.
- **J1 owns a sandbox task type** on the static opportunity, created once from
  `relearn_task_2` and thereafter only renamed / archived / unarchived. Its name
  toggles between `Relearn Sandbox A` and `Relearn Sandbox B` every run — the slug
  is never rendered in the table, so toggling two known names is what keeps the row
  findable without carrying state between runs. J1 must never touch the live
  `relearn_task` type.
- Module and form labels differ in **capitalisation** between master and copy
  (`Re-Learn Task` vs `Re-learn Task`), and Maestro matches case-sensitively, so
  the flow uses character classes (`Re-[Ll]earn Task`), not `(?i)`.

---

## 3. Rules and hard-won implementation details

### Working agreements (non-negotiable)

1. **Never push or open a PR** unless told to at that moment. Commit locally freely.
2. **On any failure, send the screenshot** via SendUserFile with a one-line
   statement of the failed step.
3. **Never re-run opportunity-creating setup to debug a post-creation fix.**
   Reuse existing data; minimise trash on staging.
4. **When Nitin describes a UI path from manual testing, follow it literally.**
   An app definition read from the master does not necessarily match the build on
   the device. Verify against the *opportunity's own* app copy.
5. Only claim a case verified once its assertion has passed in a real run.

### Connect web behaviours

- Task-type **slug is permanently consumed** per app: unique on (app, slug),
  unconditional, no delete in the UI, and archiving does not free it.
- Archived task types **stay listed** with the Archived date filled (MM/DD/YYYY).
- The slug never renders in the config table — verify it from the task-unit
  option's *value*, not the table.
- Being **invited is not enough** to assign a task: the Create Task worker
  dropdown lists only workers who **accepted** on their device.
- Same task type can be re-assigned after completion (the uniqueness constraint
  applies only while `status=assigned`), which is what makes re-runs possible.
- Only PM-org admins create/delete; any org member can edit a due date (PR #1381).
- Automation-created opportunities get a **7-day** window (start today+2), hence
  the deliberate 365-day one. `OLP_2`/`OLP_3` start/end dates in test data are
  dead config — the code computes them.
- HQ's "copy application" takes the **released** build, so the master must be
  released *before* copying or the copy silently lacks new forms.

### Mobile behaviours (APK 2.63.4)

- Backup code screen is `fragment_recovery_code.xml`: six-box `NumericCodeView`
  (`backup_code_view`, children have index ids only), submit
  `connect_backup_code_button`, error `connect_backup_code_error_message`.
  The old `connect_backup_code_input` no longer exists (removed 3 Apr 2026,
  commit `3d194096c`).
- `PersonalIdManager.completeSignin()` **auto-opens the nav drawer**. Dismiss by
  tapping the scrim (~92% width). **Pressing Back on the setup screen exits the app.**
- A fresh install has **no Connect access** (`hasConnectAccess` is a local flag),
  so the drawer has no "Opportunities". If `connect_login_button`
  ("Go to Connect menu") is absent, use the setup screen's overflow →
  **"Refresh Opportunities"**, then the button appears.
- On the Connect job list the opportunity **title is not clickable** — use the
  card's `btn_resume` (downloads/opens the app) or `btn_view_info`.
- The pending-task warning is on the **deliver app home screen** next to
  Start/Sync: *"Complete assigned tasks to continue delivering services."*
- Clearing it needs the Connect card's own **"Click to sync progress"**
  (`btnSync`) — neither a CommCare sync nor merely opening the screen suffices.
  **Staging takes minutes** to reflect a submission; prod is near-instant.
- **Wait for Connect's task-completion push, do not wait a fixed time.** Connect
  fires it from `transaction.on_commit` once the task is marked complete, so its
  arrival is proof the server state is ready to fetch. Title **"Task Completed"**,
  body **"You have completed the task '<task type name>'."**
  (`send_task_completion_notification`). The earlier flow synced ~10s after
  submitting and then waited 300s without re-fetching, so the stale pending state
  could never clear; it passed once on timing luck. Waiting on the push resolved in
  **~28s** and also earns E2E-005.
  - Open the shade **first**, then wait: notifications land in an open shade live,
    so one `extendedWaitUntil` suffices and no retry loop is needed.
  - **Back closes the shade. An upward swipe does not** — a vertical drag inside an
    open shade scrolls the notification list, leaving the panel up so every later
    assertion runs against system UI.
  - `launchApp` needs `permissions: all: allow`: Android 13 gates
    POST_NOTIFICATIONS behind a runtime prompt and `clearState` re-asks each run.
  - Unexplained: the notification was gone from the shade ~1 minute after being
    asserted. Catching it live is what makes this reliable.
- **A failed command inside a Maestro `repeat` aborts the whole loop**, so
  sync-then-short-wait retry loops fail on the first round. Do not reintroduce
  one without a construct that swallows the intermediate failure. There is no
  tolerant sleep in Maestro either — an `optional: true` tap on an absent element
  burns its ~7s element timeout and is WARNED rather than failed, which is the only
  delay that is safe inside a `repeat`.
- The warning and the completion message both render on **two** surfaces:
  `view_job_card.xml` (app home job tile) and `view_progress_job_card.xml`
  (Connect delivery-progress card). Both are asserted.
- The re-learn form completes via the **next arrow** (`nav_btn_next`); FINISH is
  often never shown, so treat `nav_btn_finish` as optional and assert
  `.*form sent to server.*` on the home screen instead.
- Unproven on this Maestro version (1.39.13): `below:` as a sole selector,
  `repeat: while:`. `repeat: times:`, `point:` taps and `runFlow: when:` all work.

---

## 4. Exact next steps

Steps 1 and 2 of the previous revision are **done**. The whole suite is green:
unit → OLP(+TTC-002) → J1 → J2 → J3 → J4 → mobile chain. Run it in that order and
**strictly sequentially** — J2–J4 all assign the same type to the same worker, so
parallel runs collide on the duplicate-assignment constraint. Each self-cleans.
Web journeys are ~70–90s each, the OLP test ~3min, the mobile chain ~7min.

### Next — extend the mobile chain to E2E-002 + E2E-003

One device session doing: assign → **submit Registration Form visit (rejected,
"Pending Task" flag)** → complete the re-learn form → **submit another visit
(accepted)**. They must land as a pair, since 002 alone would still pass if
delivery were blocked permanently. Registration Form fields: name, picture
(skippable), id (unique numeric), GPS (skippable), Finish. One cold start instead
of three saves ~20 min/run.

### Then

- **Commit the plan workbook.** `Tasking_Workflow_Automation_Test_Plan.xlsx` is not
  in the repo, so the case list and the `Automation Target` mapping exist nowhere in
  version control and no total can be checked.
- Decide on **pushing**: the branch is 12 commits ahead and draft PR #23 is far
  behind local.
- Consider retrying the BrowserStack **uploads**, not just session start: a
  transient `ConnectionResetError` on the test-suite upload cost a whole run.

### Also outstanding

- **`login_signup_success.yaml` and `login_account_locked.yaml` are broken
  against 2.63.4** (removed `connect_backup_code_input`; they also assert drawer
  items "Opportunities" and "GO TO CONNECT MENU" that no longer render). The
  Maestro CI job will go red once the 2.63.4 APK lands on `main`. Nitin has not
  said who fixes these.
- **CI shape**: unit + J1–J4 as the per-PR gate (~12 min, no device); the mobile
  chain nightly or on demand (slow, ~2-in-12 BrowserStack session flake).
- **OCS/chatbot task types**: functionality works, but the automation user needs
  an OCS account to use "Connect OCS account". Deferred, not skipped.
- **When LDVP is automated**, the tasking stage folds into it (after the delivery
  and payment stages, since a pending task rejects visits) and stops needing its
  own opportunity. Pass setup via a shared artifact, not one mega-test.
- Dropped by decision: the `worker_visits_tasks` waffle switch (no access, so
  TLV-006/IMP-003 stay skipped) and IMP-002 (suspected blank Name/Description in
  the worker task-details panel).
