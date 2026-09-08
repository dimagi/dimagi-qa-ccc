import re
import time

from pages.mobile_pages.base_page import BasePage
from utils.helpers import LocatorLoader
from utils.utility import simulate_fingerprint

locators = LocatorLoader("locators/mobile_locators.yaml", platform="mobile")

class PersonalIDPage(BasePage):

    PHONE_INPUT = locators.get("login_page", "phone_input")
    CONTINUE_BTN = locators.get("login_page", "continue_btn")
    COUNTRY_CODE = locators.get("login_page", "country_code")
    TERMS_CHECKBOX = locators.get("login_page", "terms_checkbox")
    USE_FINGERPRINT_TXT = locators.get("login_page", "use_fingerprint_txt")
    CONFIGURE_FINGERPRINT_BTN = locators.get("login_page", "configure_fingerprint_btn")
    DEMO_USER_CONFIRM = locators.get("login_page", "demo_user_confirm")
    OK_BTN = locators.get("login_page", "ok_btn")
    NAME_INPUT = locators.get("login_page", "name_input")
    BACKUP_CODE_WELCOME_TEXT = locators.get("login_page", "backup_code_welcome_text")
    BACKUP_CODE_INPUT = locators.get("login_page", "backup_code_input")
    POPUP_MESSAGE_TXT = locators.get("login_page", "popup_msg_txt")
    WRONG_BACKUP_CODE_TXT = locators.get("login_page", "wrong_backup_code_txt")
    NETWORK_ERROR_TXT = locators.get("login_page", "network_connection_err_txt")
    PROGRESS_BAR = locators.get("login_page", "progress_bar")
    EMAIL_INPUT = locators.get("login_page", "email_input")
    EMAIL_SKIP_BTN = locators.get("login_page", "email_skip_btn")
    EMAIL_CONTINUE_BTN = locators.get("login_page", "email_continue_btn")
    EMAIL_ERROR_TXT = locators.get("login_page", "email_error_txt")
    EMAIL_SKIP_CONFIRM_YES = locators.get("login_page", "email_skip_confirm_yes")
    CONFIRM_CODE_INPUT = locators.get("login_page", "confirm_code_input")
    EMAIL_OTP_INPUT = locators.get("otp_page", "email_otp_input")
    EMAIL_VERIFY_DESCRIPTION = locators.get("otp_page", "email_verify_description")
    EMAIL_VERIFY_ERROR = locators.get("otp_page", "email_verify_error")
    EMAIL_RESEND_BTN = locators.get("otp_page", "email_resend_btn")
    EMAIL_RESEND_COUNTDOWN = locators.get("otp_page", "email_resend_countdown")
    PHOTO_CAPTURE_TITLE = locators.get("otp_page", "photo_capture_title")
    TAKE_PHOTO_BTN = locators.get("otp_page", "take_photo_btn")

    def enter_phone_number(self, phone_number):
        self.type_element(self.PHONE_INPUT, phone_number)

    def enter_country_code(self, country_code):
        self.type_element(self.COUNTRY_CODE, country_code)

    def accept_terms(self):
        self.click_element(self.TERMS_CHECKBOX)

    def continue_next(self):
        try:
            self.click_when_enabled(self.CONTINUE_BTN)
        except Exception as e:
            self.click_element(self.TERMS_CHECKBOX)
            time.sleep(1)
            self.click_element(self.TERMS_CHECKBOX)
            time.sleep(2)
            self.click_element(self.CONTINUE_BTN)

    def start_signup(self, country_code, phone_number, retries=3):
        self.enter_country_code(country_code)
        self.enter_phone_number(phone_number)
        time.sleep(2)
        self.accept_terms()
        time.sleep(2)
        self.continue_next()
        time.sleep(5)
        self.wait_for_element_to_disappear(self.PROGRESS_BAR)

        if self.is_displayed(self.NETWORK_ERROR_TXT):
            for attempt in range(retries):
                print(f"Network Error: attempt {attempt + 1}")
                time.sleep(2)
                self.continue_next()
                self.wait_for_element_to_disappear(self.PROGRESS_BAR)
                if not self.is_displayed(self.NETWORK_ERROR_TXT):
                    break

            time.sleep(1)

    def click_configure_fingerprint(self):
        if self.BIOMETRIC_ENABLED:
            self.click_element(self.CONFIGURE_FINGERPRINT_BTN)
            time.sleep(2)

    def handle_fingerprint_auth(self):
        if self.BIOMETRIC_ENABLED:
            time.sleep(2)
            simulate_fingerprint(driver=self.driver, run_on=self.driver.run_on)

    def demo_user_confirm(self):
        if self.BIOMETRIC_ENABLED:
            time.sleep(2)
            self.wait_for_element(self.DEMO_USER_CONFIRM)
            self.click_element(self.OK_BTN)

    def enter_name(self, name):
        self.type_element(self.NAME_INPUT, name)
        time.sleep(2)
        self.click_when_enabled(self.CONTINUE_BTN)

    def verify_backup_code_screen(self, name):
        self.wait_for_element(self.BACKUP_CODE_WELCOME_TEXT)
        welcome_text = self.get_text(self.BACKUP_CODE_WELCOME_TEXT)
        assert re.match(
            rf"Welcome back\s+{name}",
            welcome_text
        )

    def skip_email_if_present(self):
        """Dismiss the optional email step that 2.64+ adds after the backup code.

        The step only appears when the email_otp_verification switch is active on
        ConnectID and the account has no verified email, so this is deliberately
        tolerant of it being absent. Returns True if it was skipped.
        """
        if not self.is_displayed(self.EMAIL_SKIP_BTN, timeout=15):
            return False
        self.click_element(self.EMAIL_SKIP_BTN)
        # Confirmation dialog - the buttons reuse the app-linking Yes/No strings.
        self.click_element(self.EMAIL_SKIP_CONFIRM_YES)
        return True

    def enter_backup_code(self, code):
        self.type_code(self.BACKUP_CODE_INPUT, code)
        self.click_when_enabled(self.CONTINUE_BTN)
        self.skip_email_if_present()
        self.wait_for_element(self.OK_BTN)
        self.click_element(self.OK_BTN)


    def set_backup_code(self, code):
        """Set a NEW account's backup code - fills both Code and Confirm Code.

        Registration shows two NumericCodeView fields; recovery shows only one.
        Use enter_backup_code for recovery, this for registration.
        """
        self.type_code(self.BACKUP_CODE_INPUT, code)
        self.type_code(self.CONFIRM_CODE_INPUT, code)
        self.click_when_enabled(self.CONTINUE_BTN)

    def is_registration_backup_screen(self):
        """True when this is the registration backup code screen, not recovery.

        An existing phone number silently routes to recovery, which reaches the
        same-looking screen through the same steps. The confirm field is the
        reliable tell: registration has it, recovery does not.
        """
        return self.is_displayed(self.CONFIRM_CODE_INPUT, timeout=20)

    def enter_email(self, address):
        """Type an address on the optional email step and continue."""
        self.type_element(self.EMAIL_INPUT, address)
        self.click_when_enabled(self.EMAIL_CONTINUE_BTN)

    def enter_email_otp(self, code):
        """Enter the emailed verification code.

        otp_code_view is a NumericCodeView and auto-submits on the sixth digit
        (setCodeCompleteListener), so there is no Verify button to press.
        """
        self.type_code(self.EMAIL_OTP_INPUT, code)

    def verify_email_added(self):
        """Confirm the 'Email Added' dialog - EXISTING_USER workflow only.

        Only shown to an already-signed-in user adding an email through Manage
        Profile. Registration has no such dialog; a successful verify goes
        straight to photo capture - use verify_photo_capture_screen for that.
        """
        self.wait_for_element(self.POPUP_MESSAGE_TXT)
        message = self.get_text(self.POPUP_MESSAGE_TXT)
        assert "Your email has been added successfully" in message, (
            f"Expected the email-added confirmation, got: {message!r}"
        )
        self.click_element(self.OK_BTN)

    def verify_photo_capture_screen(self, name):
        """Confirm registration reached photo capture, which greets the user.

        Reaching this screen is the observable proof that the email verification
        succeeded: the app only advances here once the server accepts the code.
        """
        self.wait_for_element(self.TAKE_PHOTO_BTN)
        title = self.get_text(self.PHOTO_CAPTURE_TITLE)
        assert name in title, f"Expected a welcome for {name!r}, got: {title!r}"

    def signin_existing_user(self, mobile_country_code, mobile_num, username, mobile_backup_code):
        self.start_signup(mobile_country_code, mobile_num)
        self.click_configure_fingerprint()
        self.handle_fingerprint_auth()
        self.demo_user_confirm()
        self.enter_name(username)
        self.enter_backup_code(mobile_backup_code)

    def verify_wrong_backup_code_err(self):
        self.type_code(self.BACKUP_CODE_INPUT, "123456")
        self.click_when_enabled(self.CONTINUE_BTN)
        toast = self.wait_for_element(self.WRONG_BACKUP_CODE_TXT)
        toast_text = toast.text
        print(toast_text)
        assert "You have entered the wrong Backup Code" in toast_text
        self.wait_for_element(self.OK_BTN)
        self.click_element(self.OK_BTN)


    def account_locked_error(self):
        self.wait_for_element(self.POPUP_MESSAGE_TXT)
        locked_txt = self.get_text(self.POPUP_MESSAGE_TXT)
        assert re.match(
            rf"Your account has been locked. Please contact support",
            locked_txt
        )
        self.click_element(self.OK_BTN)


