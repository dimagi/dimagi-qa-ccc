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
MAESTRO_LOG_TAIL_LINES = 40  # enough to see the failing step + its preceding context


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


def _maestro_auth():
    username = os.environ.get("BROWSERSTACK_USERNAME", "").strip()
    access_key = os.environ.get("BROWSERSTACK_ACCESS_KEY", "").strip()
    return (username, access_key) if username and access_key else None


def _parse_maestro_failures(report_json_path: Path) -> list[dict]:
    """Return list of {name, classname, error} for every failed Maestro flow.

    maestro_report.json (run_on_browserstack.py) only carries flow name/status,
    no error text - the actual failing-step detail lives in BrowserStack's own
    Maestro API. Pulls the tail of each failed flow's log (the same one
    map_10/map_11's staging-vs-prod investigation used manually) as the
    "traceback". Best-effort: a build/session/log lookup failing for one flow
    just means that flow's line says so, not that the whole analysis is lost."""
    import json

    import requests

    if not report_json_path.exists():
        print(f"[ai_failure_analyst] {report_json_path} not found")
        return []
    report = json.loads(report_json_path.read_text(encoding="utf-8"))
    build_id = report.get("build_id")
    failed_names = {
        f["name"]
        for s in report.get("sessions", [])
        for f in s.get("flows", [])
        if f.get("status") == "failed"
    }
    if not build_id or not failed_names:
        return []

    auth = _maestro_auth()
    if not auth:
        print("[ai_failure_analyst] BROWSERSTACK creds not set - failures reported without log detail")
        return [{"name": n, "classname": "", "error": "(no BrowserStack credentials to fetch the log)"} for n in failed_names]

    base = "https://api-cloud.browserstack.com/app-automate/maestro/v2"
    failures = []
    try:
        build = requests.get(f"{base}/builds/{build_id}", auth=auth, timeout=30).json()
        for device in build.get("devices", []):
            for session in device.get("sessions", []):
                detail = requests.get(f"{base}/builds/{build_id}/sessions/{session['id']}", auth=auth, timeout=30).json()
                for group in detail.get("testcases", {}).get("data", []):
                    for tc in group.get("testcases", []):
                        if tc.get("name") not in failed_names or tc.get("status") != "failed":
                            continue
                        error = "(log unavailable)"
                        log_url = tc.get("maestro_log")
                        if log_url:
                            try:
                                log_text = requests.get(log_url, auth=auth, timeout=30).text
                                error = "\n".join(log_text.strip().splitlines()[-MAESTRO_LOG_TAIL_LINES:])
                            except Exception as exc:  # noqa: BLE001
                                error = f"(log fetch failed: {exc})"
                        failures.append({"name": tc["name"], "classname": "", "error": error})
    except Exception as exc:  # noqa: BLE001
        print(f"[ai_failure_analyst] BrowserStack API lookup failed: {exc}")
        return [{"name": n, "classname": "", "error": f"(BrowserStack lookup failed: {exc})"} for n in failed_names]

    # Any failed flow the API lookup didn't match still gets reported, just without detail.
    found = {f["name"] for f in failures}
    for name in failed_names - found:
        failures.append({"name": name, "classname": "", "error": "(no matching BrowserStack session testcase found)"})
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


def _render_report(failures: list[dict], scope: str, client: OpenAI) -> str:
    """Shared by analyse()/analyse_maestro(): failures -> compact report text,
    writing ai_failure_report.md for the legacy dimagi_pytest.yaml workflow's
    artifact/PR-comment flow along the way (manual-dispatch only, but
    functional - keep it working rather than assume it's dead)."""
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
    (PROJECT_ROOT / "ai_failure_report.md").write_text(report_text, encoding="utf-8")
    return report_text


def analyse(xml_path: str, scope_label: str | None = None) -> str:
    """Web suite: run analysis on a JUnit XML report, print + return a compact
    glance-friendly report (empty string if nothing to report or no API key)."""
    api_key = _load_api_key()
    if not api_key:
        print("[ai_failure_analyst] OPENAI_API_KEY not set - skipping analysis.")
        return ""

    path = Path(xml_path)
    failures = _parse_failures(path)
    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} - nothing to analyse.")
        return ""

    return _render_report(failures, scope_label or path.stem, OpenAI(api_key=api_key))


def analyse_maestro(report_json_path: str, scope_label: str | None = None) -> str:
    """Mobile suite: run analysis on a maestro_report.json (+ BrowserStack logs
    for detail), print + return a compact glance-friendly report (empty string
    if nothing to report or no API key)."""
    api_key = _load_api_key()
    if not api_key:
        print("[ai_failure_analyst] OPENAI_API_KEY not set - skipping analysis.")
        return ""

    path = Path(report_json_path)
    failures = _parse_maestro_failures(path)
    if not failures:
        print(f"[ai_failure_analyst] No failures in {path.name} - nothing to analyse.")
        return ""

    return _render_report(failures, scope_label or path.stem, OpenAI(api_key=api_key))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python utils/ai_failure_analyst.py <path/to/junit.xml|maestro_report.json> [scope_label]")
        sys.exit(1)

    _path, _label = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else None)
    if _path.endswith(".json"):
        analyse_maestro(_path, _label)
    else:
        analyse(_path, _label)
