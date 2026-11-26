import pytest

from utils import jira_ticket

ISSUE = {
    "key": "CCCT-2649",
    "fields": {
        "summary": "Clear Work Areas",
        "issuetype": {"name": "Story"},
        "status": {"name": "Done"},
        "parent": {"key": "CCCT-2600", "fields": {"summary": "Microplanning v2"}},
        "description": "Add a button to clear work areas.",
        "comment": {"comments": [{"author": {"displayName": "Dev"}, "created": "2026-07-01T10:00:00", "body": "Also clear groups."}]},
    },
}


def test_format_issue_includes_parent_description_and_comments():
    text = jira_ticket.format_issue(ISSUE)
    assert text.startswith("CCCT-2649: Clear Work Areas")
    assert "Parent: CCCT-2600 Microplanning v2" in text
    assert "Add a button to clear work areas." in text
    assert "- Dev (2026-07-01): Also clear groups." in text


def test_format_issue_without_description_or_comments():
    issue = {"key": "CCCT-1", "fields": {"summary": "x", "description": None, "comment": {"comments": []}}}
    text = jira_ticket.format_issue(issue)
    assert "Description:\n(none)" in text and "Comments:\n(none)" in text


@pytest.mark.parametrize("key", ["ccct-1", "CCCT-12/../x", "CCCT", "../CCCT-1"])
def test_fetch_issue_rejects_anything_but_an_issue_key(key):
    with pytest.raises(ValueError, match="not a Jira issue key"):
        jira_ticket.fetch_issue(key, "https://example.atlassian.net", "e", "t")
