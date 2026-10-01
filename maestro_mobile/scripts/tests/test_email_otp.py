"""Unit tests for the email OTP helper.

Only the pure parts are covered - extracting a code from a body. The IMAP
plumbing is left to integration use, since faking an IMAP server would test the
fake rather than the mailbox.
"""

from utils.email_otp import extract_otp


def test_extract_otp_finds_a_six_digit_code():
    assert extract_otp("Your PersonalID code is 481920. It expires shortly.") == "481920"


def test_extract_otp_ignores_longer_digit_runs():
    # Reference numbers and ids must not be mistaken for the code.
    assert extract_otp("Ref 1234567890, code 481920, end") == "481920"


def test_extract_otp_ignores_shorter_digit_runs():
    assert extract_otp("Code expires in 10 minutes: 481920") == "481920"


def test_extract_otp_takes_the_first_code_when_several_appear():
    assert extract_otp("481920 was sent, not 123456") == "481920"


def test_extract_otp_returns_none_when_absent():
    assert extract_otp("No code in this message at all") is None


def test_extract_otp_returns_none_for_empty_body():
    assert extract_otp("") is None


def test_extract_otp_returns_none_for_none_body():
    assert extract_otp(None) is None


def test_extract_otp_ignores_the_expiry_minutes_in_the_real_body():
    # The real PersonalID email carries two numbers - the code and the expiry.
    body = "Your email verification code is: 481920\nThis code expires in 10 minutes."
    assert extract_otp(body) == "481920"
