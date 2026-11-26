#!/usr/bin/env python3
"""
AI Failure Analyst
==================
Reads a web suite's JUnit XML or a mobile suite's maestro_report.json, and
asks OpenAI for a short, glance-friendly diagnosis of each failing test - one
line each, not a multi-paragraph report. Meant to be read in a Slack thread in
a few seconds, not a full write-up.

Usage:
    python utils/ai_failure_analyst.py reports/playwright-web-stage.xml
    python utils/ai_failure_analyst.py maestro_report.json

Printing to stdout is the primary interface (CI captures it for Slack);
analyse()/analyse_maestro() also return the compact text for in-process use.
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "maestro_mobile" / "scripts"))
from log_masking import mask_sensitive  # noqa: E402

try:
    from openai import OpenAI
except ImportError:  # a missing optional dependency must not end the importing script
    OpenAI = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWN_ISSUES_FILE = PROJECT_ROOT / "test_data" / "known_issues.yaml"
AI_DISCLAIMER = "AI-generated, unverified - treat as a hint, not a diagnosis."

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


ERROR_BUDGET = 3500  # characters of error text sent per failure
_RETRY_NOISE = re.compile(r"^(E\s+)?\s*(-\s*)?(\d+\s*[x\u00d7]\s*)?(waiting for element to be visible|retrying click action|waiting \d+ms)", re.I)


def _condense_error(text: str, budget: int = ERROR_BUDGET) -> str:
    """Shrink a Playwright/pytest error without losing the evidence a diagnosis needs.

    Playwright's call log repeats "waiting for element to be visible ... retrying"
    dozens of times; cutting the text at N characters kept that noise and dropped
    the lines that matter (what the locator resolved to, and why the click failed).
    Collapse the repeated retry lines into a count, keep the head and the tail."""
    kept, noise = [], 0
    for line in text.splitlines():
        if _RETRY_NOISE.match(line):
            noise += 1
        else:
            kept.append(line)
    if noise:
        kept.append(f"(+{noise} repeated retry/wait lines omitted - the element stayed in this state)")
    out = "\n".join(kept)
    if len(out) <= budget:
        return out
    head = budget // 2
    return out[:head] + "\n...[truncated]...\n" + out[-(budget - head):]


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
                    "error":     _condense_error(mask_sensitive(node.text or node.attrib.get("message", ""))),
                    "tag":       tag,
                })
                break
    return failures


def _parse_maestro_failures(report_json_path: Path) -> list[dict]:
    """Return list of {name, classname, error} for every failed Maestro flow.

    The "traceback" is the masked log tail run_on_browserstack/maestro_report keep
    in maestro_report.json (`log_tail`), so no BrowserStack call or credentials are
    needed here."""
    if not report_json_path.exists():
        print(f"[ai_failure_analyst] {report_json_path} not found")
        return []
    report = json.loads(report_json_path.read_text(encoding="utf-8"))
    return [
        {"name": f["name"], "classname": "", "error": _condense_error(f.get("log_tail") or "(no log captured)")}
        for s in report.get("sessions", [])
        for f in s.get("flows", [])
        if f.get("status") not in ("passed", "skipped", None)
    ]


def _dedupe(failures: list[dict]) -> list[dict]:
    """One entry per test name - a test can appear twice in one run (e.g. two JUnit
    entries for a rerun), which would waste a slot and print two lines."""
    seen, unique = set(), []
    for f in failures:
        if f["name"] in seen:
            continue
        seen.add(f["name"])
        unique.append(f)
    return unique


def _load_known_issues() -> list[dict]:
    try:
        return yaml.safe_load(KNOWN_ISSUES_FILE.read_text(encoding="utf-8")) or []
    except Exception:  # noqa: BLE001 - no file/unreadable: just no known issues
        return []


def _normalise_name(name: str) -> str:
    """Strip the ".yaml" extension and a trailing "[param]" suffix, lower-cased."""
    name = re.sub(r"\[.*\]$", "", str(name).strip())
    return re.sub(r"\.ya?ml$", "", name).strip().lower()


def _known_issue_for(failure: dict, known_issues: list[dict]):
    # Exact match on the normalised test/flow name, so "messaging_consent" does not
    # also swallow "messaging_consent_history".
    name = _normalise_name(failure["name"])
    for issue in known_issues:
        if any(_normalise_name(m) == name for m in issue.get("match", [])):
            return issue
    return None


SYSTEM_PROMPT = """\
You are a senior QA automation engineer triaging CI failures for a Playwright \
(Python, Page Object Model, YAML locators) and Maestro (mobile YAML flows) test \
suite testing a Django web app (CommCare Connect).

Reply with EXACTLY ONE LINE, no markdown, no preamble, in this exact shape:
<Flaky|Test bug|Product bug|Env|Unclear> — <root cause in <=20 words> — Evidence: "<short quote from the log>" — Fix: <concrete action in <=12 words>

"Flaky" = timing/race/staging-availability: the element or state DID appear on some \
tries, or the log shows a slow response. Nothing to fix in code.
"Test bug" = a defect in the TEST code (bad/ambiguous locator, wrong assertion or logic) \
- fix is in this repo.
"Product bug" = the app behaved wrongly and the test is right - fix is a product ticket, \
NOT a test change.
"Env" = external dependency/data/environment issue (seed data, staging outage, \
expired real-clock state) - not fixable by changing code.
"Unclear" = the log does not show enough to choose; say what to look at.

Rules:
- Base the label on the log, and quote the line that supports it in Evidence.
- If a locator "resolved to" an element and every retry says it is "not visible" for \
the whole timeout, that is a Test bug (the locator picked the wrong or hidden element), \
NOT Flaky. A longer timeout will not help; never suggest one for that pattern.
- Only suggest a longer wait when the log shows the element did become ready or a \
response was merely slow.
- A Maestro/BrowserStack failure that only says a flow "did not pass" gives no cause: \
answer Unclear and name the flow's build to open, do NOT label it a Product bug.
- Never pair "Flaky" with a code-change fix.
- If unsure between Test bug and Product bug, answer Unclear rather than guessing.
Be terse. One line only.
"""


def _analyse_failure(client, name: str, error: str) -> str:
    response = client.chat.completions.create(
        model=os.environ.get("AI_ANALYST_MODEL", "gpt-4o"),
        max_tokens=160,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Test: `{name}`\n\nTraceback:\n```\n{error}\n```"},
        ],
    )
    return response.choices[0].message.content.strip().replace("\n", " ")


def _render_report(failures: list[dict], scope: str, client) -> str:
    """Shared by analyse()/analyse_maestro(): failures -> compact report text,
    writing ai_failure_report.md (uploaded as a workflow artifact) along the way."""
    failures = _dedupe(failures)
    known_issues = _load_known_issues()
    shown, overflow = failures[:MAX_FAILURES], failures[MAX_FAILURES:]

    lines = [f"\U0001f916 AI Failure Analysis — {scope}", f"_{AI_DISCLAIMER}_"]
    for f in shown:
        issue = _known_issue_for(f, known_issues)
        if issue:
            diagnosis = (
                f"Known issue ({issue['id']}) — {issue['summary']} — Fix: none in tests; "
                "check it's the same failure"
            )
        else:
            print(f"[ai_failure_analyst] Analysing: {f['name']} ...")
            try:
                diagnosis = _analyse_failure(client, f["name"], f["error"])
            except Exception as exc:  # noqa: BLE001 - best-effort, never break CI over this
                diagnosis = f"Env — analysis unavailable ({exc.__class__.__name__}) — Fix: check manually"
        line = f"• `{f['name']}`: {diagnosis}"
        lines.append(line)
        print(line)
    if overflow:
        lines.append(f"...and {len(overflow)} more failure(s) not analysed - see the run's test report.")

    report_text = "\n".join(lines)
    print(f"\n{report_text}")
    (PROJECT_ROOT / "ai_failure_report.md").write_text(report_text, encoding="utf-8")
    return report_text


def _client_or_none():
    """An OpenAI client, or None (with the reason printed) if analysis can't run."""
    if OpenAI is None:
        print("[ai_failure_analyst] openai not installed - skipping analysis.")
        return None
    api_key = _load_api_key()
    if not api_key:
        print("[ai_failure_analyst] OPENAI_API_KEY not set - skipping analysis.")
        return None
    return OpenAI(api_key=api_key)


def analyse(xml_path: str, scope_label: str | None = None) -> str:
    """Web suite: run analysis on a JUnit XML report, print + return a compact
    glance-friendly report (empty string if nothing to report or analysis can't run)."""
    client = _client_or_none()
    if client is None:
        return ""

    path = Path(xml_path)
    failures = _parse_failures(path)
    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} - nothing to analyse.")
        return ""

    return _render_report(failures, scope_label or path.stem, client)


def analyse_maestro(report_json_path: str, scope_label: str | None = None) -> str:
    """Mobile suite: run analysis on a maestro_report.json (its masked `log_tail`
    per failed flow), print + return a compact glance-friendly report (empty string
    if nothing to report or analysis can't run)."""
    client = _client_or_none()
    if client is None:
        return ""

    path = Path(report_json_path)
    failures = _parse_maestro_failures(path)
    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} - nothing to analyse.")
        return ""

    return _render_report(failures, scope_label or path.stem, client)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/ai_failure_analyst.py <path/to/junit.xml|maestro_report.json> [scope_label]")
        sys.exit(1)

    _path, _label = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if _path.endswith(".json"):
        analyse_maestro(_path, _label)
    else:
        analyse(_path, _label)
