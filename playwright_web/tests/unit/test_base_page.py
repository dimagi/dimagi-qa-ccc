from datetime import datetime, timedelta

from pages.base_page import BasePage


def test_generate_date_range_returns_dd_mm_yyyy_format():
    base = BasePage(page=None)
    start, end = base.generate_date_range(7)

    today = datetime.today()
    expected_start = (today + timedelta(days=2)).strftime("%d-%m-%Y")
    expected_end = (today + timedelta(days=2) + timedelta(days=7)).strftime("%d-%m-%Y")

    assert start == expected_start
    assert end == expected_end
