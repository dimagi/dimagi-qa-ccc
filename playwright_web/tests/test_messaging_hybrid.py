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

import datetime
import os
import time

import pytest

from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.cchq_messaging_page import CCHQMessagingPage
from pages.cchq_reports_page import CCHQReportsPage
from tests.test_messaging_web import _env_value

# Keys whose value differs per environment. Anything left out of this tuple is
# used verbatim on both, which is fine for genuinely shared values and silently
# wrong for the rest: alert_worker_user_id and alert_opportunity were missing
# here, so a staging run addressed the alert to a prod HQ user id and looked for
# a prod opportunity on the device. Neither is empty, so the fixture's
# missing-value skip did not catch it either - the tests would simply have
# failed, on staging only, for a reason that had nothing to do with messaging.
ENV_SPECIFIC_KEYS = (
    "survey_form",
    "worker_user_id",
    "channel_name",
    "spare_channel",
    "alert_worker_user_id",
    "alert_opportunity",
)


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

    Also covers **TC-BRD-004** - that the completed survey reached HQ. The
    device answering every question does not prove the submission landed, so
    the test finishes by finding this run's own row in Submit History.

    Submit History shows only who submitted, when, and which form - not the case
    name - so the row is pinned to this run with a timestamp cutoff taken before
    the send, not with the unique first answer. Note the submission is
    attributed to the Connect user id rather than the PersonalID mobile worker,
    which is why searching by mobile worker turned up nothing and left these
    cases looking blocked.
    """
    flow = messaging_data["survey_flow"]

    from flows.mobile_runner import env_by_flow

    worker = env_by_flow([flow], config.env)[flow]

    # Unique so the resulting submission is attributable to this run - which is
    # what TC-BRD-004 will search HQ for.
    stamp = str(int(time.time()))[-6:]
    first_answer = f"Automation Survey {stamp}"

    # Cutoff for the submit-history search, taken before anything is sent so it
    # cannot exclude this run's own submission. Without it the newest matching
    # row from a PREVIOUS run satisfies the assertion and the test passes having
    # proved nothing.
    started_at = datetime.datetime.now(datetime.timezone.utc)

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
            "Q3_LABEL": messaging_data["survey_q3_label"],
            "Q3_ANSWER": messaging_data["survey_q3_answer"],
            "Q4_LABEL": messaging_data["survey_q4_label"],
            "Q4_ANSWER": messaging_data["survey_q4_answer"],
        },
        reports=False,
        app_env=config.env,
    )
    print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Survey was not delivered or could not be answered: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )

    # --- WEB: TC-BRD-004, the completed survey reached HQ ---
    # Matched on survey_form itself rather than a hardcoded form name: Submit
    # History's breadcrumb is exactly that string, so pointing the suite at a
    # different form cannot leave a stale literal behind here.
    reports = CCHQReportsPage(page, config)
    submission = reports.wait_for_submission(
        user_id=messaging_data["worker_user_id"],
        form_path_contains=messaging_data["survey_form"],
        after=started_at,
    )
    assert submission, (
        f"The survey was answered on the device but no {messaging_data['survey_form']!r} "
        f"submission by {messaging_data['worker_user_id']} appeared in Submit History after "
        f"{started_at:%Y-%m-%d %H:%M:%S} UTC - see {summary['build_url']}"
    )
    print(
        f"STEP [Web] Submission reached HQ: {submission['path']} at {submission['time']} "
        f"(form {submission['form_id']})"
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


def test_keyword_returns_a_survey_that_is_answerable(page, config, settings, messaging_data):
    """TC-KWD-004 - a keyword whose reply is a Connect Survey is delivered and answerable.

    The survey half of TC-KWD-002. There the reply is a single canned message,
    so one bubble ends the test; here the reply is a conversation, and each
    question arrives only once the previous is answered - so reaching the last
    one proves HQ is running the survey rather than echoing a string back.

    Also covers **TC-KWD-005** - that the completed survey reached HQ - the same
    way TC-BRD-004 does, bounded by a cutoff taken before the keyword is
    configured so a previous run's submission cannot satisfy it.

    The keyword is removed at both ends so prod does not accumulate them and the
    test stays re-runnable.
    """
    flow = messaging_data["keyword_survey_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]
    stamp = str(int(time.time()))[-6:]
    first_answer = f"Automation Keyword Survey {stamp}"
    started_at = datetime.datetime.now(datetime.timezone.utc)

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.delete_existing_keywords()
    try:
        # --- WEB: configure a keyword whose reply is the survey ---
        keyword = messaging.create_keyword_with_connect_survey(
            survey_form=messaging_data["survey_form"],
        )
        print(f"STEP [Hybrid] Keyword {keyword!r} configured to reply with a Connect Survey")

        # --- MOBILE: send the keyword, then answer every question ---
        summary = run_flows(
            flows=[flow],
            env={
                **worker,
                "CHANNEL_NAME": messaging_data["channel_name"],
                "KEYWORD": keyword,
                "Q1_LABEL": messaging_data["survey_q1_label"],
                "Q1_ANSWER": first_answer,
                "Q2_LABEL": messaging_data["survey_q2_label"],
                "Q2_ANSWER": messaging_data["survey_q2_answer"],
                "Q3_LABEL": messaging_data["survey_q3_label"],
                "Q3_ANSWER": messaging_data["survey_q3_answer"],
                "Q4_LABEL": messaging_data["survey_q4_label"],
                "Q4_ANSWER": messaging_data["survey_q4_answer"],
            },
            reports=False,
            app_env=config.env,
        )
        print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"The keyword survey was not delivered or could not be answered: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )

        # --- WEB: TC-KWD-005, the completed survey reached HQ ---
        reports = CCHQReportsPage(page, config)
        submission = reports.wait_for_submission(
            user_id=messaging_data["worker_user_id"],
            form_path_contains=messaging_data["survey_form"],
            after=started_at,
        )
        assert submission, (
            f"The keyword survey was answered on the device but no "
            f"{messaging_data['survey_form']!r} submission by "
            f"{messaging_data['worker_user_id']} appeared in Submit History after "
            f"{started_at:%Y-%m-%d %H:%M:%S} UTC - see {summary['build_url']}"
        )
        print(
            f"STEP [Web] Submission reached HQ: {submission['path']} at {submission['time']} "
            f"(form {submission['form_id']})"
        )
    finally:
        messaging.delete_existing_keywords()


def test_conditional_alert_reaches_the_channel(page, config, settings, messaging_data):
    """TC-CAL-003 - an alert fires on a matching form submission and reaches the channel.

    The last of the legacy ports: test_tc_09's mobile half (Messaging_2).

    Runs as the TASKING worker, not the messaging one. The messaging worker is
    enrolled on no opportunity on prod - legacy's "test_09" no longer exists -
    so it cannot submit the form that fires the alert. The tasking worker is
    already enrolled, past assessment and delivering on an opportunity whose
    deliver app has the Registration Form, and is a mobile worker on the same
    HQ domain, so it can receive the alert too.

    That works because the alert matches a CASE PROPERTY while its recipient is
    a USER: submitter and recipient are free to be the same account, and no new
    opportunity was needed.

    Coupling to be aware of: this shares an account with the tasking suite, so
    the two must not run device sessions concurrently - a PersonalID number
    cannot hold a session twice.
    """
    flow = messaging_data["conditional_alert_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]

    # The join between the HQ rule and the mobile submission. Unique per run, so
    # a stale alert from a previous run cannot satisfy this one.
    entity_id = str(int(time.time() * 1000) % 1_000_000)

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.open_messaging_option("Conditional Alerts")
    messaging.delete_existing_alerts(messaging.MESSAGE_ALERT_NAME)
    try:
        # --- WEB: the alert has to exist before the form is submitted ---
        message = messaging.create_connect_message_conditional_alert(
            entity_id_value=entity_id,
            user_recipients=[messaging_data["alert_worker_user_id"]],
        )
        print(f"STEP [Hybrid] Alert created on entity_id={entity_id}, body {message!r}")

        # --- MOBILE: submit the form carrying that entity id, then read the channel ---
        summary = run_flows(
            flows=[flow],
            env={
                **worker,
                "OPPORTUNITY": messaging_data["alert_opportunity"],
                "CHANNEL_NAME": messaging_data["channel_name"],
                "ENTITY_ID": entity_id,
                "EXPECTED_MESSAGE": message,
            },
            reports=False,
            app_env=config.env,
        )
        print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"The alert did not reach the channel: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )
    finally:
        messaging.open_messaging_option("Conditional Alerts")
        messaging.delete_existing_alerts(messaging.MESSAGE_ALERT_NAME)


def test_conditional_alert_survey_is_answerable(page, config, settings, messaging_data):
    """TC-CAL-005 - an alert-triggered Connect Survey is delivered and answerable.

    Ports test_tc_09's Messaging_3. Same trigger as TC-CAL-003 - a form
    submission carrying the entity id the alert filters on - but the content is
    a survey, so the worker answers it question by question in the chat.

    Runs as the tasking worker for the same reason as TC-CAL-003: it is the
    account that can actually submit the form. See that test for the coupling
    note.

    Reaching the second question is what makes this more than a delivery test:
    it only arrives once the first is answered, so the survey is proven to be a
    live conversation rather than a single canned message.

    Also covers **TC-CAL-006** - that the completed survey reached HQ - by
    finding this run's row in Submit History. The match is on the full
    survey_form breadcrumb rather than just "Registration Form", because this
    flow submits a Delivery App Registration Form too (that is what fires the
    alert), and a loose match would happily assert on that one instead.
    """
    flow = messaging_data["conditional_alert_survey_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]
    entity_id = str(int(time.time() * 1000) % 1_000_000)
    first_answer = f"Automation Alert Survey {entity_id}"
    # Taken before the alert is created, so it cannot exclude this run's own
    # submission - see TC-BRD-004 for why an unbounded search proves nothing.
    started_at = datetime.datetime.now(datetime.timezone.utc)

    login_page = LoginPage(page)
    login_page.valid_login_cchq(config, settings)
    CCHQHomePage(page).verify_home_page_title("Welcome")

    messaging = CCHQMessagingPage(page)
    messaging.open_messaging_option("Conditional Alerts")
    messaging.delete_existing_alerts(messaging.SURVEY_ALERT_NAME)
    try:
        messaging.create_connect_survey_conditional_alert(
            entity_id_value=entity_id,
            user_recipients=[messaging_data["alert_worker_user_id"]],
            survey_form=messaging_data["survey_form"],
        )
        print(f"STEP [Hybrid] Survey alert created on entity_id={entity_id}")

        summary = run_flows(
            flows=[flow],
            env={
                **worker,
                "OPPORTUNITY": messaging_data["alert_opportunity"],
                "CHANNEL_NAME": messaging_data["channel_name"],
                "ENTITY_ID": entity_id,
                "Q1_LABEL": messaging_data["survey_q1_label"],
                "Q1_ANSWER": first_answer,
                "Q2_LABEL": messaging_data["survey_q2_label"],
                "Q2_ANSWER": messaging_data["survey_q2_answer"],
                "Q3_LABEL": messaging_data["survey_q3_label"],
                "Q3_ANSWER": messaging_data["survey_q3_answer"],
                "Q4_LABEL": messaging_data["survey_q4_label"],
                "Q4_ANSWER": messaging_data["survey_q4_answer"],
            },
            reports=False,
            app_env=config.env,
        )
        print(f"STEP [Hybrid] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
        assert summary["status"] == "SUCCESS", (
            f"The alert survey was not delivered or could not be answered: {summary['passed']} passed / "
            f"{summary['failed']} failed - see {summary['build_url']}"
        )

        # --- WEB: TC-CAL-006, the completed survey reached HQ ---
        reports = CCHQReportsPage(page, config)
        submission = reports.wait_for_submission(
            user_id=messaging_data["alert_worker_user_id"],
            form_path_contains=messaging_data["survey_form"],
            after=started_at,
        )
        assert submission, (
            f"The alert survey was answered on the device but no "
            f"{messaging_data['survey_form']!r} submission by "
            f"{messaging_data['alert_worker_user_id']} appeared in Submit History after "
            f"{started_at:%Y-%m-%d %H:%M:%S} UTC - see {summary['build_url']}"
        )
        print(
            f"STEP [Web] Submission reached HQ: {submission['path']} at {submission['time']} "
            f"(form {submission['form_id']})"
        )
    finally:
        messaging.open_messaging_option("Conditional Alerts")
        messaging.delete_existing_alerts(messaging.SURVEY_ALERT_NAME)


def test_channel_list_shows_empty_state(config, messaging_data):
    """TC-CHN-003 - a worker in no channels is told so, not shown a blank screen.

    Device-only, and the one case that cannot share an account with anything
    else. It runs as MAESTRO_MESSAGING_EMPTY_STATE, which has to be an account
    that has never been in ANY channel on ANY domain - a channel cannot be
    undone, so a single consent request to that number retires this case for
    good. mobile_workers.yaml carries the same warning next to the entry.

    Legacy's verify_channel_list() accepted empty OR populated, so it pinned
    neither state and would have passed here regardless.

    A failure is worth reading carefully: it most likely means the account has
    picked up a channel rather than that the empty state is broken.
    """
    flow = messaging_data["empty_state_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]

    summary = run_flows(flows=[flow], env=worker, reports=False, app_env=config.env)
    print(f"STEP [Mobile] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"The channel list did not show the empty state: {summary['passed']} passed / "
        f"{summary['failed']} failed. If this account has been added to a channel the case cannot "
        f"pass again and needs a fresh worker - see {summary['build_url']}"
    )


def test_subscribed_channels_sort_before_unsubscribed(config, messaging_data):
    """TC-CHN-006 - subscribed channels list above unsubscribed ones.

    Device-only: the sort is ChannelAdapter.setChannels, and nothing about it is
    observable from HQ.

    Needs no setup. The account already holds several channels and they are all
    subscribed, so the flow creates the unsubscribed state itself by
    unsubscribing a spare, then restores it - which also keeps the case
    re-runnable rather than depending on a channel someone left in the right
    state by hand.

    It moves a channel that starts ABOVE the anchor to below it, and back. A
    test that only checked "the unsubscribed one is at the bottom" would pass
    even if the app never sorted at all, provided the row already happened to
    sit last.
    """
    flow = messaging_data["subscription_flow"]

    from flows.mobile_runner import env_by_flow, run_flows

    worker = env_by_flow([flow], config.env)[flow]

    summary = run_flows(
        flows=[flow],
        env={
            **worker,
            "CHANNEL_NAME": messaging_data["channel_name"],
            "SPARE_CHANNEL": messaging_data["spare_channel"],
        },
        reports=False,
        app_env=config.env,
    )
    print(f"STEP [Mobile] Maestro build {summary['build_id']} -> {summary['status']} ({summary['build_url']})")
    assert summary["status"] == "SUCCESS", (
        f"Channel sort did not behave as expected: {summary['passed']} passed / "
        f"{summary['failed']} failed - see {summary['build_url']}"
    )


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
