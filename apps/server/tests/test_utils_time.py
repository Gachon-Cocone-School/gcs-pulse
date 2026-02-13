import pytest
from datetime import datetime, date
from fastapi import HTTPException
from app.utils_time import validate_snippet_date, validate_snippet_week, current_business_key

def test_validate_snippet_date():
    # 2024-02-13 is a Tuesday
    yesterday = date(2024, 2, 12)
    today = date(2024, 2, 13)
    tomorrow = date(2024, 2, 14)

    # Case 1: Before 9:00 AM -> Only yesterday is allowed
    now_before = datetime(2024, 2, 13, 8, 59, 59)
    validate_snippet_date(yesterday, now=now_before)

    with pytest.raises(HTTPException) as exc:
        validate_snippet_date(today, now=now_before)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_snippet_date(tomorrow, now=now_before)
    assert exc.value.status_code == 400

    # Case 2: After 9:00 AM -> Only today is allowed
    now_after = datetime(2024, 2, 13, 9, 0, 0)
    validate_snippet_date(today, now=now_after)

    with pytest.raises(HTTPException) as exc:
        validate_snippet_date(yesterday, now=now_after)
    assert exc.value.status_code == 400

    with pytest.raises(HTTPException) as exc:
        validate_snippet_date(tomorrow, now=now_after)
    assert exc.value.status_code == 400

def test_validate_snippet_week():
    # 2024-02-12 is a Monday
    last_week_start = date(2024, 2, 5)
    this_week_start = date(2024, 2, 12)
    next_week_start = date(2024, 2, 19)

    # Case 1: Before Monday 9:00 AM -> Only last week is allowed
    now_before = datetime(2024, 2, 12, 8, 59, 59)
    validate_snippet_week(last_week_start, now=now_before)

    with pytest.raises(HTTPException) as exc:
        validate_snippet_week(this_week_start, now=now_before)
    assert exc.value.status_code == 400

    # Case 2: After Monday 9:00 AM -> Only this week is allowed
    now_after = datetime(2024, 2, 12, 9, 0, 0)
    validate_snippet_week(this_week_start, now=now_after)

    with pytest.raises(HTTPException) as exc:
        validate_snippet_week(last_week_start, now=now_after)
    assert exc.value.status_code == 400

    # Case 3: Middle of the week (Wednesday) -> Only this week is allowed
    now_mid = datetime(2024, 2, 14, 12, 0, 0)
    validate_snippet_week(this_week_start, now=now_mid)

    with pytest.raises(HTTPException) as exc:
        validate_snippet_week(last_week_start, now=now_mid)
    assert exc.value.status_code == 400


def test_current_business_key_daily_before_cutoff():
    now = datetime(2024, 2, 13, 8, 59, 59)
    assert current_business_key("daily", now) == date(2024, 2, 12)


def test_current_business_key_daily_after_cutoff():
    now = datetime(2024, 2, 13, 9, 0, 0)
    assert current_business_key("daily", now) == date(2024, 2, 13)


def test_current_business_key_weekly_before_monday_cutoff():
    now = datetime(2024, 2, 12, 8, 59, 59)
    assert current_business_key("weekly", now) == date(2024, 2, 5)


def test_current_business_key_weekly_after_monday_cutoff():
    now = datetime(2024, 2, 12, 9, 0, 0)
    assert current_business_key("weekly", now) == date(2024, 2, 12)


def test_current_business_key_raises_on_invalid_kind():
    with pytest.raises(ValueError):
        current_business_key("monthly", datetime(2024, 2, 13, 12, 0, 0))
