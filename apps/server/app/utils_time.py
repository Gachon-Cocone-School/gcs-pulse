from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException


DAILY_CUTOFF_HOUR = 9
BUSINESS_TIMEZONE = ZoneInfo("Asia/Seoul")


def to_business_timezone(now: datetime) -> datetime:
    if now.tzinfo is None:
        return now.replace(tzinfo=BUSINESS_TIMEZONE)
    return now.astimezone(BUSINESS_TIMEZONE)


def current_business_date(now: datetime) -> date:
    now_kst = to_business_timezone(now)
    cutoff = datetime.combine(now_kst.date(), time(hour=DAILY_CUTOFF_HOUR), tzinfo=BUSINESS_TIMEZONE)
    if now_kst < cutoff:
        return now_kst.date() - timedelta(days=1)
    return now_kst.date()


def week_start_monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def current_business_week_start(now: datetime) -> date:
    today = current_business_date(now)
    return week_start_monday(today)


def current_business_key(kind: str, now: datetime) -> date:
    if kind == "daily":
        return current_business_date(now)
    if kind == "weekly":
        return current_business_week_start(now)
    raise ValueError(f"Unsupported kind: {kind}")


def validate_snippet_date(target_date: date, now: datetime | None = None) -> None:
    if now is None:
        now = datetime.now()
    business_date = current_business_date(now)
    if target_date != business_date:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid date. Based on current time {now}, you can only work on {business_date}."
        )


def validate_snippet_week(target_week: date, now: datetime | None = None) -> None:
    if now is None:
        now = datetime.now()
    business_week_start = current_business_week_start(now)
    if target_week != business_week_start:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid week. Based on current time {now}, you can only work on the week starting {business_week_start}."
        )
