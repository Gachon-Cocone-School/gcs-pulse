from __future__ import annotations

from datetime import date, datetime, time, timedelta

from app.utils_time import (
    BUSINESS_TIMEZONE,
    current_business_date,
    current_business_week_start,
    to_business_timezone,
)


def resolve_default_target_date(now: datetime | None = None) -> date:
    now_kst = to_business_timezone(now or datetime.now(tz=BUSINESS_TIMEZONE))
    return current_business_date(now_kst) - timedelta(days=1)


def target_week_from_date(target_date: date) -> date:
    reference_now = datetime.combine(target_date, time(hour=12), tzinfo=BUSINESS_TIMEZONE)
    return current_business_week_start(reference_now)
