"""Retrieval of the 6-digit PersonalID email verification code.

The whole mechanism is confined to fetch_otp() so it can be swapped without
touching a single Maestro flow. If ConnectID ever exposes email OTPs the way it
already exposes phone OTPs for demo users (GET /users/demo_users returns
PhoneDevice.token for +7426 numbers), replace the body of fetch_otp with a call
to that endpoint and delete the IMAP plumbing.

Credentials are read from the [email] section of the repo-root settings.cfg - the
same file the BrowserStack credentials already use - or from environment
variables on CI. They are never passed on a command line, where they would show
up in process listings and CI logs.
"""

import email
import imaplib
import os
import re
import time
from configparser import ConfigParser
from email.utils import parsedate_to_datetime
from pathlib import Path

SETTINGS_FILE = Path(__file__).parent.parent.parent / "settings.cfg"

# Six digits not adjacent to other digits, so reference numbers and dates in the
# same message are not mistaken for the code.
OTP_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")

DEFAULT_TIMEOUT_SECONDS = 120
DEFAULT_POLL_SECONDS = 5


def extract_otp(body):
    """The 6-digit code in an email body, or None if there isn't one."""
    if not body:
        return None
    match = OTP_PATTERN.search(body)
    return match.group(1) if match else None


def _settings():
    """IMAP connection details, from the environment first then settings.cfg."""
    host = os.getenv("QA_EMAIL_IMAP_HOST")
    user = os.getenv("QA_EMAIL_IMAP_USER")
    password = os.getenv("QA_EMAIL_IMAP_PASSWORD")
    if host and user and password:
        return host, user, password

    config = ConfigParser()
    config.read(SETTINGS_FILE)
    if not config.has_section("email"):
        raise RuntimeError(
            "Email OTP retrieval is not configured.\n\n"
            f"Add an [email] section to {SETTINGS_FILE}:\n\n"
            "  [email]\n"
            "  address = your.qa.mailbox@example.com\n"
            "  imap_host = imap.gmail.com\n"
            "  imap_user = your.qa.mailbox@example.com\n"
            "  imap_password = your-app-password\n\n"
            "Gmail needs an app password with IMAP enabled, not the account "
            "password. On CI set QA_EMAIL_IMAP_HOST / _USER / _PASSWORD instead."
        )
    section = config["email"]
    return (
        section.get("imap_host", "imap.gmail.com"),
        section["imap_user"],
        section["imap_password"],
    )


def base_address():
    """The mailbox that plus-addressed test emails route back to."""
    address = os.getenv("QA_EMAIL_ADDRESS")
    if address:
        return address
    config = ConfigParser()
    config.read(SETTINGS_FILE)
    if not config.has_option("email", "address"):
        raise RuntimeError(f"No [email] address in {SETTINGS_FILE}")
    return config.get("email", "address")


def _body_of(message):
    """The plain-text body of an email.message.Message, or ''."""
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode(errors="replace")
        return ""
    payload = message.get_payload(decode=True)
    return payload.decode(errors="replace") if payload else ""


def _newest_code_for(recipient, not_before, host, user, password):
    """The code from the newest message to recipient sent at or after not_before.

    The not_before guard matters: plus-addressed test addresses are reused across
    runs, and without it a stale code from an earlier run would be returned and
    the test would fail confusingly on a code that was once valid.
    """
    connection = imaplib.IMAP4_SSL(host)
    try:
        connection.login(user, password)
        connection.select("INBOX")
        status, data = connection.search(None, "TO", f'"{recipient}"')
        if status != "OK" or not data or not data[0]:
            return None

        # Newest first - stop at the first message that is recent enough.
        for message_id in reversed(data[0].split()):
            status, fetched = connection.fetch(message_id, "(RFC822)")
            if status != "OK" or not fetched or not fetched[0]:
                continue
            message = email.message_from_bytes(fetched[0][1])
            date_header = message.get("Date")
            if date_header and not_before:
                try:
                    if parsedate_to_datetime(date_header).timestamp() < not_before:
                        return None  # Older than this run; nothing newer behind it.
                except (TypeError, ValueError):
                    pass  # Undated message - fall through and try to read it.
            code = extract_otp(_body_of(message))
            if code:
                return code
        return None
    finally:
        try:
            connection.logout()
        except imaplib.IMAP4.error:
            pass


def fetch_otp(
    recipient,
    not_before=None,
    timeout=DEFAULT_TIMEOUT_SECONDS,
    poll_interval=DEFAULT_POLL_SECONDS,
):
    """Poll the QA mailbox until a code addressed to recipient arrives.

    not_before is a unix timestamp; messages older than it are ignored. Pass the
    time just before the app was asked to send the code. Defaults to the moment
    this call starts, which is right for the normal request-then-fetch sequence.

    Raises TimeoutError if no code arrives within timeout seconds.
    """
    if not_before is None:
        not_before = time.time()
    host, user, password = _settings()
    deadline = time.time() + timeout
    while time.time() < deadline:
        code = _newest_code_for(recipient, not_before, host, user, password)
        if code:
            return code
        time.sleep(poll_interval)
    raise TimeoutError(
        f"No email OTP for {recipient} within {timeout}s. Check the address is "
        "reachable from the app's environment and that the mailbox is correct."
    )
