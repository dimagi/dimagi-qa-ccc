"""Run a web action while a Maestro build is already in flight.

run_flows() blocks the calling thread polling BrowserStack, so a hybrid test can
normally only do web work *before* or *after* the device session. Some cases
need it *during*: anything where a push has to arrive at a device that is
already signed in and watching for it.

  - the one-shot "New Channel" push, which fires only when consent is first
    requested (TC-CHN-001a)
  - a message-received push landing on a backgrounded app, which is the whole
    point of the deep-link case (TC-MSG-006)
  - a send attempted while the device has just unsubscribed (TC-SUB-004)

None of these work if the web half runs first: the push then arrives before the
worker has signed in, so it reaches a device not yet registered as that user and
is simply lost. Sending afterwards is no better - the session is over.

Playwright's sync API is not shareable across threads, so the action gets its
own Playwright instance, browser and page rather than borrowing the test's.

Coordination is by delay, deliberately. The device cannot signal readiness back,
so the contract is: give the flow a generous head start here, and a long
extendedWaitUntil on the device side. Firing late is harmless - the device is
still waiting. Firing early loses the push.
"""

import threading
import time

from playwright.sync_api import sync_playwright


class DeferredWebAction:
    """A web action started on a timer, run in its own browser.

    Usage:
        trigger = DeferredWebAction(request_consent, delay_seconds=210)
        trigger.start()
        summary = run_flows(...)      # blocks; the trigger fires part-way through
        trigger.join_and_raise()
    """

    def __init__(self, action, delay_seconds, label="web action"):
        self.action = action
        self.delay_seconds = delay_seconds
        self.label = label
        self.result = None
        self.error = None
        self.fired_at = None
        self._thread = threading.Thread(target=self._run, daemon=True)

    def _run(self):
        time.sleep(self.delay_seconds)
        self.fired_at = time.time()
        print(f"STEP [MidBuild] firing {self.label} after {self.delay_seconds}s")
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(headless=True)
                try:
                    self.result = self.action(browser.new_page())
                finally:
                    browser.close()
            print(f"STEP [MidBuild] {self.label} completed: {self.result!r}")
        except Exception as exc:  # surfaced by join_and_raise, not swallowed
            self.error = exc
            print(f"STEP [MidBuild] {self.label} FAILED: {exc}")

    def start(self):
        self._thread.start()
        return self

    def join_and_raise(self, timeout=300):
        """Wait for the action to finish and re-raise anything it hit.

        Called after run_flows() returns. A device flow that failed because the
        trigger never fired should report the trigger's error, not a timeout on
        a notification that was never sent.
        """
        self._thread.join(timeout)
        if self._thread.is_alive():
            raise AssertionError(
                f"{self.label} did not finish within {timeout}s of the build ending"
            )
        if self.error is not None:
            raise AssertionError(f"{self.label} failed: {self.error}") from self.error
        return self.result
