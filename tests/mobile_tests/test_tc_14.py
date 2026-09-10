import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number


@allure.feature("PID & CONNECT")
@allure.story("Email during account recovery")
@allure.tag("RE_03", "RE_04")
@allure.description("""
 RE_03 - verifying an email during recovery completes recovery
 RE_04 - an account that already has a verified email is not asked again

 One test in this order because RE_04 needs an account that HAS a verified
 email, and RE_03 is what creates that state. Running them together also makes
 the pair meaningful: the SAME account is offered the email step on the first
 recovery and not on the second, which is the behaviour under test.

 Self-contained - no fixture accounts. Forget PersonalID clears the account only
 on the device, so this registers its own account, forgets it, and recovers it
 twice.

 Appium rather than Maestro because RE_03 needs a real emailed code.
 """)
@pytest.mark.mobile
def test_14_recovery_email_verification(mobile_driver, settings, config):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    mailbox = EmailOtpReader(settings)
    env = config.env.lower()

    phone_number = fresh_phone_number()
    backup_code = fresh_backup_code()
    username = f"QA Recovery {phone_number}"
    email_address = mailbox.address_for("re03", env=env)

    with allure.step("Register an account with no email, and complete signup"):
        home.open_side_menu()
        home.click_signup()
        pid.start_signup("+7426", phone_number)
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()
        pid.demo_user_confirm()
        pid.enter_name(username)
        assert pid.is_registration_backup_screen(), (
            f"+7426 {phone_number} already has an account - this ran recovery, "
            "not registration. Re-run to get a new number."
        )
        pid.set_backup_code(backup_code)
        pid.skip_email_if_present()
        pid.save_photo_and_finish()

    with allure.step("Forget the account, then recover it"):
        home.sign_out()
        home.open_side_menu()
        home.click_signup()
        pid.start_signup("+7426", phone_number)
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()
        pid.demo_user_confirm()
        pid.enter_name(username)
        assert not pid.is_registration_backup_screen(), (
            "Expected the recovery backup code screen (one field), but the "
            "registration screen appeared - the account was not found."
        )

    # ------------------------------------------------------------------ RE_03
    with allure.step("RE_03: the email step is offered, and an address is verified"):
        pid.enter_backup_code_only(backup_code)
        pid.wait_for_email_step()
        requested_at = time.time()
        pid.enter_email(email_address)
        try:
            code = mailbox.get_verification_code(email_address, not_before=requested_at)
        except TimeoutError:
            # A code can take longer to become visible over IMAP than the
            # poll window allows - see test_tc_11 for the full note. Not a
            # delivery failure.
            pid.resend_email_otp()
            code = mailbox.get_verification_code(email_address, not_before=time.time())
        pid.enter_email_otp(code)
        # Recovery completes here - NOT photo capture, which is where the
        # registration journey goes. The two share this email screen and diverge
        # only afterwards, so the distinction is the point of the case.
        pid.verify_recovery_success()

    # ------------------------------------------------------------------ RE_04
    with allure.step("RE_04: recovering again does not ask for an email"):
        home.sign_out()
        home.open_side_menu()
        home.click_signup()
        pid.start_signup("+7426", phone_number)
        pid.click_configure_fingerprint()
        pid.handle_fingerprint_auth()
        pid.demo_user_confirm()
        pid.enter_name(username)
        pid.enter_backup_code_only(backup_code)
        # The server returns the stored address on confirm_backup_code, so the
        # app skips straight to recovery success without offering the step.
        assert not pid.is_email_step_shown(), (
            "The email step was offered to an account that already has a "
            "verified email - it should have been skipped."
        )
        pid.verify_recovery_success()
