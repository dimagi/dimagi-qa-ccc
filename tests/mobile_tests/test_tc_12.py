import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.manage_profile_page import ManageProfilePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number

# MP_19 needs an address genuinely bound to ANOTHER account on this environment.
# It seeds itself from the mailbox rather than carrying a hardcoded value, which
# would rot whenever an environment is wiped - and rot silently, because an
# unknown address is simply accepted.
#
# It looks for an address a PREVIOUS run of this test bound via MP_13. The tag
# matters: only MP_13 binds an address, because it completes the account first
# and then adds the email to a real user. An address from SE_10 is verified but
# NOT bound - that flow ends at photo capture by design, so complete_profile
# never runs, no ConnectUser exists, and the unique constraint on
# ConnectUser.email (where is_active=True) has nothing to collide with.


@allure.feature("PID & CONNECT")
@allure.story("Manage Profile - email changes")
@allure.tag("MP_13", "MP_09")
@allure.description("""
 The Manage Profile cases that need a real emailed verification code.

 MP_13 - changing the email and entering the correct code updates the account
 MP_09 - an existing email cannot then be removed

 One test in this order because MP_09 needs an account that HAS a verified
 email, and MP_13 is what creates that state.

 MP_19 is separate (test_tc_13) even though it looks related: it needs no
 pre-existing email, and keeping it here meant a skip mid-test discarded the
 MP_13 and MP_09 results that had already passed.

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
    # Anything this run creates must not be mistaken for a previous run's
    # address when MP_19 goes looking for one.
    started_at = time.time()

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
            # A code can take longer to become visible over IMAP than the
            # poll window allows - see test_tc_11 for the full note. Not a
            # delivery failure.
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
