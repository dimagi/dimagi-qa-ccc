import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.manage_profile_page import ManageProfilePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number

# Addresses genuinely bound to another PersonalID account, for MP_19.
#
# It has to be an address added through MANAGE PROFILE on a completed account -
# i.e. one created by an earlier MP_13 run. An address from SE_10 does NOT work,
# even though SE_10 verifies it: that flow ends at photo capture by design, so
# complete_profile never runs, no ConnectUser is created, and the address only
# ever sits on the ConfigurationSession as verified_email. The unique constraint
# is on ConnectUser.email where is_active=True, so with no user there is nothing
# to collide with and the server accepts the address happily.
#
# Per environment: an address is only taken on the server holding that account.
#
# To add one for a new environment, run this test there once. MP_13 will bind a
# fresh +<env>-mp13-<ts> address; put it here and MP_19 works from then on.
ALREADY_USED_EMAIL_BY_ENV = {
    "prod": "automation.user.commcarehq+prod-mp13-1788971053@gmail.com",
    # stage: none yet - this test has not run there. MP_19 skips until it has.
}


@allure.feature("PID & CONNECT")
@allure.story("Manage Profile - email changes")
@allure.tag("MP_13", "MP_09", "MP_19")
@allure.description("""
 The Manage Profile cases that need a real emailed verification code.

 MP_13 - changing the email and entering the correct code updates the account
 MP_09 - an existing email cannot then be removed
 MP_19 - it cannot be changed to an address another account already uses

 Deliberately one test in this order: all three need an account that HAS a
 verified email, and MP_13 is what creates that state. Splitting them would mean
 three separate registrations plus three code round-trips for no extra coverage.

 In the Appium suite rather than Maestro because reading the mailbox mid-session
 needs Python holding the session. The rest of Manage Profile (MP_01-MP_08,
 MP_10-MP_12, MP_14-MP_18) is covered by the Maestro flows.
 """)
@pytest.mark.mobile
def test_12_manage_profile_email(mobile_driver, settings, config):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    profile = ManageProfilePage(mobile_driver)
    mailbox = EmailOtpReader(settings)
    env = config.env.lower()

    phone_number = fresh_phone_number()
    backup_code = fresh_backup_code()
    username = f"QA MP {phone_number}"
    new_email = mailbox.address_for("mp13", env=env)

    with allure.step("Register a new account and complete signup"):
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
        # Skip the signup email step; the point of this test is adding one later
        # through Manage Profile.
        pid.skip_email_if_present()
        pid.save_photo_and_finish()

    with allure.step("Open Manage Profile"):
        home.open_side_menu()
        profile.open_from_drawer()

    # ------------------------------------------------------------------ MP_13
    with allure.step(f"MP_13: change the email to {new_email}"):
        profile.open_edit()
        profile.set_email(new_email)
        requested_at = time.time()
        profile.save()
        profile.confirm_send_code()

    with allure.step("MP_13: read the code and enter it"):
        try:
            code = mailbox.get_verification_code(new_email, not_before=requested_at)
        except TimeoutError:
            # The OTP email is not always delivered even when the API reports
            # success - see test_tc_11 for the same fallback.
            pid.resend_email_otp()
            code = mailbox.get_verification_code(new_email, not_before=time.time())
        pid.enter_email_otp(code)

    with allure.step("MP_13: the change is confirmed and shown on Profile"):
        pid.verify_email_added()
        assert new_email in profile.profile_email(), (
            f"Profile should show {new_email}, got {profile.profile_email()!r}"
        )

    # ------------------------------------------------------------------ MP_09
    with allure.step("MP_09: an existing email cannot be removed"):
        profile.open_edit()
        profile.clear_email()
        assert not profile.is_save_enabled(), (
            "Save should stay disabled when clearing an address the account "
            "already has - clearing an existing email is not allowed."
        )
        # Restore the address so the form is clean for MP_19.
        profile.set_email(new_email)

    # ------------------------------------------------------------------ MP_19
    with allure.step("MP_19: an address another account uses is refused"):
        already_used = ALREADY_USED_EMAIL_BY_ENV.get(env)
        if not already_used:
            pytest.skip(f"No known already-verified address for env {env!r}")
        profile.set_email(already_used)
        taken_requested_at = time.time()
        profile.save()
        profile.confirm_send_code()
        # The rejection happens when the verified address is written to this
        # user, so a correct code has to be entered first. The code goes to an
        # address in our own mailbox, so it is readable.
        taken_code = mailbox.get_verification_code(
            already_used, not_before=taken_requested_at
        )
        pid.enter_email_otp(taken_code)
        pid.verify_email_already_in_use()
