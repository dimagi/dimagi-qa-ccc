import signal

import pytest

import flows.mobile_runner  # noqa: F401 - puts maestro_mobile/scripts on the path
import run_on_browserstack as bs


@pytest.fixture
def stops(monkeypatch):
    calls = []
    monkeypatch.setattr(bs, "stop_build", lambda auth, build_id: calls.append(build_id))
    return calls


def test_exception_while_build_running_stops_it(stops):
    with pytest.raises(RuntimeError):
        with bs.stop_build_on_abort(auth=None) as running:
            running["build_id"] = "b1"
            raise RuntimeError("poll failed")
    assert stops == ["b1"]


def test_signal_while_build_running_stops_it(stops):
    with pytest.raises(KeyboardInterrupt):
        with bs.stop_build_on_abort(auth=None) as running:
            running["build_id"] = "b1"
            signal.raise_signal(signal.SIGINT)
    assert stops == ["b1"]


def test_sigterm_handler_unwinds_instead_of_killing():
    with bs.stop_build_on_abort(auth=None):
        handler = signal.getsignal(signal.SIGTERM)
    with pytest.raises(KeyboardInterrupt):
        handler(signal.SIGTERM, None)


def test_finished_build_is_not_stopped(stops):
    with pytest.raises(RuntimeError):
        with bs.stop_build_on_abort(auth=None) as running:
            running["build_id"] = "b1"
            running["build_id"] = None  # poll returned
            raise RuntimeError("later failure")
    assert stops == []


def test_clean_exit_stops_nothing_and_restores_handlers(stops):
    before = {sig: signal.getsignal(sig) for sig in (signal.SIGINT, signal.SIGTERM)}
    with bs.stop_build_on_abort(auth=None) as running:
        running["build_id"] = "b1"
        running["build_id"] = None
    assert stops == []
    assert {sig: signal.getsignal(sig) for sig in before} == before


def test_stop_build_never_raises(monkeypatch):
    def boom(*args, **kwargs):
        raise ConnectionError("network down")

    monkeypatch.setattr(bs.requests, "post", boom)
    bs.stop_build(auth=None, build_id="b1")  # must not raise


def test_stop_build_uses_unversioned_endpoint(monkeypatch):
    seen = {}

    class Response:
        status_code = 200
        text = '{"message":"Stopping build"}'

    def fake_post(url, **kwargs):
        seen["url"] = url
        return Response()

    monkeypatch.setattr(bs.requests, "post", fake_post)
    bs.stop_build(auth=None, build_id="b1")
    assert seen["url"] == "https://api-cloud.browserstack.com/app-automate/maestro/builds/b1/stop"
