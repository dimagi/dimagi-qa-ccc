#!/usr/bin/env python3
"""
AI Failure Analyst
==================
Parses a JUnit XML report, sends each failing test's traceback to OpenAI,
and writes a plain-English diagnosis to ai_failure_report.md.

Usage (called automatically by CI after tests run):
    python utils/ai_failure_analyst.py reports/web-stage.xml
    python utils/ai_failure_analyst.py reports/mobile-prod.xml

Output:
    ai_failure_report.md   — uploaded as a CI artifact and printed to console
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ai_failure_analyst] openai not installed — skipping analysis.")
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_api_key() -> str:
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    cfg = PROJECT_ROOT / "settings.cfg"
    if cfg.exists():
        for line in cfg.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("OPENAI_API_KEY"):
                _, _, value = line.partition("=")
                value = value.strip()
                if value:
                    return value
    return ""


def _parse_failures(xml_path: Path) -> list[dict]:
    """Return list of {name, classname, error} for every failed/errored test."""
    if not xml_path.exists():
        print(f"[ai_failure_analyst] XML not found: {xml_path}")
        return []

    tree = ET.parse(xml_path)
    failures = []
    for tc in tree.iter("testcase"):
        for tag in ("failure", "error"):
            node = tc.find(tag)
            if node is not None:
                failures.append({
                    "name":      tc.attrib.get("name", "unknown"),
                    "classname": tc.attrib.get("classname", ""),
                    "error":     (node.text or node.attrib.get("message", ""))[:3000],
                    "tag":       tag,
                })
                break
    return failures


SYSTEM_PROMPT = """\
You are a senior QA automation engineer reviewing a Selenium/Appium pytest failure.
The project uses Python, Selenium 4, Appium, Page Object Model, YAML locators.

For each failure, provide a structured diagnosis in exactly this format:

**Root Cause:** One sentence describing what went wrong technically.
**Flaky or Real Bug:** State "Likely flaky" or "Likely real bug" and why in one sentence.
**Fix:** One concrete, actionable suggestion (e.g. "Add an explicit wait for X", "Update locator for Y element").

Be concise. No preamble. No markdown headers beyond the three bold labels above.
"""


def _analyse_failure(client: OpenAI, name: str, error: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=300,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content":
                f"Test: `{name}`\n\nTraceback:\n```\n{error}\n```"
            },
        ],
    )
    return response.choices[0].message.content.strip()


def analyse(xml_path: str) -> int:
    """Run analysis on xml_path. Returns number of failures found."""
    api_key = _load_api_key()
    if not api_key:
        print("[ai_failure_analyst] OPENAI_API_KEY not set — skipping analysis.")
        return 0

    path = Path(xml_path)
    failures = _parse_failures(path)

    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} — nothing to analyse.")
        return 0

    client = OpenAI(api_key=api_key)
    scope = path.stem  # e.g. "web-stage"

    report_lines = [
        f"# AI Failure Analysis — `{scope}`\n",
        f"**{len(failures)} failure(s) detected**\n",
        "---\n",
    ]

    for i, f in enumerate(failures, 1):
        print(f"\n[ai_failure_analyst] Analysing ({i}/{len(failures)}): {f['name']} ...")
        diagnosis = _analyse_failure(client, f["name"], f["error"])

        block = (
            f"## {i}. `{f['name']}`\n"
            f"> Class: `{f['classname']}`  |  Type: `{f['tag']}`\n\n"
            f"{diagnosis}\n\n"
            "---\n"
        )
        report_lines.append(block)
        print(diagnosis)

    report_text = "\n".join(report_lines)
    report_path = PROJECT_ROOT / "ai_failure_report.md"
    report_path.write_text(report_text, encoding="utf-8")
    print(f"\n[ai_failure_analyst] Report written -> {report_path}")
    return len(failures)


def post_to_slack(webhook_url: str, scope: str, env: str):
    """Post the AI failure report to Slack as a threaded comment."""
    import json
    import urllib.request

    report_path = PROJECT_ROOT / "ai_failure_report.md"
    if not report_path.exists():
        print("[ai_failure_analyst] No report file found - nothing to post to Slack.")
        return

    content = report_path.read_text(encoding="utf-8").strip()
    if not content or "No failures" in content:
        return

    # Slack text limit per attachment is ~3000 chars
    if len(content) > 2800:
        content = content[:2800] + "\n... [truncated - see full report artifact]"

    payload = {
        "attachments": [
            {
                "color": "danger",
                "title": f":robot_face: AI Failure Analysis — {scope.upper()} ({env.upper()})",
                "text": content,
                "footer": "ai_failure_analyst | gpt-4o-mini",
                "mrkdwn_in": ["text"],
            }
        ]
    }

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        print("[ai_failure_analyst] Slack notification sent.")
    except Exception as e:
        print(f"[ai_failure_analyst] Slack post failed (non-fatal): {e}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/ai_failure_analyst.py <path/to/junit.xml>")
        sys.exit(1)

    xml_file = sys.argv[1]
    count = analyse(xml_file)

    if count > 0:
        webhook = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
        if webhook:
            # Infer scope and env from filename (e.g. "reports/web-stage.xml")
            stem = Path(xml_file).stem          # "web-stage"
            parts = stem.split("-", 1)
            scope = parts[0] if len(parts) > 0 else "unknown"
            env   = parts[1] if len(parts) > 1 else "unknown"
            post_to_slack(webhook, scope, env)
        else:
            print("[ai_failure_analyst] SLACK_WEBHOOK_URL not set - skipping Slack post.")
