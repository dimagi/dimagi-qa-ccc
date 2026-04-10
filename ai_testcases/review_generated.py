#!/usr/bin/env python3
"""
AI Test Review Gate
===================
Reviews AI-generated pytest test files before they are committed.
Called by the CI workflow after generation; exits non-zero if any file fails review.

Usage:
    python ai_testcases/review_generated.py tests/web_tests/test_foo.py
    python ai_testcases/review_generated.py tests/web_tests/test_foo.py tests/mobile_tests/test_bar.py

Exit codes:
    0  — all files passed review
    1  — one or more files failed review (commit is blocked)
    2  — API key missing or openai not installed (review skipped, commit proceeds)
"""

import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[review_generated] openai not installed — skipping review, proceeding.")
    sys.exit(2)

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


REVIEW_SYSTEM_PROMPT = """\
You are a senior QA automation engineer reviewing a pytest test file generated for the
dimagi-qa-ccc project (Selenium/Appium, Page Object Model, Allure reporting).

Check the file against this checklist:
1. All four Allure decorators present on every test function:
   @allure.feature, @allure.story, @allure.tag, @allure.description
2. Every logical action is wrapped in `with allure.step("...")`
3. No invented imports — only these are allowed:
   allure, pytest, pages.*, utils.helpers, utils.utility, selenium, appium
4. Assertions present for every step that says "Verify" or "Assert"
5. No hardcoded credentials, passwords, or absolute URLs
6. The correct pytest marker is used: @pytest.mark.web or @pytest.mark.mobile

Reply with exactly one of:
  PASS
  FAIL: <short reason>

Nothing else. No preamble.
"""


def _review_file(client: OpenAI, path: Path) -> tuple[bool, str]:
    """Returns (passed, reason)."""
    code = path.read_text(encoding="utf-8")
    if len(code) > 12000:
        code = code[:12000] + "\n... [truncated]"

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=100,
        messages=[
            {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
            {"role": "user", "content": f"```python\n{code}\n```"},
        ],
    )
    verdict = response.choices[0].message.content.strip()
    passed = verdict.upper().startswith("PASS")
    reason = verdict if not passed else "OK"
    return passed, reason


def main(files: list[str]) -> int:
    api_key = _load_api_key()
    if not api_key:
        print("[review_generated] OPENAI_API_KEY not set — skipping review, proceeding.")
        return 2

    paths = [Path(f) for f in files if f.endswith(".py")]
    if not paths:
        print("[review_generated] No .py files provided — nothing to review.")
        return 0

    client = OpenAI(api_key=api_key)
    all_passed = True

    for path in paths:
        if not path.exists():
            print(f"[review_generated] SKIP (not found): {path}")
            continue

        print(f"[review_generated] Reviewing: {path.name} …")
        passed, reason = _review_file(client, path)

        if passed:
            print(f"  PASS — {path.name}")
        else:
            print(f"  FAIL — {path.name}: {reason}")
            all_passed = False

    return 0 if all_passed else 1


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ai_testcases/review_generated.py <file1.py> [file2.py ...]")
        sys.exit(0)
    sys.exit(main(sys.argv[1:]))
