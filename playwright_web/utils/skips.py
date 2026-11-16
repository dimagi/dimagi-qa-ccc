"""Labelled skips.

A bare pytest.skip says nothing about whether the skip is expected. Every skip
in the web suite goes through one of these so the run summary can bucket it:

- skip_not_applicable: the test does not apply on this environment by design
  (e.g. invoice mutations on prod, staging-only fixtures). Expected, not a gap.
- skip_needs_data: the test could run but the fixture, config or live state it
  needs is missing. This is a coverage gap with a next step (seed or point at data).
- skip_blocked: the test could not run because something upstream failed or
  looks broken (an earlier test failed, an endpoint errors, a control is missing).
  This may be a real product defect hiding as a skip, so it is reported on its
  own and needs investigation - never read it as harmless.

Messaging on staging keeps its own [MESSAGING-EXCLUDED] tag (CCCT-2671).
"""
from typing import NoReturn

import pytest

NOT_APPLICABLE_TAG = "[NOT-APPLICABLE]"
NEEDS_DATA_TAG = "[NEEDS-DATA]"
BLOCKED_TAG = "[BLOCKED]"

# Bucket names used by classify() and the CI summary.
NOT_APPLICABLE = "not_applicable"
NEEDS_DATA = "needs_data"
BLOCKED = "blocked"
UNLABELLED = "unlabelled"


def skip_not_applicable(reason: str) -> NoReturn:
    """Skip: this test does not apply on this environment by design."""
    __tracebackhide__ = True
    pytest.skip(f"{NOT_APPLICABLE_TAG} {reason}")


def skip_needs_data(reason: str) -> NoReturn:
    """Skip: the fixture, config or live state this test needs is missing."""
    __tracebackhide__ = True
    pytest.skip(f"{NEEDS_DATA_TAG} {reason}")


def skip_blocked(reason: str) -> NoReturn:
    """Skip: something upstream failed or looks broken; investigate, it may be a defect."""
    __tracebackhide__ = True
    pytest.skip(f"{BLOCKED_TAG} {reason}")


def classify(reason: str) -> str:
    """Bucket a skip reason by its tag; no known tag means UNLABELLED.

    BLOCKED wins if several tags appear, so a possible defect is never downgraded."""
    for tag, bucket in (
        (BLOCKED_TAG, BLOCKED),
        (NOT_APPLICABLE_TAG, NOT_APPLICABLE),
        (NEEDS_DATA_TAG, NEEDS_DATA),
    ):
        if tag in reason:
            return bucket
    return UNLABELLED
