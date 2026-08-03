# Tasking Automation — Handoff Blueprint (2026-08-03)

Ticket: **CCCT-2658** — automate the Connect web tasking / re-learn workflow.
Plan workbook: `Tasking_Workflow_Automation_Test_Plan.xlsx` (43 cases; the
`Automation Target` column maps each case to a test or marks it deferred/manual).

---

## 1. What is built, and what is actually proven

### Verified green (assertions passed in a real run)

| Test | Cases | Evidence |
|---|---|---|
| `test_task_type_config.py` (J1) | TTC-001…006, TAS-005 | CI green on PR #23 |
| `test_e2e_relearn_lifecycle.py` + `worker_relearn_task.yaml` | **E2E-001, E2E-006**, TAS-001 | Passed end to end 2026-08-03, 5m54s |
| `test_olp_01_02_03.py`, `test_olp_04.py` | IMP-004 | CI green + local |
| `tests/unit/` (19 tests) | — | Local, <1s |

The hybrid pass covers the whole chain: web assigns → device signs in (2.63.4) →
Connect access granted on a clean install → deliver app downloaded → **blocking
warning visible** → re-learn form completed → **warning gone, replaced by "All
required tasks have been completed"** → web reads **Complete** (Open 0, Complete 1).

**Verified total: 11 of 43 cases.** Do not claim more.

### Written but NEVER executed — treat as unproven

`test_task_assignment_lifecycle.py` (J2), `test_task_views_filters.py` (J3),
`test_task_permissions.py` (J4) — 16 cases. They self-skip because
`TASKING.static_*` is unset. J2 shares code paths where two real bugs were found
via the hybrid test, so expect failures on first run.

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

---

## 2. Project structure

Worktree: **`C:\dqccc-tasking`**, branch **`feature/tasking-web-automation`**,
**5 commits ahead of origin** (plus whatever is committed at handoff).
Draft **PR #23** is open against `main` but its head is behind local. **Nothing
may be pushed without Nitin saying so at that moment.**

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
│       ├── test_task_assignment_lifecycle.py     # J2  unrun
│       ├── test_task_views_filters.py            # J3  unrun
│       ├── test_task_permissions.py              # J4  unrun
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
  Current flow: one sync then a **300s** wait (this is what passed).
- **A failed command inside a Maestro `repeat` aborts the whole loop**, so
  sync-then-short-wait retry loops fail on the first round. Do not reintroduce
  one without a construct that swallows the intermediate failure.
- The re-learn form completes via the **next arrow** (`nav_btn_next`); FINISH is
  often never shown, so treat `nav_btn_finish` as optional and assert
  `.*form sent to server.*` on the home screen instead.
- Unproven on this Maestro version (1.39.13): `below:` as a sole selector,
  `repeat: while:`. `repeat: times:`, `point:` taps and `runFlow: when:` all work.

---

## 4. Exact next steps

### Step 1 — five code changes (all agreed, none started)

1. `flows/olp_setup.py`: `LEARN_APP_MASTER = "[Master] Learn App"`,
   `DELIVER_APP_MASTER = "[Master] Delivery App"`. **Required** — the old
   `[08/12] …` names are stale and `test_olp_01_02_03` will fail without this.
2. `worker_relearn_task.yaml` env → case-tolerant patterns, because master and
   copy differ in casing (`Re-Learn Task` vs `Re-learn Task`;
   `Re-learn form` vs `Re-learn Form`; `Second Relearn form` vs `… Form`):
   `TASK_MODULE: "Re-[Ll]earn Task"`, `TASK_FORM: "Re-learn [Ff]orm"`.
   Use character classes, not `(?i)`. Note `Re-learn [Ff]orm` does not match
   "Second Relearn Form" (no hyphen), so the two stay distinguishable.
3. Restructure **J1** to run on the year-long opportunity without consuming slugs:
   - create its **sandbox type from `relearn_task_2`** if absent, selecting by
     option **value** (both labels are similar), and identify it by **slug**
     afterwards because TTC-005 renames it;
   - drop the "task type table is empty" and copied-app-name assertions;
   - archive **and unarchive** only its own sandbox type — never the live
     `relearn_task`, or J2–J4 and the hybrid test break;
   - keep **TTC-002 (create)** on the fresh opportunity that
     `test_olp_01_02_03` builds, where consuming a slug is free;
   - **drop TTC-003** as a standalone check — the hybrid test proves slug
     integrity more strongly (a mismatch makes completion impossible).
   - Run J1 first in the sequence and assert the type is assignable again before
     finishing, so a broken unarchive fails fast instead of poisoning later tests.
4. `test_data/web_test_data.yaml` → fill `TASKING.static_*` from the year-long
   opportunity (`static_org: pm_automation_01`,
   `static_opp_id: 9d533d0d-b835-488a-8726-7d2aac52df95`,
   `static_worker: Relearn Task User`, `static_task_type: Relearn Task Unit`,
   plus `network-manager` / `Network Manager` for J4). This activates J2–J4.
5. Move the completed-task assertions (**TAS-009** no Edit on completed rows,
   **TDL-003** completed not deletable, plus re-assign-after-completion) to the
   **end of the mobile chain**, where a completed task is guaranteed — not into
   J2, where they would depend on leftovers and fail on a clean environment.

### Step 2 — run in this order, fixing what reality disagrees with

Unit tests → **J1** → **J2** → **J3** → **J4** → mobile chain.
Strictly sequential: J2–J4 all assign the same type to the same worker, so
parallel runs collide on the duplicate-assignment constraint. Each self-cleans.
Expect several rounds per test (J1 took 4, the mobile flow ~8).

### Step 3 — then extend the mobile chain

One device session doing: assign → **submit Registration Form visit (rejected,
"Pending Task" flag)** → complete the re-learn form → **submit another visit
(accepted)**. Covers **E2E-002 + E2E-003**; must be a pair, since 002 alone would
still pass if delivery were blocked permanently. Registration Form fields:
name, picture (skippable), id (unique numeric), GPS (skippable), Finish.
One cold start instead of three saves ~20 min/run.

**E2E-005 (push notifications)** — recommended **manual**. Depends on FCM
reaching a cloud device and reading the notification shade; if automated at all,
assert the app's own Notifications screen.

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
