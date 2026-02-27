from __future__ import annotations

from datetime import date

from fastapi import HTTPException


async def get_snippet_owner_or_404(db, snippet, *, get_user_by_id):
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    return owner


def ensure_snippet_readable_or_403(viewer, owner, *, can_read_snippet) -> None:
    if not can_read_snippet(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")


def ensure_snippet_editable_or_403(
    viewer,
    owner,
    target_date_or_week,
    *,
    kind: str,
    request,
    is_snippet_editable,
) -> None:
    if not is_snippet_editable(
        viewer,
        owner,
        target_date_or_week,
        kind,
        request=request,
    ):
        raise HTTPException(status_code=403, detail="Not editable")


async def generate_feedback_json_or_none(
    *,
    daily_snippet_content: str,
    organized_content: str,
    playbook_content: str | None,
    copilot,
    generate_feedback_with_ai,
    parse_feedback_json,
    logger,
    prompt_name: str | None = None,
    snippet_label: str | None = None,
) -> str | None:
    kwargs = {
        "daily_snippet_content": daily_snippet_content,
        "organized_content": organized_content,
        "playbook_content": playbook_content,
        "copilot": copilot,
    }
    if prompt_name is not None:
        kwargs["prompt_name"] = prompt_name
    if snippet_label is not None:
        kwargs["snippet_label"] = snippet_label

    feedback_json = await generate_feedback_with_ai(**kwargs)
    return parse_feedback_json_or_none(
        feedback_json,
        parse_feedback_json=parse_feedback_json,
        logger=logger,
    )


async def persist_snippet_feedback(db, snippet, feedback_json: str | None) -> None:
    setattr(snippet, "feedback", feedback_json)
    await db.commit()
    await db.refresh(snippet)


async def resolve_source_and_organized_content(
    *,
    raw_content: str,
    copilot,
    organize_content_with_ai,
    build_suggestion_source,
    suggestion_prompt_name: str,
    direct_prompt_name: str | None = None,
) -> tuple[str, str]:
    if raw_content.strip():
        source_content = raw_content
        if direct_prompt_name is None:
            organized_content = await organize_content_with_ai(raw_content, copilot)
        else:
            organized_content = await organize_content_with_ai(
                raw_content,
                copilot,
                prompt_name=direct_prompt_name,
            )
        return source_content, organized_content

    source_content = await build_suggestion_source()
    organized_content = await organize_content_with_ai(
        source_content,
        copilot,
        prompt_name=suggestion_prompt_name,
    )
    return source_content, organized_content


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
