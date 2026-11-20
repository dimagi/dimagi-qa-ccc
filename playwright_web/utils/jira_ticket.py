"""Print a Jira ticket's summary, parent, description and comments for the QA agent.

The agent reads untrusted PR text, so it gets this narrow command instead of curl:
it can only read the issue it names, with the credentials from the environment.

Usage (from playwright_web/):
    python -m utils.jira_ticket CCCT-2649

Needs JIRA_BASE_URL (e.g. https://dimagi.atlassian.net), JIRA_EMAIL, JIRA_API_TOKEN.
"""

import base64
import json
import os
import re
import sys
import urllib.request

FIELDS = "summary,description,comment,parent,status,issuetype"


def fetch_issue(key, base_url, email, token):
    if not re.fullmatch(r"[A-Z][A-Z0-9]+-\d+", key):
        raise ValueError(f"not a Jira issue key: {key!r}")
    # API v2 returns description and comments as plain text, not Atlassian Document Format.
    request = urllib.request.Request(f"{base_url.rstrip('/')}/rest/api/2/issue/{key}?fields={FIELDS}")
    auth = base64.b64encode(f"{email}:{token}".encode()).decode()
    request.add_header("Authorization", f"Basic {auth}")
    request.add_header("Accept", "application/json")
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def format_issue(issue):
    fields = issue["fields"]
    lines = [f"{issue['key']}: {fields.get('summary', '')}"]
    if fields.get("issuetype"):
        lines.append(f"Type: {fields['issuetype'].get('name')}")
    if fields.get("status"):
        lines.append(f"Status: {fields['status'].get('name')}")
    parent = fields.get("parent")
    if parent:
        lines.append(f"Parent: {parent['key']} {parent.get('fields', {}).get('summary', '')}")
    lines += ["", "Description:", fields.get("description") or "(none)", "", "Comments:"]
    comments = (fields.get("comment") or {}).get("comments", [])
    for comment in comments:
        lines.append(f"- {comment.get('author', {}).get('displayName', '?')} ({comment.get('created', '')[:10]}): {comment.get('body', '')}")
    if not comments:
        lines.append("(none)")
    return "\n".join(lines)


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: python -m utils.jira_ticket <ISSUE-KEY>")
    settings = [os.environ.get(name) for name in ("JIRA_BASE_URL", "JIRA_EMAIL", "JIRA_API_TOKEN")]
    if not all(settings):
        sys.exit("Jira is not configured (JIRA_BASE_URL / JIRA_EMAIL / JIRA_API_TOKEN); work from the PR alone.")
    print(format_issue(fetch_issue(sys.argv[1], *settings)))


if __name__ == "__main__":
    main()
