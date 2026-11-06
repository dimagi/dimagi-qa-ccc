import pytest

from flows.ldvp_values import assert_percent


def test_percent_accepts_connects_decimal_form():
    # Connect's Learn tab shows "100.0%", not "100%".
    assert_percent("100.0%", 100, "Modules completed")
    assert_percent(" 100% ", 100, "Modules completed")


def test_percent_rejects_partial_progress():
    with pytest.raises(AssertionError, match="50.0%"):
        assert_percent("50.0%", 100, "Modules completed")


def test_percent_treats_an_empty_cell_as_not_yet():
    # Before Connect records anything the cell can be a dash; the web wait must
    # keep polling (AssertionError), not crash on a ValueError.
    with pytest.raises(AssertionError):
        assert_percent("—", 100, "Modules completed")
