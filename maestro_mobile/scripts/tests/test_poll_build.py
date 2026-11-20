"""Unit tests for polling a BrowserStack build through status-endpoint errors."""

import sys
from pathlib import Path

import pytest
import requests

# run_on_browserstack imports its sibling apk_check by bare name, as when run as a script.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_on_browserstack as runner  # noqa: E402


class _Response:
    def __init__(self, status_code, data=None):
        self.status_code, self._data = status_code, data or {}

    def json(self):
        return self._data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(str(self.status_code))


@pytest.fixture
def replies(monkeypatch):
    """Queue status-endpoint replies (a _Response or an exception to raise)."""
    queue = []

    def fake_get(*_args, **_kwargs):
        reply = queue.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(runner.requests, "get", fake_get)
    monkeypatch.setattr(runner.time, "sleep", lambda _seconds: None)
    return queue


def test_polls_through_5xx_and_timeouts_until_the_build_finishes(replies):
    replies += [
        _Response(504),
        requests.Timeout("slow"),
        _Response(200, {"status": "running"}),
        _Response(502),
        _Response(200, {"status": "passed"}),
    ]
    assert runner.poll_build(None, "build1")["status"] == "passed"
    assert not replies


def test_gives_up_after_too_many_errors_in_a_row(replies, monkeypatch):
    monkeypatch.setattr(runner, "MAX_STATUS_ERRORS", 3)
    replies += [_Response(503), requests.ConnectionError("down"), _Response(504), _Response(200, {"status": "passed"})]
    with pytest.raises(RuntimeError, match="3 times in a row"):
        runner.poll_build(None, "build1")


def test_a_good_answer_resets_the_error_count(replies, monkeypatch):
    monkeypatch.setattr(runner, "MAX_STATUS_ERRORS", 3)
    replies += [
        _Response(503),
        _Response(503),
        _Response(200, {"status": "running"}),
        _Response(503),
        _Response(503),
        _Response(200, {"status": "failed"}),
    ]
    assert runner.poll_build(None, "build1")["status"] == "failed"


def test_client_errors_still_fail_straight_away(replies):
    replies += [_Response(401)]
    with pytest.raises(requests.HTTPError):
        runner.poll_build(None, "build1")
