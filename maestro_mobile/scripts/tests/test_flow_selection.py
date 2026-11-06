"""Unit tests for picking which flows a run executes (--tag / --flows)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import run_on_browserstack as runner  # noqa: E402

# The workflow's "What to run" dropdown offers these, lower-cased into --tag.
DROPDOWN_TAGS = {"login", "map", "profile", "recovery"}


def test_every_suite_flow_has_a_dropdown_tag():
    untagged = [flow for flow in runner.TEST_FLOWS if not runner.flow_tags(flow) & DROPDOWN_TAGS]
    assert untagged == []


def test_no_selection_runs_the_whole_suite():
    assert runner.select_flows() == runner.TEST_FLOWS


def test_tag_keeps_suite_order_and_only_matching_flows():
    selected = runner.select_flows(tags=["profile"])
    assert selected and all("profile" in runner.flow_tags(flow) for flow in selected)
    assert selected == [flow for flow in runner.TEST_FLOWS if flow in selected]


def test_several_tags_combine():
    assert set(runner.select_flows(tags=["login", "recovery"])) == {
        flow for flow in runner.TEST_FLOWS if runner.flow_tags(flow) & {"login", "recovery"}
    }


def test_explicit_flows_win_over_tags():
    assert runner.select_flows(tags=["profile"], flows=["map_10_toggle_panel_visible.yaml"]) == [
        "map_10_toggle_panel_visible.yaml"
    ]


def test_unknown_tag_is_an_error():
    with pytest.raises(ValueError, match="No flow in TEST_FLOWS carries"):
        runner.select_flows(tags=["no_such_area"])


def test_env_baking_keeps_the_tags_header():
    text = (runner.FLOWS_DIR / "profile_view.yaml").read_text(encoding="utf-8")
    baked = runner.apply_env_overrides(text, {"SOME_KEY": "value"})
    header = baked.split("\n---", 1)[0]
    assert "tags: [profile]" in header
