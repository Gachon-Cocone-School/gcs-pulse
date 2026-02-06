from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta


DAILY_CUTOFF_HOUR = 9


def current_business_date(now: datetime) -> date:
    cutoff = datetime.combine(now.date(), time(hour=DAILY_CUTOFF_HOUR), tzinfo=now.tzinfo)
    if now < cutoff:
        return now.date() - timedelta(days=1)
    return now.date()


def week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def current_business_week_start(now: datetime) -> date:
    today = current_business_date(now)
    return week_start_monday(today)
