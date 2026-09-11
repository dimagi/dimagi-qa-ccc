import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")


class ManageProfilePage(BasePage):
    """Manage Profile: the Profile screen and its Edit Profile form.

    Only the cases that need a real emailed code live here (MP_09, MP_13, MP_19);
    the rest of Manage Profile is covered by the Maestro flows. See the spec for
    why those three cannot be Maestro.
    """

    DRAWER_LINK = locators.get("manage_profile", "drawer_manage_profile_link")

    PROFILE_NAME_HEADER = locators.get("manage_profile", "profile_name_header")
    VALUE_NAME = locators.get("manage_profile", "profile_value_name")
    VALUE_PHONE = locators.get("manage_profile", "profile_value_phone")
    VALUE_EMAIL = locators.get("manage_profile", "profile_value_email")
    FORGET_BTN = locators.get("manage_profile", "forget_account_btn")
    EDIT_MENU = locators.get("manage_profile", "edit_profile_menu")

    NAME_INPUT = locators.get("manage_profile", "edit_name_input")
    PHONE_INPUT = locators.get("manage_profile", "edit_phone_input")
    EMAIL_INPUT = locators.get("manage_profile", "edit_email_input")
    SAVE_BTN = locators.get("manage_profile", "edit_save_btn")
    CANCEL_BTN = locators.get("manage_profile", "edit_cancel_btn")
    OTP_CONFIRM_SEND = locators.get("manage_profile", "otp_confirm_send")

    def open_from_drawer(self):
        """Open Manage Profile. Assumes the drawer is already open."""
        self.wait_for_element(self.DRAWER_LINK)
        self.click_element(self.DRAWER_LINK)
        self.wait_for_element(self.VALUE_NAME)

    def open_edit(self):
        self.wait_for_element(self.EDIT_MENU)
        self.click_element(self.EDIT_MENU)
        self.wait_for_element(self.NAME_INPUT)

    def clear_email(self):
        """Empty the email field.

        Cleared with the cursor at the end: clear() on the element rather than a
        tap-then-erase, because a tap lands the cursor where it hits and erasing
        backwards from mid-text leaves a tail.
        """
        field = self.wait_for_element(self.EMAIL_INPUT)
        field.clear()

    def set_email(self, address):
        self.clear_email()
        self.wait_for_element(self.EMAIL_INPUT).send_keys(address)

    def save(self):
        self.click_when_enabled(self.SAVE_BTN)

    def is_save_enabled(self):
        return self.wait_for_element(self.SAVE_BTN).is_enabled()

    def confirm_send_code(self):
        """Accept the 'Verify your new email' prompt and go to the code screen."""
        self.wait_for_element(self.OTP_CONFIRM_SEND)
        self.click_element(self.OTP_CONFIRM_SEND)

    def profile_email(self):
        return self.get_text(self.VALUE_EMAIL)

    def profile_name(self):
        return self.get_text(self.VALUE_NAME)
