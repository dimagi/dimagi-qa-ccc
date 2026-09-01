"""Opportunity Dashboard - Tier 2/3 budget MUTATIONS (OD_10/11/12/14/15).

These tests actually change data (a worker's max visits), so they follow the
mutate-then-revert policy: capture the baseline, apply the change, assert, and
restore the baseline in a `finally` block. Every test is net-zero.

Because they mutate shared staging data, the whole module is GATED behind
`OPD.mutation_opportunity_name[_staging]` and skips until that key names an
opportunity with claimed workers (safe to touch). It is deliberately left unset in
committed data so the module never mutates unattended in CI - a human points it at
a known opp (e.g. after confirming with the opp owner) and runs it supervised.
Per policy: mutate-then-revert on staging, assert-and-skip on prod.

One login per module (module-scoped `budget` fixture). Source facts: the add-budget
view answers a valid submit with a 302 back to the page + a success flash; the
page's own table shows each worker's summed "Max Visits"; decrease below completed
(or below zero) is rejected with a fixed error. See
project_connect_opportunity_dashboard memory.
"""

import pytest

from flows.olp_setup import PM_ORG
from flows.tasking_static import env_value, login_to_connect
from pages.connect_opportunity_dashboard_page import OpportunityDashboardPage
from pages.connect_opportunity_list_page import ConnectOpportunityListPage


def _mutation_opp(test_data, config):
    return env_value(test_data.get("OPD") or {}, "mutation_opportunity_name", config)


def _open_dashboard(page, test_data, config, settings, name):
    connect_page = login_to_connect(page, config, settings, PM_ORG)
    olp = ConnectOpportunityListPage(connect_page)
    olp.verify_loaded()
    if connect_page.locator(olp.ROW_LINK_BY_NAME.format(name=name)).count() == 0:
        pytest.skip(f"Mutation opportunity {name!r} not visible to this account/env")
    olp.open_opportunity(name)
    dash = OpportunityDashboardPage(connect_page)
    dash.verify_loaded()
    dash.dashboard_url = dash.page.url
    return dash


@pytest.fixture(scope="module")
def budget(browser, config, settings, test_data):
    name = _mutation_opp(test_data, config)
    if not name:
        pytest.skip(
            "OPD.mutation_opportunity_name not set - budget-mutation tests are gated so they "
            "never change shared data unattended. Point it at a staging opp with claimed workers "
            "and run supervised."
        )
    if config.env == "prod":
        pytest.skip("Budget mutations run on staging only (assert-and-skip on prod).")
    context = browser.new_context(ignore_https_errors=True)
    page = context.new_page()
    try:
        try:
            dash = _open_dashboard(page, test_data, config, settings, name)
        except Exception:
            page.close()
            page = context.new_page()
            dash = _open_dashboard(page, test_data, config, settings, name)
        yield dash
    finally:
        context.close()


def _require_claimed_workers(budget):
    budget.goto_add_budget()
    if not budget.add_budget_has_claimed_workers():
        pytest.skip("Mutation opportunity has no claimed workers - the visits form is not rendered")


def test_opd_10_add_budget_existing_worker(budget):
    """OD_10: increasing a worker's visits applies and is reflected in Max Visits;
    reverted afterwards."""
    _require_claimed_workers(budget)
    before = budget.add_budget_row_max_visits(0)
    increased = False
    try:
        budget.apply_budget_change(1, "increase_visits")
        increased = True
        budget.goto_add_budget()
        after = budget.add_budget_row_max_visits(0)
        assert after > before, f"Max Visits did not increase (before={before}, after={after})"
    finally:
        if increased:
            budget.apply_budget_change(1, "decrease_visits")
            budget.goto_add_budget()
            restored = budget.add_budget_row_max_visits(0)
            assert restored == before, f"REVERT FAILED: before={before}, restored={restored}"


def test_opd_11_increase_visits_proportional(budget):
    """OD_11: increasing by N raises total Max Visits by N x (payment units) - a
    positive multiple of N; reverted afterwards."""
    _require_claimed_workers(budget)
    n = 2
    before = budget.add_budget_row_max_visits(0)
    increased = False
    try:
        budget.apply_budget_change(n, "increase_visits")
        increased = True
        budget.goto_add_budget()
        after = budget.add_budget_row_max_visits(0)
        delta = after - before
        assert delta > 0 and delta % n == 0, (
            f"increase not proportional to {n} (before={before}, after={after}, delta={delta})"
        )
        budget._step(f"Increase delta {delta} = {n} x {delta // n} payment unit(s)")
    finally:
        if increased:
            budget.apply_budget_change(n, "decrease_visits")
            budget.goto_add_budget()
            restored = budget.add_budget_row_max_visits(0)
            assert restored == before, f"REVERT FAILED: before={before}, restored={restored}"


def test_opd_12_decrease_visits_proportional(budget):
    """OD_12: decreasing by N lowers total Max Visits by N x (payment units). Runs
    as increase-then-decrease so it is net-zero and always valid (no completed-visit
    dependency)."""
    _require_claimed_workers(budget)
    n = 2
    before = budget.add_budget_row_max_visits(0)
    increased = False
    try:
        # Create headroom so the decrease is unconditionally valid.
        budget.apply_budget_change(n, "increase_visits")
        increased = True
        budget.goto_add_budget()
        mid = budget.add_budget_row_max_visits(0)
        # The decrease under test.
        budget.apply_budget_change(n, "decrease_visits")
        increased = False
        budget.goto_add_budget()
        after = budget.add_budget_row_max_visits(0)
        delta = mid - after
        assert delta > 0 and delta % n == 0, (
            f"decrease not proportional to {n} (mid={mid}, after={after}, delta={delta})"
        )
        assert after == before, f"decrease did not return to baseline (before={before}, after={after})"
    finally:
        if increased:  # decrease step failed - undo the earlier increase
            budget.apply_budget_change(n, "decrease_visits")
            budget.goto_add_budget()
            restored = budget.add_budget_row_max_visits(0)
            assert restored == before, f"REVERT FAILED: before={before}, restored={restored}"


def test_opd_14_cannot_decrease_below_completed_or_zero(budget):
    """OD_14: decreasing by more than the available visits is rejected with the
    'Cannot decrease...' error and applies no change (same validation/message that
    guards decreasing below already-completed visits)."""
    _require_claimed_workers(budget)
    before = budget.add_budget_row_max_visits(0)
    # A decrease far larger than any max_visits forces the below-zero branch, which
    # raises the same error as the below-completed branch - no data is mutated.
    applied = budget.apply_budget_change(999999, "decrease_visits")
    assert not applied, "A huge decrease should be rejected, not applied"
    assert budget.budget_decrease_error_present(), "Expected the 'Cannot decrease...' validation error"
    budget.goto_add_budget()
    after = budget.add_budget_row_max_visits(0)
    assert after == before, f"Rejected decrease must not change Max Visits (before={before}, after={after})"


def test_opd_15_change_reflected_on_connect_workers(budget):
    """OD_15: an add-budget change is reflected on the Connect Workers (Deliver)
    page - the progress-bar denominators (max visits) move by the same delta.
    Reverted afterwards. (Mobile reflection is out of web scope.)"""
    _require_claimed_workers(budget)
    before_ab = budget.add_budget_row_max_visits(0)
    budget.goto_worker_tab("deliver")
    before_del = budget.deliver_denominator_sum()
    increased = False
    try:
        budget.apply_budget_change(1, "increase_visits")
        increased = True
        budget.goto_add_budget()
        after_ab = budget.add_budget_row_max_visits(0)
        delta = after_ab - before_ab
        assert delta > 0, f"Max Visits did not increase (before={before_ab}, after={after_ab})"
        budget.goto_worker_tab("deliver")
        after_del = budget.deliver_denominator_sum()
        assert after_del - before_del == delta, (
            f"Deliver page did not reflect the change: add-budget delta={delta}, "
            f"deliver delta={after_del - before_del}"
        )
    finally:
        if increased:
            budget.apply_budget_change(1, "decrease_visits")
            budget.goto_add_budget()
            restored = budget.add_budget_row_max_visits(0)
            assert restored == before_ab, f"REVERT FAILED: before={before_ab}, restored={restored}"
