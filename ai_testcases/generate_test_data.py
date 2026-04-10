#!/usr/bin/env python3
"""
AI Test Data Generator
======================
Generates YAML test data entries from a plain-English scenario description.

Usage:
    # Print generated YAML to stdout:
    python ai_testcases/generate_test_data.py "Payment for 3 workers, budget USD 500, 30 days"

    # Append directly to a YAML file:
    python ai_testcases/generate_test_data.py "Opportunity with learning module" --append test_data/web_test_data.yaml

    # Specify the test ID prefix (default: auto-detected):
    python ai_testcases/generate_test_data.py "Worker signup flow" --id TC_11

Requirements:
    OPENAI_API_KEY set in environment or settings.cfg
"""

import argparse
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("[ERROR] The 'openai' package is not installed. Run: pip install openai")
    sys.exit(1)

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


# --------------------------------------------------------------------------
# Existing schema examples — injected into the prompt so the model produces
# entries that match the real YAML structure exactly.
# --------------------------------------------------------------------------
WEB_SCHEMA_EXAMPLE = """\
OLP_1:
  opportunity_name: "Automation Opportunity March"
  currency: "USD (US Dollar)"
  passing_score: "80"
  budget: "500"
  max_visits_per_user: "10"
  end_date: "05-10-2026"
  org_name: "PM_Automation_01"
  domain: "connectqa"

PAYMENT_1:
  worker_username: "worker_connect_1"
  payment_amount: "100"
  payment_unit: "Visit"
  approval_status: "Approved"
"""

MOBILE_SCHEMA_EXAMPLE = """\
TC_1:
  country_code: "+91"
  phone_number: "9876543210"
  username: "connect_worker_tc1"
  backup_code: "123456"
  opportunity_name: "Field Visit Opportunity"
  org_name: "PM_Automation_01"
"""

SYSTEM_PROMPT = """\
You are a senior QA automation engineer for the dimagi-qa-ccc project
(CommCare Connect — Selenium/Appium pytest framework).

Your job is to generate realistic YAML test data entries based on a plain-English scenario.

Rules:
1. Output ONLY valid YAML — no markdown fences, no prose, no explanation.
2. Match the exact field names and value formats shown in the schema examples.
3. Use realistic-looking but obviously fake values (no real phone numbers, no real API keys).
4. Use the test ID provided; if none is given, use the next logical ID based on the schema.
5. Dates must be in MM-DD-YYYY format and set at least 7 days in the future from today.
6. Budget and score values must be numeric strings (e.g. "500", "80").
7. Generate only the fields relevant to the described scenario — do not invent extra fields.
"""


def _next_id_from_file(yaml_path: Path, prefix: str) -> str:
    """Scan yaml_path for existing IDs with the given prefix and return the next one."""
    if not yaml_path.exists():
        return f"{prefix}_1"
    import re
    content = yaml_path.read_text(encoding="utf-8")
    matches = re.findall(rf"^{re.escape(prefix)}_(\d+)\s*:", content, re.MULTILINE)
    if not matches:
        return f"{prefix}_1"
    max_num = max(int(m) for m in matches)
    return f"{prefix}_{max_num + 1}"


def generate(description: str, test_id: str | None, append_to: Path | None) -> str:
    api_key = _load_api_key()
    if not api_key:
        print("[ERROR] OPENAI_API_KEY not found. Set it in environment or settings.cfg.")
        sys.exit(1)

    # Determine schema type from description keywords
    is_mobile = any(w in description.lower() for w in
                    ("mobile", "phone", "app", "signup", "tc_", "worker login"))
    schema = MOBILE_SCHEMA_EXAMPLE if is_mobile else WEB_SCHEMA_EXAMPLE
    data_file = "test_data/mobile_workers.yaml" if is_mobile else "test_data/web_test_data.yaml"

    # Auto-detect next ID if not provided
    if not test_id:
        prefix = "TC" if is_mobile else "OLP"
        if append_to:
            test_id = _next_id_from_file(append_to, prefix)
        else:
            test_id = f"{prefix}_NEW"

    user_message = (
        f"Generate a YAML test data entry for this scenario:\n{description}\n\n"
        f"Use test ID: {test_id}\n"
        f"Target file: {data_file}\n\n"
        f"Schema to follow:\n{schema}"
    )

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=400,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )

    yaml_block = response.choices[0].message.content.strip()

    # Strip accidental markdown fences
    if yaml_block.startswith("```"):
        lines = yaml_block.splitlines()
        yaml_block = "\n".join(lines[1:-1]).strip()

    return yaml_block


def main():
    parser = argparse.ArgumentParser(
        description="Generate YAML test data entries from a plain-English scenario."
    )
    parser.add_argument(
        "description",
        help="Plain-English description of the test scenario."
    )
    parser.add_argument(
        "--id",
        dest="test_id",
        default=None,
        help="Test data ID to use (e.g. OLP_12, TC_11). Auto-detected if omitted."
    )
    parser.add_argument(
        "--append",
        dest="append_to",
        default=None,
        help="YAML file to append the generated entry to."
    )
    args = parser.parse_args()

    append_path = Path(args.append_to) if args.append_to else None
    if append_path and not append_path.is_absolute():
        append_path = PROJECT_ROOT / append_path

    yaml_output = generate(args.description, args.test_id, append_path)

    if append_path:
        with open(append_path, "a", encoding="utf-8") as f:
            f.write("\n" + yaml_output + "\n")
        print(f"[OK] Appended to {append_path}")
        print(yaml_output)
    else:
        print(yaml_output)


if __name__ == "__main__":
    main()
