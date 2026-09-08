"""Generation of unique, demo-safe test data for PersonalID registration.

Numbering convention (agreed 2026-09-08, announced to the team): automation
registers accounts on country code +7426 with subscriber numbers in the 129xxxx
block. Two separate reasons for that shape:

* +7426 is ConnectID's TEST_NUMBER_PREFIX, which makes the user a demo user.
  Demo users bypass SMS and are marked phone-validated at session creation -
  necessary because the qaAutomation build never shows the phone OTP screen, and
  the email OTP endpoints reject an unvalidated ConfigurationSession with 403.
* The 129 block keeps automation-created accounts identifiable at a glance, so
  they can be audited or bulk-deactivated later without anyone having to work out
  whether a given account was someone's manual test.

Registration also needs a number with no existing account: an existing one sends
the backup code screen down the recovery path, which looks similar and behaves
differently. Callers should assert they are on the registration screen - see
PersonalIDPage.is_registration_backup_screen.
"""

import itertools
import time

AUTOMATION_BLOCK = "129"

# Committed to test_data for the existing recovery cases.
RESERVED_PHONE_NUMBERS = frozenset({"7426000", "7426005"})

_counter = itertools.count()


def fresh_phone_number():
    """A 7-digit subscriber number in the automation block, unique per call."""
    while True:
        tail = f"{(int(time.time()) + next(_counter)) % 10000:04d}"
        number = f"{AUTOMATION_BLOCK}{tail}"
        if number not in RESERVED_PHONE_NUMBERS:
            return number


def fresh_backup_code():
    """A 6-digit backup code. Value is arbitrary; it only has to be consistent."""
    return f"{int(time.time()) % 1000000:06d}"
