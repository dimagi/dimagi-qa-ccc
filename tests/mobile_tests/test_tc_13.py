import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.manage_profile_page import ManageProfilePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader
from utils.test_data_gen import fresh_backup_code, fresh_phone_number


@allure.feature("PID & CONNECT")
@allure.story("Manage Profile - email changes")
@allure.tag("MP_19")
@allure.description("""
 MP_19 - changing the email to one another account already uses is refused.

 Separate from test_tc_12 on purpose. It needs no pre-existing email, and when
 it lived inside that test a skip here discarded the MP_13 and MP_09 results
 that had already passed - pytest.skip mid-test abandons the whole test.

 The address it needs is one a PREVIOUS MP_13 run bound to a real account on
 this environment, found from the mailbox rather than hardcoded. Only MP_13
 binds an address: it completes the account first, then adds the email to a real
 user. An address from SE_10 is verified but NOT bound, because that flow ends at
 photo capture and never creates the account.
 """)
@pytest.mark.mobile
def test_13_manage_profile_email_already_used(mobile_driver, settings, config):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    profile = ManageProfilePage(mobile_driver)
    mailbox = EmailOtpReader(settings)
    env = config.env.lower()

    already_used = mailbox.find_previous_address("mp13", env=env, before=time.time())
    if not already_used:
        pytest.skip(
            f"No address bound by an MP_13 run on {env!r} yet - run test_tc_12 "
            "there once and this will have data."
        )

    phone_number = fresh_phone_number()
    backup_code = fresh_backup_code()
    username = f"QA MP19 {phone_number}"

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
        pid.skip_email_if_present()
        pid.save_photo_and_finish()

    with allure.step(f"Try to claim {already_used}, which another account holds"):
        home.open_side_menu()
        profile.open_from_drawer()
        profile.open_edit()
        profile.set_email(already_used)
        requested_at = time.time()
        profile.save()
        profile.confirm_send_code()

    with allure.step("Enter the code and confirm the address is refused"):
        # The rejection happens when the verified address is written to this
        # user, so a correct code has to be entered first. The code goes to an
        # address in our own mailbox, so it is readable.
        code = mailbox.get_verification_code(already_used, not_before=requested_at)
        pid.enter_email_otp(code)
        pid.verify_email_already_in_use()
