"""Hybrid web -> device messaging tests (CCCT-2671).

Web sends the message from CommCare HQ, a Maestro flow on a BrowserStack device
asserts it arrives in the worker's channel. Same shape as the tasking hybrid
test: pytest owns the scenario and calls run_flows() mid-test, so the device
half is one build with no pausing.

Why the assertion has to happen on the device: message bodies are AEAD-encrypted
with a per-channel key that only the device holds, so no test can read message
content server-side. The web half therefore returns the exact body it sent and
the flow matches on it, rather than settling for "some message arrived".

Run with:  pytest playwright_web/tests/test_messaging_hybrid.py --env prod
"""

import pytest

from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.cchq_messaging_page import CCHQMessagingPage
from tests.test_messaging_web import _env_value

ENV_SPECIFIC_KEYS = ("survey_form", "worker_user_id", "channel_name")


@pytest.fixture
def messaging_data(test_data, config):
    data = dict(test_data.get("MESSAGING"))
    for key in ENV_SPECIFIC_KEYS:
        data[key] = _env_value(data, key, config)
    missing = [key for key in ENV_SPECIFIC_KEYS if not data.get(key)]
    if missing:
        pytest.skip(
            f"MESSAGING data not configured for env '{config.env}' (missing: {', '.join(missing)})"
        )
    return data


def test_broadcast_connect_message_reaches_the_channel(page, test_data, config, settings, messaging_data):
    """TC-BRD-002 - a Connect Message broadcast arrives in the worker's channel.

    Ports the mobile half of legacy test_tc_10 (Messaging_5). Also exercises
    TC-CHN-002 on the way: the flow asserts the channel is present in the list
    before opening it, so a channel that failed to sync fails here with that
    reason rather than as a missing message.
    """
    flow = messaging_data["broadcast_flow"]

    # Resolve the worker from mobile_workers.yaml - the same single source the
    # Maestro runner uses - so the identity the device signs in with and the one
    # this test reasons about cannot drift apart.
    from flows.mobile_runner import env_by_flow

    worker = env_by_flow([flow], config.env)[flow]

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.open_messaging_option("Broadcasts")

    # --- WEB: send the broadcast ---
    message = messaging.create_broadcast_with_connect_message(
        user_recipients=[messaging_data["worker_user_id"]]
    )
    print(f"STEP [Hybrid] Broadcast sent with body: {message!r}")

    # --- MOBILE: the worker opens the channel and must see that exact body ---
    from flows.mobile_runner import run_flows

    summary = run_flows(
        flows=[flow],
        env={
            # Passing the resolved worker back keeps the values this test read and
            # the values the device signs in with provably identical.
            **worker,
            "CHANNEL_NAME": messaging_data["channel_name"],
            "EXPECTED_MESSAGE": message,
        },
        # Mid-test run: don't overwrite the Maestro suite's own report.
        reports=False,
        # Each build targets one Connect server, so the APK follows the env.
        app_env=config.env,
    )
    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Broadcast did not reach the channel: {summary['passed']} passed / {summary['failed']} failed - "
        f"see {summary['build_url']}"
    )
