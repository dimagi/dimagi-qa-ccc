import time

import allure
import pytest

from pages.mobile_pages.home_page import HomePage
from pages.mobile_pages.manage_profile_page import ManageProfilePage
from pages.mobile_pages.personal_id_page import PersonalIDPage
from utils.email_otp import EmailOtpReader


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
def test_13_manage_profile_email_already_used(mobile_driver, settings, config, test_data):
    pid = PersonalIDPage(mobile_driver)
    home = HomePage(mobile_driver)
    profile = ManageProfilePage(mobile_driver)
    mailbox = EmailOtpReader(settings)
    env = config.env.lower()

    # Deliberately ignore anything bound in the last few minutes. test_tc_12 runs
    # immediately before this in a full suite run and binds a fresh address, and
    # picking that one races two things at once: the server finishing the binding,
    # and the verification mail becoming visible over IMAP. That is exactly how
    # this failed on prod 2026-09-15 - a 180s timeout on an address bound ten
    # minutes earlier, which then passed on retry. An older address is settled.
    SETTLE_SECONDS = 300
    already_used = mailbox.find_previous_address(
        "mp13", env=env, before=time.time() - SETTLE_SECONDS
    )
    if not already_used:
        pytest.skip(
            f"No settled address bound by an MP_13 run on {env!r} - run test_tc_12 "
            f"there, wait {SETTLE_SECONDS // 60} minutes, and this will have data."
        )

    # Recovers a fixture rather than registering: registration cannot complete on
    # 2.64, and this case does not need a new account - only one that is NOT the
    # account holding `already_used`.
    #
    # The rename fixture, deliberately. Not the email fixture, which is the very
    # account that bound the address MP_19 tries to claim. Not the shared profile
    # fixture either: MP_19 leaves no email behind (the claim is refused), but if
    # it ever partially succeeded it would break MP_03's "no address rendered"
    # assertion permanently. The rename fixture's only constraint is its name,
    # which this case never touches.
    fixture = test_data.get_for_env("MAESTRO_PROFILE_RENAME_FIXTURE", env)

    with allure.step("Recover the fixture account"):
        home.open_side_menu()
        home.click_signup()
        pid.recover_existing_account(
            fixture["country_code"], fixture["phone_number"],
            fixture["username"], fixture["backup_code"],
        )
        pid.skip_email_if_present()
        pid.dismiss_recovery_dialog()

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
