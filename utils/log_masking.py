"""Mask what must not leave CI before a log or traceback goes to a third party.

Shared by maestro_report.py (mobile log tails) and ai_failure_analyst.py (web
tracebacks), so both suites are masked the same way.
"""

import re
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
SENSITIVE_SOURCES = (
    ROOT / "test_data" / "mobile_workers.yaml",
    ROOT / "test_data" / "web_test_data.yaml",
)
SENSITIVE_KEY_HINTS = ("phone", "backup", "code", "password", "otp", "pin")
MIN_VALUE_LEN = 4  # shorter values would mask ordinary text
MASK = "***"


def _collect(node, found):
    if isinstance(node, dict):
        for key, value in node.items():
            if isinstance(value, (dict, list)):
                _collect(value, found)
            elif value and any(hint in str(key).lower() for hint in SENSITIVE_KEY_HINTS):
                if len(str(value)) >= MIN_VALUE_LEN:
                    found.add(str(value))
    elif isinstance(node, list):
        for item in node:
            _collect(item, found)


def sensitive_values():
    """Phone numbers, backup codes and anything else keyed like a secret in the
    mobile worker and web test-data files, longest first so substrings don't leak."""
    found = set()
    for source in SENSITIVE_SOURCES:
        try:
            _collect(yaml.safe_load(source.read_text(encoding="utf-8")) or {}, found)
        except Exception:  # noqa: BLE001 - masking falls back to the generic rules
            continue
    return sorted(found, key=len, reverse=True)


def mask_sensitive(text):
    """Drop every inputText line (what was typed on the device), mask runs of 6+
    digits (OTPs, phone numbers), then mask every known sensitive value."""
    kept = [line for line in str(text).splitlines() if "inputText" not in line]
    # Digit runs first, so a full phone number is masked whole before a shorter
    # known value could replace only part of it and leave the rest behind.
    masked = re.sub(r"\d{6,}", MASK, "\n".join(kept))
    for value in sensitive_values():
        masked = masked.replace(value, MASK)
    return masked
