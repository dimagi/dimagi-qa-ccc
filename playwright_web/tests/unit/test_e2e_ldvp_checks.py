import pytest

from tests.test_e2e_ldvp import _assert_percent


def test_percent_accepts_connects_decimal_form():
    # Prod's Learn tab shows "100.0%" (2026-10-29), not "100%".
    _assert_percent("100.0%", 100, "Modules completed")
    _assert_percent(" 100% ", 100, "Modules completed")


def test_percent_rejects_partial_progress():
    with pytest.raises(AssertionError, match="50.0%"):
        _assert_percent("50.0%", 100, "Modules completed")


def test_percent_treats_an_empty_cell_as_not_yet():
    # Before Connect records anything the cell can be a dash; the web wait must
    # keep polling (AssertionError), not crash on a ValueError.
    with pytest.raises(AssertionError):
        _assert_percent("—", 100, "Modules completed")
