from datetime import datetime, timedelta

from pages.base_page import BasePage


def _fmt(d):
    return d.strftime("%d-%m-%Y")


def test_date_range_can_start_today():
    # CCCT-2670: an opportunity starting in two days says "The job has not started
    # yet" and earns nothing, so a same-day end-to-end run needs it to start today.
    today = datetime.today()
    start, end = BasePage.generate_date_range(None, 30, start_offset_days=0)
    assert start == _fmt(today)
    assert end == _fmt(today + timedelta(days=30))


def test_date_range_default_still_starts_in_two_days():
    # The OLP regression and program setup rely on the existing default.
    today = datetime.today()
    start, _ = BasePage.generate_date_range(None, 7)
    assert start == _fmt(today + timedelta(days=2))
