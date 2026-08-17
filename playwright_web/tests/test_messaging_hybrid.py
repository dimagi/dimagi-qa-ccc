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

import os
import time

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


def test_broadcast_connect_survey_is_answerable(page, test_data, config, settings, messaging_data):
    """TC-BRD-003 - a Connect Survey broadcast is delivered and can be answered.

    Ports the mobile half of legacy test_tc_10 (Messaging_6), with the two
    things that made the legacy version weaker replaced:

    - The questions and answers are data, not literals baked into
      fill_survey_form(), so the test is not tied to one specific survey form.
    - The first answer is unique per run, so the submission this run produced is
      identifiable rather than indistinguishable from every previous run's.

    TC-BRD-004 - proving the completed submission reached HQ's submit history -
    is deliberately not asserted yet: it needs the Submit History report mapped,
    and answering the survey is worth landing on its own first. Until then this
    covers delivery and answering, not submission.
    """
    flow = messaging_data["survey_flow"]

    from flows.mobile_runner import env_by_flow

    worker = env_by_flow([flow], config.env)[flow]

    # Unique so the resulting submission is attributable to this run - which is
    # what TC-BRD-004 will search HQ for.
    stamp = str(int(time.time()))[-6:]
    first_answer = f"Automation Survey {stamp}"

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.open_messaging_option("Broadcasts")

    # --- WEB: send the survey ---
    messaging.create_broadcast_with_connect_survey(
        user_recipients=[messaging_data["worker_user_id"]],
        survey_form=messaging_data["survey_form"],
    )
    print(f"STEP [Hybrid] Survey broadcast sent, first answer will be {first_answer!r}")

    # --- MOBILE: the worker answers it question by question ---
    from flows.mobile_runner import run_flows

    summary = run_flows(
        flows=[flow],
        env={
            **worker,
            "CHANNEL_NAME": messaging_data["channel_name"],
            "Q1_LABEL": messaging_data["survey_q1_label"],
            "Q1_ANSWER": first_answer,
            "Q2_LABEL": messaging_data["survey_q2_label"],
            "Q2_ANSWER": messaging_data["survey_q2_answer"],
        },
        reports=False,
        app_env=config.env,
    )
    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Survey was not delivered or could not be answered: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )


def test_keyword_triggered_from_channel_returns_a_message(page, test_data, config, settings, messaging_data):
    """TC-KWD-002 - sending a keyword in the channel returns its Connect Message.

    Has no legacy equivalent: the Selenium suite never touched Keywords.

    This is also the only case that exercises the worker-initiated send path
    against a real consequence, which is why the plan carries no separate "send
    free text" test. An outgoing bubble proves only that the UI drew something -
    MessageManager stores and renders it before the network call - whereas a
    reply proves the message reached the server and was processed.

    The keyword is removed at both ends so prod does not accumulate them and the
    test stays re-runnable.
    """
    flow = messaging_data["keyword_flow"]

    from flows.mobile_runner import env_by_flow

    worker = env_by_flow([flow], config.env)[flow]

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.delete_existing_keywords()
    try:
        # --- WEB: configure the keyword and the reply it should send ---
        keyword, reply = messaging.create_keyword_with_connect_message()
        print(f"STEP [Hybrid] Keyword {keyword!r} configured to reply {reply!r}")

        # --- MOBILE: send that keyword from the channel and await the reply ---
        from flows.mobile_runner import run_flows

        summary = run_flows(
            flows=[flow],
            env={
                **worker,
                "CHANNEL_NAME": messaging_data["channel_name"],
                "KEYWORD": keyword,
                "EXPECTED_REPLY": reply,
            },
            reports=False,
            app_env=config.env,
        )
        print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"Keyword did not return its reply: {summary['passed']} passed / {summary['failed']} failed - "
            f"see {summary['build_url']}"
        )
    finally:
        messaging.delete_existing_keywords()


def test_consent_gates_message_delivery(config, settings, messaging_data):
    """TC-SUB-004 / TC-SUB-006 - nothing arrives while unsubscribed, delivery resumes after.

    Three phases, because ordering has to be a fact rather than a hope:

      build 1  the device unsubscribes and the build ends
      web      a broadcast is sent with the channel provably unsubscribed
      build 2  the device confirms it never arrived, resubscribes, and a second
               broadcast (sent mid-build) does arrive

    Consent is server-side state, so it survives the reinstall between builds.

    The single-build version of this was wrong in a way worth remembering: it
    tried to wait out the blocked send between unsubscribing and resubscribing,
    but the wait was an extendedWaitUntil on an already-visible element and
    returned instantly. The device resubscribed a minute BEFORE the message was
    sent, so it was delivered to a consented channel and the test proved
    nothing while looking like a product bug.

    The pair is judged together: TC-SUB-004 alone would still pass if delivery
    were broken permanently, so the blocked message's absence is only checked
    after the allowed one has arrived.
    """
    unsubscribe_flow = messaging_data["unsubscribe_flow"]
    delivery_flow = messaging_data["consent_delivery_flow"]
    allowed_delay = int(messaging_data.get("allowed_send_delay_seconds", 500))

    from flows.mid_build_web import DeferredWebAction
    from flows.mobile_runner import env_by_flow, run_flows

    stamp = int(time.time() * 1000)
    blocked = f"Blocked while unsubscribed {stamp}"
    allowed = f"Allowed after resubscribe {stamp}"

    def send(body):
        def action(page):
            LoginPage(page).valid_login_cchq(config, settings)
            CCHQHomePage(page).verify_home_page_title("Welcome")
            messaging = CCHQMessagingPage(page)
            messaging.open_messaging_option("Broadcasts")
            return messaging.create_broadcast_with_connect_message(
                user_recipients=[messaging_data["worker_user_id"]],
                message=body,
            )

        return action

    # --- Phase 1: unsubscribe and end the session ---
    worker = env_by_flow([unsubscribe_flow], config.env)[unsubscribe_flow]
    first = run_flows(
        flows=[unsubscribe_flow],
        env={**worker, "CHANNEL_NAME": messaging_data["channel_name"]},
        reports=False,
        app_env=config.env,
    )
    print(f"STEP [Hybrid] unsubscribe build {first['build_id']} -> {first['status']}")
    assert first["status"] == "SUCCESS", (
        f"Could not leave the channel unsubscribed, so the rest proves nothing - see {first['build_url']}"
    )

    # --- Phase 2: send while it is definitely unsubscribed ---
    blocked_send = DeferredWebAction(send(blocked), 0, label="send while unsubscribed").start()
    blocked_send.join_and_raise()
    print(f"STEP [Hybrid] sent while unsubscribed: {blocked!r}")

    # --- Phase 3: verify absence, resubscribe, and verify delivery resumes ---
    worker = env_by_flow([delivery_flow], config.env)[delivery_flow]
    allowed_send = DeferredWebAction(send(allowed), allowed_delay, label="send after resubscribe").start()
    second = run_flows(
        flows=[delivery_flow],
        env={
            **worker,
            "CHANNEL_NAME": messaging_data["channel_name"],
            "MESSAGE_BLOCKED": blocked,
            "MESSAGE_ALLOWED": allowed,
        },
        reports=False,
        app_env=config.env,
    )
    allowed_send.join_and_raise()

    print(f"STEP [Hybrid] delivery build {second['build_id']} -> {second['status']} ({second['build_url']})")
    assert second["status"] == "SUCCESS", (
        f"Consent did not gate delivery as expected: {second['passed']} passed / "
        f"{second['failed']} failed - see {second['build_url']}"
    )


def test_message_push_opens_the_thread(config, settings, messaging_data):
    """TC-MSG-006 - tapping a messaging push opens that channel's thread.

    Previously judged not automatable, wrongly. The case needs a message to
    arrive while the app is BACKGROUNDED, which neither ordering can produce:
    send before the build and it is already queued, so it arrives on the first
    sync rather than as a push; send after and the session is over.

    DeferredWebAction sends it PART-WAY THROUGH the build instead, by which time
    the worker is signed in, the app is backgrounded and the device is parked in
    the notification shade.

    The flow matches the message BODY in the shade rather than a notification
    title: the body is generated here and injected, whereas the title's wording
    is the product's business and asserting it would make this a test of copy.
    """
    flow = messaging_data["push_deeplink_flow"]
    delay = int(messaging_data.get("consent_trigger_delay_seconds", 210))

    from flows.mid_build_web import DeferredWebAction
    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]
    message = f"Test Connect Message Broadcast {int(time.time() * 1000)}"

    def send_broadcast(page):
        LoginPage(page).valid_login_cchq(config, settings)
        CCHQHomePage(page).verify_home_page_title("Welcome")
        messaging = CCHQMessagingPage(page)
        messaging.open_messaging_option("Broadcasts")
        return messaging.create_broadcast_with_connect_message(
            user_recipients=[messaging_data["worker_user_id"]],
            message=message,
        )

    trigger = DeferredWebAction(send_broadcast, delay, label="send broadcast").start()

    summary = run_flows(
        flows=[flow],
        env={
            **worker,
            "CHANNEL_NAME": messaging_data["channel_name"],
            "EXPECTED_MESSAGE": message,
        },
        reports=False,
        app_env=config.env,
    )
    # Surface a trigger failure first: if the broadcast never went out, the
    # device timed out waiting for something nobody sent, and reporting that as
    # a push-delivery failure would be misleading.
    trigger.join_and_raise()

    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Push did not arrive or did not open the thread: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )


def test_first_consent_request_creates_a_channel(config, settings, messaging_data):
    """TC-CHN-001a / TC-CHN-002 - requesting consent creates a channel and pushes.

    One-shot per (worker, HQ domain), so it is gated behind an env var the way
    test_setup_tasking_opportunity.py gates its setup:

        MESSAGING_CHANNEL_SETUP=1 pytest tests/test_messaging_hybrid.py -k first_consent --env stage

    ConnectID's CreateChannelView is get_or_create on (server, connect_user,
    channel_source), and channel_source is the HQ domain. The first request
    creates the channel and fires a "New Channel" push; every later one returns
    the existing channel and sends nothing. Left ungated it would burn a device
    build on every CI run and then skip. TC-CHN-001b covers the repeat behaviour
    on every run; see the plan for how automating learn + assessment would make
    this one per-run too.

    The web half fires PART-WAY THROUGH the build rather than before it: a push
    sent before the worker signs in reaches a device not yet registered as that
    user and is lost. DeferredWebAction runs it on a timer in its own browser,
    while run_flows() blocks here polling BrowserStack.
    """
    if os.getenv("MESSAGING_CHANNEL_SETUP") != "1":
        pytest.skip(
            "One-shot: the 'New Channel' push fires only the first time a worker gets a channel. "
            "Run with MESSAGING_CHANNEL_SETUP=1 against a worker that has none."
        )

    flow = messaging_data["channel_created_flow"]
    delay = int(messaging_data.get("consent_trigger_delay_seconds", 210))

    from flows.mid_build_web import DeferredWebAction
    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]

    def request_consent(page):
        LoginPage(page).valid_login_cchq(config, settings)
        CCHQHomePage(page).verify_home_page_title("Welcome")
        messaging = CCHQMessagingPage(page)
        messaging.open_user_consent()
        return messaging.request_messaging_consent()

    trigger = DeferredWebAction(request_consent, delay, label="request messaging consent").start()

    summary = run_flows(
        flows=[flow],
        env={**worker, "CHANNEL_NAME": messaging_data["channel_name"]},
        reports=False,
        app_env=config.env,
    )
    banner = trigger.join_and_raise()

    # Interpret the banner before judging the device. If nothing was created the
    # channel already existed, so the push could never have fired and a device
    # failure says nothing about the product.
    if banner and "no channels created" in banner.lower():
        pytest.skip(
            f"Consent request created nothing ({banner!r}) - this worker already has a channel, "
            "so the one-shot push cannot fire again. Use a worker with no channels, which "
            "messaging_empty_state.yaml can confirm."
        )

    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Channel creation was not observed on the device: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )


def test_channel_unsubscribe_and_resubscribe(config, messaging_data):
    """TC-SUB-001/002/003/005 - consent can be withdrawn and restored on the device.

    Device-only despite living in this file: consent is a device action
    (POST /messaging/update_consent/), so there is no web half to drive. It sits
    here so it is run and reported alongside the rest of the messaging suite
    rather than needing its own entry point.

    The delivery-blocked pair - TC-SUB-004 (nothing arrives while unsubscribed)
    and TC-SUB-006 (delivery resumes afterwards) - is not covered here. Both
    need a send to happen *between* two device sessions, and a Maestro build
    cannot be paused midway; they want two run_flows() calls with a web send in
    between, which is worth doing once this passes.

    ConnectID makes TC-SUB-004 cheap when we get to it: SendServerConnectMessage
    returns 400 NO_USER_CONSENT for an unsubscribed channel, so the assertion
    can be made on the web side rather than by proving absence on a device.

    The flow resubscribes before it ends, so the account is left as found and
    the test is re-runnable.
    """
    flow = messaging_data["consent_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]

    summary = run_flows(
        flows=[flow],
        env={**worker, "CHANNEL_NAME": messaging_data["channel_name"]},
        reports=False,
        app_env=config.env,
    )
    print(f"STEP [Mobile] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Unsubscribe/resubscribe did not behave as expected: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )
