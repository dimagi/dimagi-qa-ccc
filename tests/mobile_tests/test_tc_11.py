import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number


@allure.feature("PID & CONNECT")
@allure.story("Email verification during signup")
@allure.tag("SE_10")
@allure.description("""
 SE_10 - a new PersonalID user adds an email during signup and verifies it with
 the real code sent to that address.

 This lives in the Appium suite rather than Maestro on purpose. Reading the code
 requires pausing mid-session to poll a mailbox, which only works where Python
 holds the session - the same approach dimagi-qa-sureadhere uses for its
 password-reset tests. Maestro flows run remotely as declarative YAML and cannot
 call back into Python, so the rest of the signup email cases (SE_01-SE_09,
 SE_11, SE_12) are Maestro and this one is not.

 Requires:
 - the email_otp_verification switch active on ConnectID for the environment
 - an [email] section in settings.cfg (see settings-sample.cfg)
 """)
@pytest.mark.mobile
@pytest.mark.skip(
    reason="SE_10 needs the unreleased 2.65 build - re-enable when 2.65 ships. "
    "See the comment below."
)
# SKIPPED, 2026-09-10: this case passes, on prod and on staging, but only
# against the 2.64+ signup email step as built in the unreleased 2.65 APK that
# was used to write it. Keeping it running would mean pinning the whole mobile
# suite to 2.65, and the rest of the suite is the stable regression set - it
# should stay on the released build.
#
# Nothing else depends on this test. It registers its own account from a cleared
# app and shares no fixture or account with any other case, so skipping it
# changes no other test's starting state.
#
# TO RE-ENABLE once 2.65 is released: delete the skip marker above, and add
# signup_email_add.yaml / signup_email_verify.yaml back to TEST_FLOWS in
# maestro_mobile/scripts/run_on_browserstack.py (SE_08 and SE_09, same gap).
def test_11_signup_email_verification(mobile_driver, settings, config):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    mailbox = EmailOtpReader(settings)
    env = config.env.lower()

    phone_number = fresh_phone_number()
    backup_code = fresh_backup_code()
    username = f"QA Email {phone_number}"
    # A unique address per run: an address already bound to another account
    # cannot be reused. All variants deliver to the same inbox, so the
    # environment is baked into the address - otherwise a staging message and a
    # prod message are indistinguishable in that shared mailbox.
    email_address = mailbox.address_for("se10", env=env)

    with allure.step("Click on Sign In / Register"):
        home.open_side_menu()
        home.click_signup()

    with allure.step(f"Register a new demo number (+7426 {phone_number})"):
        pid.start_signup("+7426", phone_number)
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()
        pid.demo_user_confirm()

    with allure.step("Enter the account name"):
        pid.enter_name(username)

    with allure.step("Confirm this is registration, not recovery"):
        # A number that already had an account reaches a near-identical screen by
        # the same route. Fail here rather than silently testing recovery.
        assert pid.is_registration_backup_screen(), (
            f"+7426 {phone_number} already has an account - this ran the recovery "
            "path, not registration. Re-run to get a new number."
        )

    with allure.step("Set the backup code"):
        pid.set_backup_code(backup_code)

    # Record the time before the app is asked to send, so a code left in the
    # mailbox by an earlier run is never mistaken for this one.
    requested_at = time.time()

    with allure.step(f"Enter the email address and continue ({email_address})"):
        pid.enter_email(email_address)

    with allure.step("Read the verification code from the QA mailbox"):
        # A code can take longer to become visible over IMAP than the poll
        # window allows - the message carries an in-window Date header but is
        # not yet fetchable. Seen on staging 2026-09-10, where both the original
        # and the resent code were in the mailbox afterwards, timestamped inside
        # the windows that had just failed to find them.
        #
        # This is NOT the product failing to send. An earlier version of this
        # comment claimed that, and it was wrong: the cause was a date-ordering
        # bug in EmailOtpReader, since fixed. Every email was delivered.
        #
        # Resending is what a real user would do, and it buys another window.
        try:
            code = mailbox.get_verification_code(email_address, not_before=requested_at)
        except TimeoutError:
            allure.attach(
                "No code arrived for the first request; using Resend.",
                "first attempt", allure.attachment_type.TEXT,
            )
            pid.resend_email_otp()
            resent_at = time.time()
            code = mailbox.get_verification_code(email_address, not_before=resent_at)
        allure.attach(code, "verification code", allure.attachment_type.TEXT)

    with allure.step("Enter the code and confirm signup continues to photo capture"):
        pid.enter_email_otp(code)
        # Registration shows no "Email Added" dialog - that belongs to the
        # EXISTING_USER workflow in Manage Profile. Here the app advances to photo
        # capture, and reaching it is the proof the server accepted the code.
        pid.verify_photo_capture_screen(username)
