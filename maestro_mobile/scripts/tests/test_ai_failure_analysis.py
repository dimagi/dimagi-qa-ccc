"""Unit tests for the AI failure analysis helpers that decide what is masked before
a log or traceback leaves CI, and which failures are labelled as known issues.

No OpenAI call is made - only the pure functions are covered.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import log_masking  # noqa: E402
from log_masking import MASK, mask_sensitive  # noqa: E402

from utils.ai_failure_analyst import _known_issue_for, _normalise_name  # noqa: E402

KNOWN = [{"id": "CCCT-1", "match": ["messaging_consent", "test_consent_gates_message_delivery"]}]


def test_mask_sensitive_drops_inputtext_lines():
    out = mask_sensitive("tap Next\ninputText: hunter22\ntap Done")
    assert "hunter22" not in out and "inputText" not in out
    assert "tap Next" in out and "tap Done" in out


def test_mask_sensitive_masks_long_digit_runs_but_not_short_ones():
    out = mask_sensitive("OTP 482913 sent to +919000123456, retry in 30s")
    assert "482913" not in out and "919000123456" not in out
    assert "30s" in out


def test_mask_sensitive_masks_values_from_the_test_data_files(monkeypatch):
    monkeypatch.setattr(log_masking, "sensitive_values", lambda: ["qa.user@example.org"])
    assert mask_sensitive("login qa.user@example.org failed") == f"login {MASK} failed"


def test_collect_masks_email_keys():
    found = set()
    log_masking._collect({"valid_email": "qa.user@example.org", "title": "Welcome"}, found)
    assert found == {"qa.user@example.org"}


def test_normalise_name_strips_extension_param_and_case():
    assert _normalise_name("Messaging_Consent.yaml") == "messaging_consent"
    assert _normalise_name("test_x[chromium]") == "test_x"


def test_known_issue_matches_exact_names_only():
    assert _known_issue_for({"name": "messaging_consent"}, KNOWN)["id"] == "CCCT-1"
    assert _known_issue_for({"name": "messaging_consent.yaml"}, KNOWN)["id"] == "CCCT-1"
    assert _known_issue_for({"name": "test_consent_gates_message_delivery[chromium]"}, KNOWN)
    # a longer name that merely starts with a listed one is NOT known
    assert _known_issue_for({"name": "messaging_consent_history"}, KNOWN) is None
    assert _known_issue_for({"name": "test_consent_gates_message_delivery_extra"}, KNOWN) is None
