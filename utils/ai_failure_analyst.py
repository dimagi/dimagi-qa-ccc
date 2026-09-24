#!/usr/bin/env python3
"""
AI Failure Analyst
==================
Parses a JUnit XML report and asks OpenAI for a short, glance-friendly
diagnosis of each failing test - one line each, not a multi-paragraph report.
Meant to be read in a Slack thread in a few seconds, not a full write-up.

Usage:
    python utils/ai_failure_analyst.py reports/playwright-web-stage.xml
    python utils/ai_failure_analyst.py reports/maestro-mobile-report-stage.xml

Printing to stdout is the primary interface (CI captures it for Slack);
analyse() also returns the compact text for direct in-process use.
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ai_failure_analyst] openai not installed - skipping analysis.")
    sys.exit(0)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MAX_FAILURES = 8  # cap the OpenAI calls + keep the Slack message short


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
    """Return list of {name, classname, error} for every failed/errored test.
    Skipped tests are deliberately excluded - they're not failures."""
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
                    "error":     (node.text or node.attrib.get("message", ""))[:2000],
                    "tag":       tag,
                })
                break
    return failures


SYSTEM_PROMPT = """\
You are a senior QA automation engineer triaging CI failures for a Playwright \
(Python, Page Object Model, YAML locators) and Maestro (mobile YAML flows) test \
suite testing a Django web app (CommCare Connect).

Reply with EXACTLY ONE LINE, no markdown, no preamble, in this exact shape:
<Flaky|Bug|Env> — <root cause in <=12 words> — Fix: <concrete action in <=10 words>

"Flaky" = timing/race/staging-availability, nothing to fix in test or product code.
"Bug" = a real defect in the test code (bad locator/logic) or the product.
"Env" = external dependency/data/environment issue (seed data, staging outage, \
expired real-clock state) - not fixable by changing code.

Be terse. One line only.
"""


def _analyse_failure(client: OpenAI, name: str, error: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=60,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Test: `{name}`\n\nTraceback:\n```\n{error}\n```"},
        ],
    )
    return response.choices[0].message.content.strip().replace("\n", " ")


def analyse(xml_path: str, scope_label: str | None = None) -> str:
    """Run analysis on xml_path, print + return a compact glance-friendly
    report (empty string if there's nothing to report or no API key)."""
    api_key = _load_api_key()
    if not api_key:
        print("[ai_failure_analyst] OPENAI_API_KEY not set - skipping analysis.")
        return ""

    path = Path(xml_path)
    failures = _parse_failures(path)
    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} - nothing to analyse.")
        return ""

    client = OpenAI(api_key=api_key)
    scope = scope_label or path.stem
    shown, overflow = failures[:MAX_FAILURES], failures[MAX_FAILURES:]

    lines = [f"\U0001f916 AI Failure Analysis — {scope}"]
    for f in shown:
        print(f"[ai_failure_analyst] Analysing: {f['name']} ...")
        try:
            diagnosis = _analyse_failure(client, f["name"], f["error"])
        except Exception as exc:  # noqa: BLE001 - best-effort, never break CI over this
            diagnosis = f"Env — analysis unavailable ({exc.__class__.__name__}) — Fix: check manually"
        line = f"• `{f['name']}`: {diagnosis}"
        lines.append(line)
        print(line)
    if overflow:
        lines.append(f"...and {len(overflow)} more failure(s), see the full report.")

    report_text = "\n".join(lines)
    print(f"\n{report_text}")

    # Also write the file the legacy dimagi_pytest.yaml workflow's "Upload AI
    # Failure Report" step still expects (manual-dispatch only, but functional -
    # keep it working rather than assume it's dead).
    (PROJECT_ROOT / "ai_failure_report.md").write_text(report_text, encoding="utf-8")

    return report_text


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/ai_failure_analyst.py <path/to/junit.xml> [scope_label]")
        sys.exit(1)

    analyse(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
