"""Labelled skips.

A bare pytest.skip says nothing about whether the skip is expected. Every skip
in the web suite goes through one of these so the run summary can bucket it:

- skip_not_applicable: the test does not apply on this environment by design
  (e.g. invoice mutations on prod, staging-only fixtures). Expected, not a gap.
- skip_needs_data: the test could run but the fixture, config or live state it
  needs is missing. This is a coverage gap with a next step (seed or point at data).

Messaging on staging keeps its own [MESSAGING-EXCLUDED] tag (CCCT-2671).
"""
import pytest

NOT_APPLICABLE_TAG = "[NOT-APPLICABLE]"
NEEDS_DATA_TAG = "[NEEDS-DATA]"


def skip_not_applicable(reason):
    pytest.skip(f"{NOT_APPLICABLE_TAG} {reason}")


def skip_needs_data(reason):
    pytest.skip(f"{NEEDS_DATA_TAG} {reason}")
