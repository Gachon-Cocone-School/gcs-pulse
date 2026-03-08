from __future__ import annotations

from datetime import date
from time import perf_counter
from typing import Any

from fastapi import HTTPException


def _is_unexpected_profile_context_type_error(exc: TypeError) -> bool:
    return "profile_context" in str(exc) and "unexpected keyword argument" in str(exc)


async def _call_with_optional_profile_context(async_fn, /, *args, profile_context: dict[str, Any], **kwargs):
    try:
        return await async_fn(*args, profile_context=profile_context, **kwargs)
    except TypeError as exc:
        if _is_unexpected_profile_context_type_error(exc):
            return await async_fn(*args, **kwargs)
        raise


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


async def build_snippet_page_data_response(
    *,
    request,
    db,
    snippet_id: int | None,
    kind: str,
    key_attr: str,
    key_step,
    get_snippet_viewer_or_401,
    get_request_now,
    current_business_key,
    build_snippet_page_data,
    get_snippet_by_id,
    list_snippets,
    list_from_key_name: str,
    list_to_key_name: str,
    can_read_snippet_fn=None,
):
    viewer = await get_snippet_viewer_or_401(request, db)
    now = get_request_now(request)
    server_key = current_business_key(kind, now)

    async def _list_snippets_for_range(*, db, viewer, order, from_key, to_key):
        return await list_snippets(
            db,
            viewer=viewer,
            limit=1,
            offset=0,
            order=order,
            q=None,
            scope="own",
            **{
                list_from_key_name: from_key,
                list_to_key_name: to_key,
            },
        )

    kwargs = {
        "db": db,
        "viewer": viewer,
        "request": request,
        "snippet_id": snippet_id,
        "server_key": server_key,
        "kind": kind,
        "key_attr": key_attr,
        "key_step": key_step,
        "get_snippet_by_id": get_snippet_by_id,
        "list_snippets_for_range": _list_snippets_for_range,
    }
    if can_read_snippet_fn is not None:
        kwargs["can_read_snippet_fn"] = can_read_snippet_fn

    return await build_snippet_page_data(**kwargs)


async def resolve_list_range_and_scope(
    *,
    from_key: str | None,
    to_key: str | None,
    snippet_id: int | None,
    scope: str,
    request,
    kind: str,
    key_attr: str,
    parse_key,
    get_snippet_by_id,
    get_request_now,
    current_business_key,
):
    parsed_from = parse_key(from_key) if from_key else None
    parsed_to = parse_key(to_key) if to_key else None

    if snippet_id is not None:
        snippet = await get_snippet_by_id(snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        parsed_from = parsed_to = getattr(snippet, key_attr)
        scope = "team"

    if parsed_from is None and parsed_to is None:
        now = get_request_now(request)
        current_key = current_business_key(kind, now)
        parsed_from = parsed_to = current_key

    return parsed_from, parsed_to, scope


async def create_snippet_for_current_key(
    *,
    request,
    db,
    content: str,
    kind: str,
    key_arg_name: str,
    get_snippet_viewer_or_401,
    get_request_now,
    current_business_key,
    upsert_snippet,
):
    viewer = await get_snippet_viewer_or_401(request, db)
    now = get_request_now(request)
    key = current_business_key(kind, now)

    return await upsert_snippet(
        db,
        user_id=viewer.id,
        content=content,
        **{key_arg_name: key},
    )


async def get_snippet_feedback_context(
    *,
    request,
    db,
    kind: str,
    get_snippet_viewer_or_401,
    get_request_now,
    current_business_key,
    get_snippet,
):
    viewer = await get_snippet_viewer_or_401(request, db)
    now = get_request_now(request)
    key = current_business_key(kind, now)
    snippet = await get_snippet(db, viewer.id, key)

    return key, snippet


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
    profile_context: dict[str, Any] | None = None,
) -> str | None:
    stage_context = dict(profile_context or {})
    stage_context.update(
        {
            "event": "snippet.organize.stage",
            "stage": "feedback_ai",
        }
    )

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

    feedback_start = perf_counter()
    feedback_json = await _call_with_optional_profile_context(
        generate_feedback_with_ai,
        profile_context=stage_context,
        **kwargs,
    )
    feedback_elapsed_ms = round((perf_counter() - feedback_start) * 1000, 2)
    logger.info(
        "snippet.organize.stage",
        extra={
            **stage_context,
            "status": "ok",
            "elapsed_ms": feedback_elapsed_ms,
        },
    )

    return parse_feedback_json_or_none(
        feedback_json,
        parse_feedback_json=parse_feedback_json,
        logger=logger,
        profile_context={
            **(profile_context or {}),
            "event": "snippet.organize.stage",
            "stage": "feedback_parse",
        },
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
    profile_context: dict[str, Any] | None = None,
    logger=None,
) -> tuple[str, str]:
    stage_context = dict(profile_context or {})

    if raw_content.strip():
        source_content = raw_content
        prompt_name = direct_prompt_name or "organize_daily.md"
        ai_context = {
            **stage_context,
            "event": "snippet.organize.stage",
            "stage": "organize_ai",
            "prompt_name": prompt_name,
        }
        organize_start = perf_counter()
        if direct_prompt_name is None:
            organized_content = await _call_with_optional_profile_context(
                organize_content_with_ai,
                raw_content,
                copilot,
                profile_context=ai_context,
            )
        else:
            organized_content = await _call_with_optional_profile_context(
                organize_content_with_ai,
                raw_content,
                copilot,
                prompt_name=direct_prompt_name,
                profile_context=ai_context,
            )
        if logger is not None:
            logger.info(
                "snippet.organize.stage",
                extra={
                    **ai_context,
                    "status": "ok",
                    "elapsed_ms": round((perf_counter() - organize_start) * 1000, 2),
                },
            )
        return source_content, organized_content

    source_start = perf_counter()
    source_content = await build_suggestion_source()
    if logger is not None:
        logger.info(
            "snippet.organize.stage",
            extra={
                **stage_context,
                "event": "snippet.organize.stage",
                "stage": "build_suggestion_source",
                "status": "ok",
                "elapsed_ms": round((perf_counter() - source_start) * 1000, 2),
            },
        )

    ai_context = {
        **stage_context,
        "event": "snippet.organize.stage",
        "stage": "organize_ai",
        "prompt_name": suggestion_prompt_name,
    }
    organize_start = perf_counter()
    organized_content = await _call_with_optional_profile_context(
        organize_content_with_ai,
        source_content,
        copilot,
        prompt_name=suggestion_prompt_name,
        profile_context=ai_context,
    )
    if logger is not None:
        logger.info(
            "snippet.organize.stage",
            extra={
                **ai_context,
                "status": "ok",
                "elapsed_ms": round((perf_counter() - organize_start) * 1000, 2),
            },
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
    profile_context: dict[str, Any] | None = None,
) -> str | None:
    parse_start = perf_counter()
    try:
        parse_feedback_json(feedback_json)
    except ValueError:
        logger.error(
            "Failed to parse AI feedback JSON",
            extra={
                **(profile_context or {}),
                "status": "error",
                "elapsed_ms": round((perf_counter() - parse_start) * 1000, 2),
            },
        )
        return None

    logger.info(
        "snippet.organize.stage",
        extra={
            **(profile_context or {}),
            "status": "ok",
            "elapsed_ms": round((perf_counter() - parse_start) * 1000, 2),
        },
    )
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
