"""HQ-side Connect messaging tests that need no device (CCCT-2671).

Covers the cases from Messaging_Workflow_Automation_Test_Plan.xlsx that need no
device at all - configuring the HQ side and asserting it saved:

  TC-CAL-001  'What to Send' offers Connect Message and Connect Survey (alerts)
  TC-BRD-001  the same two options on Broadcasts
  TC-CAL-002  a Connect Message conditional alert can be created
  TC-CAL-004  a Connect Survey conditional alert can be created
  TC-KWD-001  a keyword replying with a Connect Message can be created
  TC-KWD-003  a keyword replying with a Connect Survey can be created
              (plus the keyword counterpart of the two dropdown checks)

The cases where a message has to actually reach a worker - TC-CAL-003/005,
TC-BRD-002/003, TC-KWD-002/004 - live in test_messaging_hybrid.py, because the
assertion can only be made on the device: message bodies are encrypted with a
per-channel key that never leaves it.

Run with:  pytest playwright_web/tests/test_messaging_web.py --env prod
"""

import time

import pytest

from pages.cchq_home_page import CCHQHomePage
from pages.cchq_login_page import LoginPage
from pages.cchq_messaging_page import CCHQMessagingPage

CONNECT_CONTENT_OPTIONS = ["Connect Message", "Connect Survey"]


def _env_value(data, key, config):
    """Resolve a key that may differ per environment.

    Unsuffixed keys hold the prod value and `<key>_staging` the staging one, so
    anything identical on both is written once.

    Local for now on purpose: PR #23 adds the same helper as
    flows/tasking_static.env_value, and this collapses into that after the
    rebase rather than duplicating it into utils/helpers.py, which that branch
    also modifies.
    """
    if config.env == "stage":
        staged = data.get(f"{key}_staging")
        if staged not in (None, ""):
            return staged
    return data.get(key)


@pytest.fixture
def messaging(page, config, settings):
    """Logged in to HQ, sitting on the Conditional Alerts page."""
    login_page = LoginPage(page)
    home_page = CCHQHomePage(page)

    login_page.valid_login_cchq(config, settings)
    home_page.verify_home_page_title("Welcome")

    messaging_page = CCHQMessagingPage(page)
    messaging_page.open_messaging_option("Conditional Alerts")
    return messaging_page


@pytest.fixture
def messaging_data(test_data, config):
    data = dict(test_data.get("MESSAGING"))
    for key in ("survey_form", "worker_user_id"):
        data[key] = _env_value(data, key, config)
    missing = [key for key, value in data.items() if not value]
    if missing:
        pytest.skip(
            f"MESSAGING data not configured for env '{config.env}' (missing: {', '.join(missing)}). "
            "The staging recipient ids still have to be read off HQ's recipient picker - see "
            "Messaging_Workflow_Automation_Test_Plan.xlsx, Prerequisites."
        )
    return data


def test_conditional_alert_offers_connect_content_types(messaging):
    """TC-CAL-001 - both Connect options are offered on Conditional Alerts.

    Walks into the wizard far enough for the content step to render; nothing is
    saved, so this leaves no alert behind.
    """
    options = messaging.open_new_alert_and_read_what_to_send_options()
    missing = [option for option in CONNECT_CONTENT_OPTIONS if option not in options]
    assert not missing, f"Conditional alert 'What to Send' is missing {missing}. Offered: {options}"


def test_broadcast_offers_connect_content_types(messaging):
    """TC-BRD-001 - both Connect options are offered on Broadcasts."""
    messaging.open_messaging_option("Broadcasts")
    options = messaging.open_new_broadcast_and_read_what_to_send_options()
    missing = [option for option in CONNECT_CONTENT_OPTIONS if option not in options]
    assert not missing, f"Broadcast 'What to Send' is missing {missing}. Offered: {options}"


def test_create_connect_message_conditional_alert(messaging, messaging_data):
    """TC-CAL-002 - a Connect Message alert saves and appears in the list.

    The alert is removed at both ends: leftovers from a failed run would
    otherwise accumulate on the domain, and the delete is also what keeps this
    re-runnable.
    """
    entity_id = str(int(time.time() * 1000) % 1_000_000)
    messaging.delete_existing_alerts(messaging.MESSAGE_ALERT_NAME)
    try:
        message = messaging.create_connect_message_conditional_alert(
            entity_id_value=entity_id,
            user_recipients=[messaging_data["worker_user_id"]],
        )
        assert message, "No message body was generated for the alert"
    finally:
        messaging.open_messaging_option("Conditional Alerts")
        messaging.delete_existing_alerts(messaging.MESSAGE_ALERT_NAME)


def test_keyword_offers_connect_content_types(messaging):
    """Both Connect options are offered as keyword content types.

    The keyword counterpart of TC-CAL-001 / TC-BRD-001. Nothing is saved, so no
    keyword is left behind.
    """
    messaging.open_keywords()
    messaging.click_add_keyword_btn()
    options = messaging.keyword_content_type_options()
    missing = [option for option in CONNECT_CONTENT_OPTIONS if option not in options]
    assert not missing, f"Keyword content type is missing {missing}. Offered: {options}"


def test_create_keyword_with_connect_message(messaging):
    """TC-KWD-001 - a keyword replying with a Connect Message can be created."""
    messaging.delete_existing_keywords()
    try:
        keyword, message = messaging.create_keyword_with_connect_message()
        assert keyword.startswith(messaging.KEYWORD_PREFIX)
        assert message, "No reply message was generated for the keyword"
    finally:
        messaging.delete_existing_keywords()


def test_create_keyword_with_connect_survey(messaging, messaging_data):
    """TC-KWD-003 - a keyword replying with a Connect Survey can be created."""
    messaging.delete_existing_keywords()
    try:
        keyword = messaging.create_keyword_with_connect_survey(
            survey_form=messaging_data["survey_form"]
        )
        assert keyword.startswith(messaging.KEYWORD_PREFIX)
    finally:
        messaging.delete_existing_keywords()


def test_create_connect_survey_conditional_alert(messaging, messaging_data):
    """TC-CAL-004 - a Connect Survey alert saves and appears in the list."""
    entity_id = str(int(time.time() * 1000) % 1_000_000)
    messaging.delete_existing_alerts(messaging.SURVEY_ALERT_NAME)
    try:
        messaging.create_connect_survey_conditional_alert(
            entity_id_value=entity_id,
            user_recipients=[messaging_data["worker_user_id"]],
            survey_form=messaging_data["survey_form"],
        )
    finally:
        messaging.open_messaging_option("Conditional Alerts")
        messaging.delete_existing_alerts(messaging.SURVEY_ALERT_NAME)
