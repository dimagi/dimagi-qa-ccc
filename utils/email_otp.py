"""Reading the PersonalID email verification code from the QA mailbox.

Modelled on dimagi-qa-sureadhere's testPages/email/email_verification.py, which
does the same job for that product's password-reset flow.

The important property is that this is a plain synchronous call: the Appium test
drives the device while Python holds the session, so it can pause mid-test, read
the inbox and type the code in - exactly as the SureAdhere web tests do. This
works against BrowserStack too, because the Python process runs locally and only
the device is remote.

Maestro flows cannot use this. They execute remotely as declarative YAML with no
way to call back into Python mid-flow, so any case needing a real code belongs in
the Appium suite.

The email PersonalID sends (connect-id users/email_utils.py):

    Subject: Your PersonalID verification code
    Body:    Your email verification code is: 123456
             This code expires in 10 minutes.

Note the body carries two numbers - the code and the expiry - so the code is
matched as exactly six digits with no digit either side.
"""

import datetime
import re
import time

from imap_tools import AND, MailBox

from utils.helpers import SettingsLoader

OTP_SUBJECT = "Your PersonalID verification code"

# Exactly six digits, not adjacent to other digits, so "expires in 10 minutes"
# and any reference numbers are never mistaken for the code.
OTP_PATTERN = re.compile(r"(?<!\d)(\d{6})(?!\d)")

# 120s was not enough. On staging 2026-09-10 a code was sent inside the window
# and still could not be fetched during it: the message carried an in-window Date
# header but did not become visible over IMAP until later, and the same run's
# resent code did the same. Both were in the mailbox afterwards. The delay is in
# mail delivery and indexing, not in the product - the codes were sent.
#
# 180s costs nothing on the normal path, where a code is found on the first or
# second poll, and removes a flake that otherwise burns a full ten-minute run.
DEFAULT_TIMEOUT_SECONDS = 180
DEFAULT_POLL_SECONDS = 5


def extract_otp(body):
    """The 6-digit code in an email body, or None if there isn't one."""
    if not body:
        return None
    match = OTP_PATTERN.search(body)
    return match.group(1) if match else None


class EmailOtpReader:
    """Reads PersonalID verification codes from the shared QA mailbox.

    Credentials come from the [email] section of settings.cfg, or the QA_EMAIL_*
    environment variables on CI. They are never passed on a command line, where
    they would appear in process listings and CI logs.
    """

    def __init__(self, settings=None):
        settings = settings or SettingsLoader()
        self.imap_host = settings.get(
            section="email", key="imap_host", env_var="QA_EMAIL_IMAP_HOST", default="imap.gmail.com"
        )
        self.base_address = settings.get(section="email", key="address", env_var="QA_EMAIL_ADDRESS")
        # For Gmail the mailbox and the IMAP user are the same, so imap_user is
        # optional - only set it where they genuinely differ.
        self.imap_user = (
            settings.get(section="email", key="imap_user", env_var="QA_EMAIL_IMAP_USER")
            or self.base_address
        )
        self.imap_pass = settings.get(section="email", key="imap_password", env_var="QA_EMAIL_IMAP_PASSWORD")

        if not (self.imap_user and self.imap_pass):
            raise RuntimeError(
                "Email OTP retrieval is not configured. Add an [email] section to "
                "settings.cfg (see settings-sample.cfg) or set QA_EMAIL_IMAP_USER "
                "and QA_EMAIL_IMAP_PASSWORD. Gmail needs an app password with IMAP "
                "enabled, not the account password."
            )

    def address_for(self, tag, env=None):
        """A unique plus-addressed variant of the QA mailbox.

        e.g. address_for("se10", env="stage") -> qa+stage-se10-1788875825@...

        Each run needs its own address: an address already bound to another
        account cannot be reused, and a stale one would collide. They all deliver
        to the same inbox, so the env prefix is what makes a message in that inbox
        attributable to an environment at a glance - staging and prod addresses
        must never look alike.
        """
        local, _, domain = self.base_address.partition("@")
        local = local.partition("+")[0]
        prefix = f"{env}-" if env else ""
        return f"{local}+{prefix}{tag}-{int(time.time())}@{domain}"

    def find_previous_address(self, tag, env=None, before=None):
        """The most recent address this mailbox has seen for a given tag.

        Used to find an address that a PREVIOUS run bound to an account, so a
        test needing "an address someone else already uses" can seed itself
        rather than carrying a hardcoded value that rots when an environment is
        wiped.

        The tag matters: it says which test created the address, and therefore
        whether the address is actually bound to an account. An address from a
        flow that never completes registration is verified but NOT bound - the
        server holds it only on a configuration session, so it collides with
        nothing.

        `before` is a unix timestamp; messages at or after it are ignored, so a
        run never picks up the address it just created itself. Returns None when
        the mailbox has no such address, which callers should treat as "not
        seeded on this environment yet".
        """
        local, _, domain = self.base_address.partition("@")
        local = local.partition("+")[0]
        prefix = f"{local}+{env}-{tag}-" if env else f"{local}+{tag}-"

        with MailBox(self.imap_host).login(self.imap_user, self.imap_pass, "INBOX") as mailbox:
            messages = mailbox.fetch(
                AND(subject=OTP_SUBJECT), reverse=True, limit=60, mark_seen=False
            )
            for message in messages:
                if before and message.date and message.date.timestamp() >= before:
                    continue
                for recipient in message.to:
                    if recipient.lower().startswith(prefix.lower()):
                        return recipient
        return None

    def _find_code(self, target_email, not_before):
        """Newest matching code for target_email, or None.

        Filtering on subject and today's date keeps the search cheap; the
        recipient is then checked against the message itself, because the mailbox
        receives codes for every test running against every environment.
        """
        candidates = []
        with MailBox(self.imap_host).login(self.imap_user, self.imap_pass, "INBOX") as mailbox:
            messages = mailbox.fetch(
                AND(subject=OTP_SUBJECT, date_gte=datetime.date.today()),
                reverse=True,
                mark_seen=False,
            )
            for message in messages:
                if not_before and message.date and message.date.timestamp() < not_before:
                    # Too old for this request - skip it, but keep looking.
                    #
                    # Do NOT stop here. imap_tools' reverse=True reverses UID
                    # order, not date order, and the two differ in this mailbox -
                    # observed 07:38, 07:50, 07:48 in a single fetch. Treating the
                    # first old message as a terminator made the reader miss codes
                    # that had genuinely arrived, which looked exactly like the
                    # server failing to send.
                    continue
                recipients = " ".join(message.to).lower()
                body = message.text or message.html or ""
                if target_email.lower() not in recipients and target_email.lower() not in body.lower():
                    continue
                code = extract_otp(body)
                if code and message.date:
                    candidates.append((message.date, code))

        if not candidates:
            return None
        # Newest by DATE, not by fetch order.
        return max(candidates, key=lambda pair: pair[0])[1]

    def get_verification_code(
        self,
        target_email,
        not_before=None,
        timeout=DEFAULT_TIMEOUT_SECONDS,
        poll_interval=DEFAULT_POLL_SECONDS,
    ):
        """Wait for and return the code sent to target_email.

        not_before is a unix timestamp; older messages are ignored. Pass the time
        just before the app was asked to send the code. Without it a stale code
        from an earlier run would be returned - these addresses are reused, so the
        mailbox fills with codes that were each valid at the time, and the test
        would fail on one that looks perfectly correct.

        Raises TimeoutError if nothing arrives in time.
        """
        if not_before is None:
            not_before = time.time()
        deadline = time.time() + timeout
        while time.time() < deadline:
            code = self._find_code(target_email, not_before)
            if code:
                return code
            time.sleep(poll_interval)
        raise TimeoutError(
            f"No PersonalID verification code for {target_email} within {timeout}s. "
            "Check the mailbox credentials and that the address is one the server "
            "will actually send to."
        )
