from __future__ import annotations

from datetime import date

from fastapi import HTTPException


def require_snippet_content_or_400(snippet) -> str:
    if not snippet:
        raise HTTPException(status_code=400, detail="content is required")

    content = (snippet.content or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")

    return content


def parse_feedback_json_or_none(
    feedback_json: str,
    *,
    parse_feedback_json,
    logger,
) -> str | None:
    try:
        parse_feedback_json(feedback_json)
    except ValueError:
        logger.error(f"Failed to parse AI feedback JSON: {feedback_json}")
        return None

    return feedback_json


def build_daily_suggestion_source(snippet_date: date, previous_context: str) -> str:
    return (
        f"오늘 날짜: {snippet_date.isoformat()}\n\n"
        f"전날 스니펫:\n{previous_context or '(전날 스니펫 없음)'}"
    )


def build_weekly_suggestion_source(week: date, daily_items) -> str:
    weekly_context_parts: list[str] = []
    for daily_item in daily_items:
        daily_text = (daily_item.content or "").strip()
        if daily_text:
            weekly_context_parts.append(f"### {daily_item.date.isoformat()}\n{daily_text}")

    weekly_context = "\n\n".join(weekly_context_parts) if weekly_context_parts else "(이번 주 Daily Snippet 없음)"
    return (
        f"이번 주 시작일: {week.isoformat()}\n\n"
        f"이번 주 Daily Snippets:\n{weekly_context}"
    )
