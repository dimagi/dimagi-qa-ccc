import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number


@allure.feature("PID & CONNECT")
@allure.story("Email during account recovery")
@allure.tag("RE_03")
@allure.description("""
 RE_03 - verifying an email during recovery completes recovery.

 Needs an account with NO verified email, because the case is that the email
 step is offered - the server only offers it when it holds no verified address.
 The case then verifies one, which binds it permanently and cannot be undone
 (MP_09 is the case proving an existing address cannot be cleared).

 So the account is single-use and has to be registered per run, which is why
 this one is skipped while the suite runs on 2.64 - see the skip marker.
 """)
@pytest.mark.mobile
@pytest.mark.skip(
    reason="RE_03 needs a newly registered account, which cannot be automated on "
    "2.64 - re-enable when 2.65 ships. See the comment below."
)
# SKIPPED, 2026-09-15: unlike the other Manage Profile and recovery cases, this
# one cannot be moved onto a long-lived fixture. It asserts the email step is
# OFFERED, which the server does only for an account with no verified email, and
# the case's own action verifies one - permanently, since a bound address cannot
# be cleared. The fixture would work once and fail every run after.
#
# That leaves registering per run, and an automated registration cannot complete
# on 2.64: the account is not created until the photo is saved, Save Photo is
# enabled only by a real camera capture, and the qaAutomation placeholder photo
# landed in commcare-android 1e14ed79b (27-Aug-2026), after 2.64 was cut.
#
# TO RE-ENABLE once 2.65 ships: delete the skip marker. Nothing else needs
# changing - the test below still registers its own account, which works there.
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


@allure.feature("PID & CONNECT")
@allure.story("Email during account recovery")
@allure.tag("RE_04")
@allure.description("""
 RE_04 - an account that already has a verified email is not asked for one again.

 Split out from RE_03 so it can run on 2.64. RE_03 needs an account WITHOUT a
 verified email and has to register one per run; RE_04 needs the opposite - an
 account that HAS one - which a long-lived fixture provides, so it needs no
 registration and no photo.

 It recovers MAESTRO_PROFILE_EMAIL_FIXTURE, the account test_tc_12 (MP_13) binds
 an address to. Sharing is deliberate: RE_04 only cares that SOME verified
 address exists, not which, and it changes nothing - so the two tests can run in
 either order.
 """)
@pytest.mark.mobile
def test_14b_recovery_skips_email_when_already_verified(mobile_driver, config, test_data):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    env = config.env.lower()

    fixture = test_data.get_for_env("MAESTRO_PROFILE_EMAIL_FIXTURE", env)

    with allure.step("Recover an account that already has a verified email"):
        home.open_side_menu()
        home.click_signup()
        pid.recover_existing_account(
            fixture["country_code"], fixture["phone_number"],
            fixture["username"], fixture["backup_code"],
        )

    with allure.step("RE_04: the email step is not offered"):
        # The server returns the stored address on confirm_backup_code, so the
        # app goes straight to recovery success without offering the step.
        assert not pid.is_email_step_shown(), (
            "The email step was offered to an account that already has a "
            "verified email - it should have been skipped. If this fixture has "
            "never had MP_13 run against it, seed it by running test_tc_12 on "
            "this environment first."
        )
        pid.verify_recovery_success()
