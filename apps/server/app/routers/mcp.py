from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from time import perf_counter
from typing import Any, AsyncIterator, Awaitable, Callable

from fastapi import APIRouter, Depends, HTTPException
from mcp import types as mcp_types
from mcp.server.lowlevel import Server as MCPServer
from mcp.server.lowlevel.helper_types import ReadResourceContents
from mcp.server.lowlevel.server import request_ctx
from mcp.server.streamable_http import MCP_SESSION_ID_HEADER
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.types import Receive, Scope, Send

from app import crud
import app.crud_meeting_rooms as crud_meeting_rooms
from app.core.config import settings
from app.database import AsyncSessionLocal, get_db
from app.dependencies import require_privileged_api_role
from app.dependencies_copilot import get_copilot_client
from app.limiter import limiter
from app.routers import snippet_flow_helpers as _flow
from app.routers import snippet_utils as _snippet_utils
from app.routers.snippet_access import BearerAuthContext, get_bearer_auth_or_401, get_request_now
from app.utils_time import current_business_key

MCP_SERVER_NAME = "gcs-pulse-mcp"
logger = logging.getLogger(__name__)

MCP_RESOURCE_MY_PROFILE = "gcs://me/profile"
MCP_RESOURCE_MY_ACHIEVEMENTS = "gcs://me/achievements"

MCP_TOOL_DAILY_PAGE_DATA = "daily_snippets_page_data"
MCP_TOOL_DAILY_GET = "daily_snippets_get"
MCP_TOOL_DAILY_LIST = "daily_snippets_list"
MCP_TOOL_DAILY_CREATE = "daily_snippets_create"
MCP_TOOL_DAILY_ORGANIZE = "daily_snippets_organize"
MCP_TOOL_DAILY_FEEDBACK = "daily_snippets_feedback"
MCP_TOOL_DAILY_UPDATE = "daily_snippets_update"
MCP_TOOL_DAILY_DELETE = "daily_snippets_delete"

MCP_TOOL_WEEKLY_PAGE_DATA = "weekly_snippets_page_data"
MCP_TOOL_WEEKLY_GET = "weekly_snippets_get"
MCP_TOOL_WEEKLY_LIST = "weekly_snippets_list"
MCP_TOOL_WEEKLY_CREATE = "weekly_snippets_create"
MCP_TOOL_WEEKLY_ORGANIZE = "weekly_snippets_organize"
MCP_TOOL_WEEKLY_FEEDBACK = "weekly_snippets_feedback"
MCP_TOOL_WEEKLY_UPDATE = "weekly_snippets_update"
MCP_TOOL_WEEKLY_DELETE = "weekly_snippets_delete"

MCP_TOOL_COMMENT_LIST = "comments_list"
MCP_TOOL_COMMENT_CREATE = "comments_create"
MCP_TOOL_COMMENT_UPDATE = "comments_update"
MCP_TOOL_COMMENT_DELETE = "comments_delete"

MCP_TOOL_NOTIFICATION_LIST = "notifications_list"
MCP_TOOL_NOTIFICATION_UNREAD_COUNT = "notifications_unread_count"
MCP_TOOL_NOTIFICATION_READ = "notifications_read"
MCP_TOOL_NOTIFICATION_READ_ALL = "notifications_read_all"
MCP_TOOL_NOTIFICATION_GET_SETTINGS = "notifications_get_settings"
MCP_TOOL_NOTIFICATION_UPDATE_SETTINGS = "notifications_update_settings"

MCP_TOOL_MEETING_ROOM_LIST = "meeting_rooms_list"
MCP_TOOL_MEETING_ROOM_RESERVATIONS = "meeting_rooms_reservations"
MCP_TOOL_MEETING_ROOM_RESERVE = "meeting_rooms_reserve"
MCP_TOOL_MEETING_ROOM_CANCEL = "meeting_rooms_cancel"

MCP_TOOL_ACHIEVEMENT_ME = "achievements_me"
MCP_TOOL_ACHIEVEMENT_RECENT = "achievements_recent"

MCP_TOOL_USERS_LIST = "users_list"
MCP_TOOL_USERS_SEARCH = "users_search"
MCP_TOOL_USERS_TEAMS = "users_teams"

_mcp_server = MCPServer(name=MCP_SERVER_NAME)


def _ctx_request() -> Request:
    ctx = request_ctx.get()
    if ctx.request is None or not isinstance(ctx.request, Request):
        raise RuntimeError("MCP request context unavailable")
    return ctx.request


def _ctx_user() -> Any:
    request = _ctx_request()
    user = getattr(request.state, "mcp_user", None)
    if user is None:
        raise RuntimeError("MCP user context unavailable")
    return user


def _ctx_db() -> AsyncSession:
    request = _ctx_request()
    db = getattr(request.state, "mcp_db", None)
    if db is None:
        raise RuntimeError("MCP DB context unavailable")
    return db


def _require_int(arguments: dict[str, Any], key: str) -> int:
    raw_value = arguments.get(key)
    if raw_value is None:
        raise ValueError(f"{key} is required")

    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be integer") from exc


def _optional_int(arguments: dict[str, Any], key: str) -> int | None:
    raw_value = arguments.get(key)
    if raw_value is None:
        return None

    try:
        return int(raw_value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be integer") from exc


def _require_str(arguments: dict[str, Any], key: str) -> str:
    raw_value = arguments.get(key)
    if not isinstance(raw_value, str):
        raise ValueError(f"{key} must be string")
    return raw_value


def _clamp_int(raw_value: Any, *, default: int, min_value: int, max_value: int) -> int:
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return default

    if value < min_value:
        return min_value
    if value > max_value:
        return max_value
    return value


def _serialize_user_summary(user: Any) -> dict[str, Any] | None:
    if user is None:
        return None

    return {
        "id": int(user.id),
        "name": str(user.name),
        "email": str(user.email),
        "picture": user.picture,
    }


def _serialize_daily_snippet(snippet: Any) -> dict[str, Any]:
    return {
        "id": int(snippet.id),
        "user_id": int(snippet.user_id),
        "user": _serialize_user_summary(getattr(snippet, "user", None)),
        "date": snippet.date.isoformat(),
        "content": str(snippet.content),
        "feedback": snippet.feedback,
        "created_at": snippet.created_at.isoformat() if snippet.created_at else None,
        "updated_at": snippet.updated_at.isoformat() if snippet.updated_at else None,
        "comments_count": int(getattr(snippet, "comments_count", 0) or 0),
        "editable": bool(getattr(snippet, "editable", False)),
    }


def _serialize_weekly_snippet(snippet: Any) -> dict[str, Any]:
    return {
        "id": int(snippet.id),
        "user_id": int(snippet.user_id),
        "user": _serialize_user_summary(getattr(snippet, "user", None)),
        "week": snippet.week.isoformat(),
        "content": str(snippet.content),
        "feedback": snippet.feedback,
        "created_at": snippet.created_at.isoformat() if snippet.created_at else None,
        "updated_at": snippet.updated_at.isoformat() if snippet.updated_at else None,
        "editable": bool(getattr(snippet, "editable", False)),
    }


def _serialize_comment(comment: Any) -> dict[str, Any]:
    return {
        "id": int(comment.id),
        "user_id": int(comment.user_id),
        "user": _serialize_user_summary(getattr(comment, "user", None)),
        "daily_snippet_id": int(comment.daily_snippet_id) if comment.daily_snippet_id is not None else None,
        "weekly_snippet_id": int(comment.weekly_snippet_id) if comment.weekly_snippet_id is not None else None,
        "comment_type": str(comment.comment_type),
        "content": str(comment.content),
        "created_at": comment.created_at.isoformat() if comment.created_at else None,
        "updated_at": comment.updated_at.isoformat() if comment.updated_at else None,
    }


async def _load_my_profile() -> dict[str, Any]:
    user = _ctx_user()
    return {
        "id": int(user.id),
        "email": str(user.email),
        "name": str(user.name or user.email),
        "roles": [str(role) for role in (user.roles or [])],
        "team_id": int(user.team_id) if user.team_id is not None else None,
        "league_type": str(user.league_type),
    }


async def _load_my_achievements() -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()

    items = await crud.list_my_achievement_groups(db, user_id=user.id)
    normalized_items: list[dict[str, Any]] = []
    for item in items:
        normalized_items.append(
            {
                "achievement_definition_id": int(item["achievement_definition_id"]),
                "code": str(item["code"]),
                "name": str(item["name"]),
                "description": str(item["description"]),
                "badge_image_url": str(item["badge_image_url"]),
                "rarity": str(item["rarity"]),
                "grant_count": int(item["grant_count"]),
                "last_granted_at": item["last_granted_at"].isoformat(),
            }
        )

    return {
        "items": normalized_items,
        "total": len(normalized_items),
    }


async def _run_daily_page_data(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    snippet_id = _optional_int(arguments, "id")

    payload = await _flow.build_snippet_page_data_response(
        request=request,
        db=db,
        snippet_id=snippet_id,
        kind="daily",
        key_attr="date",
        key_step=timedelta(days=1),
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        build_snippet_page_data=_snippet_utils.build_snippet_page_data,
        get_snippet_by_id=crud.get_daily_snippet_by_id,
        list_snippets=crud.list_daily_snippets,
        list_from_key_name="from_date",
        list_to_key_name="to_date",
    )

    snippet = payload.get("snippet")
    return {
        "snippet": _serialize_daily_snippet(snippet) if snippet else None,
        "read_only": bool(payload["read_only"]),
        "prev_id": payload.get("prev_id"),
        "next_id": payload.get("next_id"),
    }


async def _run_daily_get(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()
    snippet_id = _require_int(arguments, "snippet_id")

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    await _flow.ensure_snippet_readable_or_403(viewer, owner, snippet.date, db, can_read_snippet=_snippet_utils.can_read_snippet)

    _snippet_utils.set_snippet_editable(
        snippet,
        viewer,
        owner,
        "daily",
        "date",
        request,
    )
    return _serialize_daily_snippet(snippet)


async def _run_daily_list(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    limit = _clamp_int(arguments.get("limit"), default=50, min_value=1, max_value=100)
    offset = _clamp_int(arguments.get("offset"), default=0, min_value=0, max_value=10_000)
    order = "asc" if arguments.get("order") == "asc" else "desc"
    from_date = arguments.get("from_date")
    to_date = arguments.get("to_date")
    snippet_id = _optional_int(arguments, "id")
    q = arguments.get("q")
    if q is not None:
        q = str(q)
    scope = str(arguments.get("scope") or "own")

    async def _get_snippet_by_id(current_snippet_id: int):
        return await crud.get_daily_snippet_by_id(db, current_snippet_id)

    parsed_from, parsed_to, scope = await _flow.resolve_list_range_and_scope(
        from_key=from_date,
        to_key=to_date,
        snippet_id=snippet_id,
        scope=scope,
        request=request,
        kind="daily",
        key_attr="date",
        parse_key=lambda key: datetime.fromisoformat(key).date(),
        get_snippet_by_id=_get_snippet_by_id,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
    )

    items, total = await crud.list_daily_snippets(
        db,
        viewer=viewer,
        limit=limit,
        offset=offset,
        order=order,
        from_date=parsed_from,
        to_date=parsed_to,
        q=q,
        scope=scope,
    )

    await _snippet_utils.apply_editable_to_snippet_list(db, items, viewer, "daily", "date", request)

    return {
        "items": [_serialize_daily_snippet(item) for item in items],
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
    }


async def _run_daily_create(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    content = _require_str(arguments, "content")

    snippet = await _flow.create_snippet_for_current_key(
        request=request,
        db=db,
        content=content,
        kind="daily",
        key_arg_name="snippet_date",
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        upsert_snippet=crud.upsert_daily_snippet,
    )
    return _serialize_daily_snippet(snippet)


async def _run_daily_organize(arguments: dict[str, Any]) -> dict[str, Any]:
    total_start = perf_counter()
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()
    copilot = await get_copilot_client(request)

    raw_content = _require_str(arguments, "content")
    now = _snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    profile_context = {
        "channel": "mcp",
        "flow": "organize",
        "snippet_kind": "daily",
        "tool_name": MCP_TOOL_DAILY_ORGANIZE,
        "user_id": viewer.id,
    }

    snippet = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, snippet_date)
    playbook_content = snippet.playbook if snippet else None

    async def _build_suggestion_source() -> str:
        previous_date = snippet_date - timedelta(days=1)
        previous = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, previous_date)
        previous_context = previous.content.strip() if previous else ""
        return _flow.build_daily_suggestion_source(snippet_date, previous_context)

    source_content, organized_content = await _flow.resolve_source_and_organized_content(
        raw_content=raw_content,
        copilot=copilot,
        organize_content_with_ai=_snippet_utils.organize_content_with_ai,
        build_suggestion_source=_build_suggestion_source,
        suggestion_prompt_name="suggest_daily_from_previous.md",
        profile_context=profile_context,
        logger=logger,
    )

    feedback_json = await _flow.generate_feedback_json_or_none(
        snippet_content=organized_content,
        playbook_content=playbook_content,
        copilot=copilot,
        generate_feedback_with_ai=_snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
        profile_context=profile_context,
    )

    logger.info(
        "snippet.organize.total",
        extra={
            **profile_context,
            "event": "snippet.organize.total",
            "status": "ok",
            "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
        },
    )

    return {
        "date": snippet_date.isoformat(),
        "organized_content": organized_content,
        "feedback": feedback_json,
    }


async def _run_daily_feedback(arguments: dict[str, Any]) -> dict[str, Any]:
    _ = arguments
    request = _ctx_request()
    db = _ctx_db()
    copilot = await get_copilot_client(request)

    snippet_date, snippet = await _flow.get_snippet_feedback_context(
        request=request,
        db=db,
        kind="daily",
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        get_snippet=crud.get_daily_snippet_by_user_and_date,
    )
    content = _flow.require_snippet_content_or_400(snippet)

    feedback_json = await _flow.generate_feedback_json_or_none(
        snippet_content=content,
        playbook_content=snippet.playbook,
        copilot=copilot,
        generate_feedback_with_ai=_snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
    )
    await _flow.persist_snippet_feedback(db, snippet, feedback_json)

    return {
        "date": snippet_date.isoformat(),
        "feedback": feedback_json,
    }


async def _run_daily_update(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    snippet_id = _require_int(arguments, "snippet_id")
    content = _require_str(arguments, "content")

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=_snippet_utils.is_snippet_editable,
    )

    updated = await crud.update_daily_snippet(db, snippet=snippet, content=content)
    return _serialize_daily_snippet(updated)


async def _run_daily_delete(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    snippet_id = _require_int(arguments, "snippet_id")

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=_snippet_utils.is_snippet_editable,
    )

    await crud.delete_daily_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}


async def _run_weekly_page_data(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    snippet_id = _optional_int(arguments, "id")

    payload = await _flow.build_snippet_page_data_response(
        request=request,
        db=db,
        snippet_id=snippet_id,
        kind="weekly",
        key_attr="week",
        key_step=timedelta(days=7),
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        build_snippet_page_data=_snippet_utils.build_snippet_page_data,
        get_snippet_by_id=crud.get_weekly_snippet_by_id,
        list_snippets=crud.list_weekly_snippets,
        list_from_key_name="from_week",
        list_to_key_name="to_week",
        can_read_snippet_fn=_snippet_utils.can_read_snippet,
    )

    snippet = payload.get("snippet")
    return {
        "snippet": _serialize_weekly_snippet(snippet) if snippet else None,
        "read_only": bool(payload["read_only"]),
        "prev_id": payload.get("prev_id"),
        "next_id": payload.get("next_id"),
    }


async def _run_weekly_get(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()
    snippet_id = _require_int(arguments, "snippet_id")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    await _flow.ensure_snippet_readable_or_403(viewer, owner, snippet.week, db, can_read_snippet=_snippet_utils.can_read_snippet)

    _snippet_utils.set_snippet_editable(snippet, viewer, owner, "weekly", "week", request)
    return _serialize_weekly_snippet(snippet)


async def _run_weekly_list(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    limit = _clamp_int(arguments.get("limit"), default=50, min_value=1, max_value=100)
    offset = _clamp_int(arguments.get("offset"), default=0, min_value=0, max_value=10_000)
    order = "asc" if arguments.get("order") == "asc" else "desc"
    from_week = arguments.get("from_week")
    to_week = arguments.get("to_week")
    snippet_id = _optional_int(arguments, "id")
    q = arguments.get("q")
    if q is not None:
        q = str(q)
    scope = str(arguments.get("scope") or "own")

    async def _get_snippet_by_id(current_snippet_id: int):
        return await crud.get_weekly_snippet_by_id(db, current_snippet_id)

    parsed_from, parsed_to, scope = await _flow.resolve_list_range_and_scope(
        from_key=from_week,
        to_key=to_week,
        snippet_id=snippet_id,
        scope=scope,
        request=request,
        kind="weekly",
        key_attr="week",
        parse_key=lambda key: datetime.fromisoformat(key).date(),
        get_snippet_by_id=_get_snippet_by_id,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
    )

    items, total = await crud.list_weekly_snippets(
        db,
        viewer=viewer,
        limit=limit,
        offset=offset,
        order=order,
        from_week=parsed_from,
        to_week=parsed_to,
        q=q,
        scope=scope,
    )

    await _snippet_utils.apply_editable_to_snippet_list(db, items, viewer, "weekly", "week", request)

    return {
        "items": [_serialize_weekly_snippet(item) for item in items],
        "total": int(total),
        "limit": int(limit),
        "offset": int(offset),
    }


async def _run_weekly_create(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    content = _require_str(arguments, "content")

    snippet = await _flow.create_snippet_for_current_key(
        request=request,
        db=db,
        content=content,
        kind="weekly",
        key_arg_name="week",
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        upsert_snippet=crud.upsert_weekly_snippet,
    )
    return _serialize_weekly_snippet(snippet)


async def _run_weekly_organize(arguments: dict[str, Any]) -> dict[str, Any]:
    total_start = perf_counter()
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()
    copilot = await get_copilot_client(request)

    raw_content = _require_str(arguments, "content")
    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    profile_context = {
        "channel": "mcp",
        "flow": "organize",
        "snippet_kind": "weekly",
        "tool_name": MCP_TOOL_WEEKLY_ORGANIZE,
        "user_id": viewer.id,
    }

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    playbook_content = snippet.playbook if snippet else None

    async def _build_suggestion_source() -> str:
        week_end = week + timedelta(days=6)
        daily_items, _ = await crud.list_daily_snippets(
            db,
            viewer=viewer,
            limit=7,
            offset=0,
            order="asc",
            from_date=week,
            to_date=week_end,
            q=None,
            scope="own",
        )
        return _flow.build_weekly_suggestion_source(week, daily_items)

    source_content, organized_content = await _flow.resolve_source_and_organized_content(
        raw_content=raw_content,
        copilot=copilot,
        organize_content_with_ai=_snippet_utils.organize_content_with_ai,
        build_suggestion_source=_build_suggestion_source,
        suggestion_prompt_name="organize_weekly.md",
        direct_prompt_name="organize_weekly.md",
        profile_context=profile_context,
        logger=logger,
    )

    feedback_json = await _flow.generate_feedback_json_or_none(
        snippet_content=organized_content,
        playbook_content=playbook_content,
        copilot=copilot,
        generate_feedback_with_ai=_snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
        profile_context=profile_context,
    )

    logger.info(
        "snippet.organize.total",
        extra={
            **profile_context,
            "event": "snippet.organize.total",
            "status": "ok",
            "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
        },
    )

    return {
        "week": week.isoformat(),
        "organized_content": organized_content,
        "feedback": feedback_json,
    }


async def _run_weekly_feedback(arguments: dict[str, Any]) -> dict[str, Any]:
    _ = arguments
    request = _ctx_request()
    db = _ctx_db()
    copilot = await get_copilot_client(request)

    week, snippet = await _flow.get_snippet_feedback_context(
        request=request,
        db=db,
        kind="weekly",
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        get_snippet=crud.get_weekly_snippet_by_user_and_week,
    )
    content = _flow.require_snippet_content_or_400(snippet)

    feedback_json = await _flow.generate_feedback_json_or_none(
        snippet_content=content,
        playbook_content=snippet.playbook,
        copilot=copilot,
        generate_feedback_with_ai=_snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
    )
    await _flow.persist_snippet_feedback(db, snippet, feedback_json)

    return {
        "week": week.isoformat(),
        "feedback": feedback_json,
    }


async def _run_weekly_update(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    snippet_id = _require_int(arguments, "snippet_id")
    content = _require_str(arguments, "content")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.week,
        kind="weekly",
        request=request,
        is_snippet_editable=_snippet_utils.is_snippet_editable,
    )

    updated = await crud.update_weekly_snippet(db, snippet=snippet, content=content)
    return _serialize_weekly_snippet(updated)


async def _run_weekly_delete(arguments: dict[str, Any]) -> dict[str, Any]:
    request = _ctx_request()
    db = _ctx_db()
    viewer = _ctx_user()

    snippet_id = _require_int(arguments, "snippet_id")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(db, snippet, get_user_by_id=crud.get_user_by_id)
    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.week,
        kind="weekly",
        request=request,
        is_snippet_editable=_snippet_utils.is_snippet_editable,
    )

    await crud.delete_weekly_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}


async def _run_comment_list(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    viewer = _ctx_user()

    daily_snippet_id = _optional_int(arguments, "daily_snippet_id")
    weekly_snippet_id = _optional_int(arguments, "weekly_snippet_id")

    if not (bool(daily_snippet_id) ^ bool(weekly_snippet_id)):
        raise ValueError("Exactly one of daily_snippet_id or weekly_snippet_id must be provided")

    if daily_snippet_id:
        snippet = await crud.get_daily_snippet_by_id(db, daily_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Daily snippet not found")
        if not await _snippet_utils.can_read_snippet(viewer, snippet.user, snippet.date, db):
            raise HTTPException(status_code=403, detail="Access denied")
        comments = await crud.list_comments(db, daily_snippet_id=daily_snippet_id)
    else:
        assert weekly_snippet_id is not None
        snippet = await crud.get_weekly_snippet_by_id(db, weekly_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Weekly snippet not found")
        if not await _snippet_utils.can_read_snippet(viewer, snippet.user, snippet.week, db):
            raise HTTPException(status_code=403, detail="Access denied")
        comments = await crud.list_comments(db, weekly_snippet_id=weekly_snippet_id)

    return {
        "items": [_serialize_comment(c) for c in comments],
        "total": len(comments),
    }


async def _run_comment_create(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    viewer = _ctx_user()

    content = _require_str(arguments, "content")
    daily_snippet_id = _optional_int(arguments, "daily_snippet_id")
    weekly_snippet_id = _optional_int(arguments, "weekly_snippet_id")
    comment_type = str(arguments.get("comment_type") or "peer")
    if comment_type not in ("peer", "professor"):
        raise ValueError("comment_type must be 'peer' or 'professor'")

    if not (bool(daily_snippet_id) ^ bool(weekly_snippet_id)):
        raise ValueError("Exactly one of daily_snippet_id or weekly_snippet_id must be provided")

    if daily_snippet_id:
        snippet = await crud.get_daily_snippet_by_id(db, daily_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Daily snippet not found")
        if not await _snippet_utils.can_read_snippet(viewer, snippet.user, snippet.date, db):
            raise HTTPException(status_code=403, detail="Access denied")
    else:
        assert weekly_snippet_id is not None
        snippet = await crud.get_weekly_snippet_by_id(db, weekly_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Weekly snippet not found")
        if not await _snippet_utils.can_read_snippet(viewer, snippet.user, snippet.week, db):
            raise HTTPException(status_code=403, detail="Access denied")

    comment = await crud.create_comment(
        db,
        user_id=viewer.id,
        content=content,
        daily_snippet_id=daily_snippet_id,
        weekly_snippet_id=weekly_snippet_id,
        comment_type=comment_type,
    )
    return _serialize_comment(comment)


async def _run_comment_update(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    viewer = _ctx_user()

    comment_id = _require_int(arguments, "comment_id")
    content = _require_str(arguments, "content")

    comment = await crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != viewer.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")

    updated = await crud.update_comment(db, comment, content)
    return _serialize_comment(updated)


async def _run_comment_delete(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    viewer = _ctx_user()

    comment_id = _require_int(arguments, "comment_id")

    comment = await crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")
    if comment.user_id != viewer.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    await crud.delete_comment(db, comment)
    return {"message": "Comment deleted"}


# ---------------------------------------------------------------------------
# Notifications handlers
# ---------------------------------------------------------------------------

def _serialize_notification(n: Any) -> dict[str, Any]:
    return {
        "id": int(n.id),
        "user_id": int(n.user_id),
        "actor_user_id": int(n.actor_user_id) if n.actor_user_id is not None else None,
        "type": str(n.type),
        "is_read": bool(n.is_read),
        "read_at": n.read_at.isoformat() if n.read_at else None,
        "daily_snippet_id": int(n.daily_snippet_id) if n.daily_snippet_id is not None else None,
        "weekly_snippet_id": int(n.weekly_snippet_id) if n.weekly_snippet_id is not None else None,
        "comment_id": int(n.comment_id) if n.comment_id is not None else None,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


def _serialize_notification_setting(s: Any) -> dict[str, Any]:
    return {
        "user_id": int(s.user_id),
        "notify_post_author": bool(s.notify_post_author),
        "notify_mentions": bool(s.notify_mentions),
        "notify_participants": bool(s.notify_participants),
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


async def _run_notifications_list(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    limit = _clamp_int(arguments.get("limit"), default=20, min_value=1, max_value=100)
    offset = _clamp_int(arguments.get("offset"), default=0, min_value=0, max_value=10000)
    items, total = await crud.list_notifications(db, user_id=user.id, limit=limit, offset=offset)
    return {
        "items": [_serialize_notification(n) for n in items],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


async def _run_notifications_unread_count(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    count = await crud.count_unread_notifications(db, user_id=user.id)
    return {"unread_count": count}


async def _run_notifications_read(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    notification_id = _require_int(arguments, "notification_id")
    notification = await crud.get_notification_by_id_for_user(db, notification_id, user_id=user.id)
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found")
    updated = await crud.mark_notification_as_read(db, notification)
    return _serialize_notification(updated)


async def _run_notifications_read_all(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    updated_count = await crud.mark_all_notifications_as_read(db, user_id=user.id)
    return {"updated_count": updated_count}


async def _run_notifications_get_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    setting = await crud.get_or_create_notification_setting(db, user_id=user.id)
    return _serialize_notification_setting(setting)


async def _run_notifications_update_settings(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    setting = await crud.get_or_create_notification_setting(db, user_id=user.id)

    def _optional_bool(key: str) -> bool | None:
        v = arguments.get(key)
        if v is None:
            return None
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            if v.lower() in ("true", "1", "yes"):
                return True
            if v.lower() in ("false", "0", "no"):
                return False
        raise ValueError(f"{key} must be boolean")

    updated = await crud.update_notification_setting(
        db,
        setting,
        notify_post_author=_optional_bool("notify_post_author"),
        notify_mentions=_optional_bool("notify_mentions"),
        notify_participants=_optional_bool("notify_participants"),
    )
    return _serialize_notification_setting(updated)


# ---------------------------------------------------------------------------
# Meeting rooms handlers
# ---------------------------------------------------------------------------

def _serialize_meeting_room(room: Any) -> dict[str, Any]:
    return {
        "id": int(room.id),
        "name": str(room.name),
        "location": str(room.location) if room.location else None,
    }


def _serialize_reservation(r: Any, viewer_id: int) -> dict[str, Any]:
    is_admin_user = False  # MCP context에서는 보수적으로 본인 여부만 체크
    reserved_by = getattr(r, "reserved_by", None)
    if reserved_by and reserved_by.name:
        display_name = reserved_by.name
    elif reserved_by and reserved_by.email:
        display_name = reserved_by.email
    else:
        display_name = f"user:{r.reserved_by_user_id}"

    return {
        "id": int(r.id),
        "meeting_room_id": int(r.meeting_room_id),
        "reserved_by_user_id": int(r.reserved_by_user_id),
        "reserved_by_name": display_name,
        "start_at": r.start_at.isoformat() if r.start_at else None,
        "end_at": r.end_at.isoformat() if r.end_at else None,
        "purpose": r.purpose,
        "can_cancel": (r.reserved_by_user_id == viewer_id or is_admin_user),
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


async def _run_meeting_rooms_list(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    rooms = await crud_meeting_rooms.list_meeting_rooms(db)
    return {"items": [_serialize_meeting_room(r) for r in rooms]}


async def _run_meeting_rooms_reservations(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    room_id = _require_int(arguments, "room_id")
    date_str = _require_str(arguments, "date")
    try:
        target_date = date.fromisoformat(date_str)
    except ValueError as exc:
        raise ValueError("date must be in YYYY-MM-DD format") from exc

    day_start = datetime.combine(target_date, datetime.min.time())
    day_end = day_start + timedelta(days=1)
    reservations = await crud_meeting_rooms.list_room_reservations_for_day(
        db, room_id=room_id, day_start=day_start, day_end=day_end
    )
    return {"items": [_serialize_reservation(r, viewer_id=user.id) for r in reservations]}


async def _run_meeting_rooms_reserve(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    room_id = _require_int(arguments, "room_id")
    start_at_str = _require_str(arguments, "start_at")
    end_at_str = _require_str(arguments, "end_at")
    purpose = arguments.get("purpose")

    try:
        start_at = datetime.fromisoformat(start_at_str)
        end_at = datetime.fromisoformat(end_at_str)
    except ValueError as exc:
        raise ValueError("start_at and end_at must be ISO 8601 datetime strings") from exc

    if start_at >= end_at:
        raise ValueError("start_at must be earlier than end_at")

    has_overlap = await crud_meeting_rooms.has_overlapping_reservation(
        db, room_id=room_id, start_at=start_at, end_at=end_at
    )
    if has_overlap:
        raise HTTPException(status_code=409, detail="Reservation time overlaps with an existing booking")

    reservation = await crud_meeting_rooms.create_reservation(
        db,
        room_id=room_id,
        reserved_by_user_id=user.id,
        start_at=start_at,
        end_at=end_at,
        purpose=(str(purpose).strip() if purpose else None) or None,
    )
    return _serialize_reservation(reservation, viewer_id=user.id)


async def _run_meeting_rooms_cancel(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    reservation_id = _require_int(arguments, "reservation_id")

    reservation = await crud_meeting_rooms.get_reservation_by_id(db, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    is_owner = reservation.reserved_by_user_id == user.id
    is_admin_user = bool(user.roles and "admin" in user.roles)
    if not is_owner and not is_admin_user:
        raise HTTPException(status_code=403, detail="Only owner or admin can cancel this reservation")

    await crud_meeting_rooms.delete_reservation(db, reservation)
    return {"message": "Deleted"}


# ---------------------------------------------------------------------------
# Achievements handlers
# ---------------------------------------------------------------------------

async def _run_achievements_me(arguments: dict[str, Any]) -> dict[str, Any]:
    return await _load_my_achievements()


async def _run_achievements_recent(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    request = _ctx_request()
    now = get_request_now(request)
    limit = _clamp_int(arguments.get("limit"), default=10, min_value=1, max_value=100)
    items, total = await crud.list_recent_public_achievement_grants(db, now=now, limit=limit)
    return {
        "items": [
            {
                "achievement_definition_id": int(item["achievement_definition_id"]),
                "code": str(item["code"]),
                "name": str(item["name"]),
                "description": str(item["description"]),
                "badge_image_url": str(item["badge_image_url"]),
                "rarity": str(item["rarity"]),
                "user_id": int(item["user_id"]),
                "user_name": str(item["user_name"]),
                "granted_at": item["granted_at"].isoformat() if item.get("granted_at") else None,
            }
            for item in items
        ],
        "total": total,
        "limit": limit,
    }


# ---------------------------------------------------------------------------
# Users handlers
# ---------------------------------------------------------------------------

async def _run_users_list(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    require_privileged_api_role(user)
    limit = _clamp_int(arguments.get("limit"), default=100, min_value=1, max_value=200)
    offset = _clamp_int(arguments.get("offset"), default=0, min_value=0, max_value=10000)
    rows, total = await crud.list_students(db, limit=limit, offset=offset)
    items = [
        {
            "student_user_id": student.id,
            "student_name": student.name or student.email,
            "student_email": student.email,
            "team_name": team.name if team else None,
        }
        for student, team in rows
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def _run_users_search(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    require_privileged_api_role(user)
    q = _require_str(arguments, "q").strip()
    if not q:
        return {"items": [], "total": 0}
    limit = _clamp_int(arguments.get("limit"), default=20, min_value=1, max_value=50)
    rows, total = await crud.search_students(db, q, limit)
    items = [
        {
            "student_user_id": student.id,
            "student_name": student.name or student.email,
            "student_email": student.email,
            "team_name": team.name if team else None,
        }
        for student, team in rows
    ]
    return {"items": items, "total": total}


async def _run_users_teams(arguments: dict[str, Any]) -> dict[str, Any]:
    db = _ctx_db()
    user = _ctx_user()
    require_privileged_api_role(user)
    limit = _clamp_int(arguments.get("limit"), default=100, min_value=1, max_value=200)
    offset = _clamp_int(arguments.get("offset"), default=0, min_value=0, max_value=10000)
    teams, total = await crud.list_teams(db, limit=limit, offset=offset)
    items = [
        {
            "id": int(t.id),
            "name": str(t.name),
            "invite_code": str(t.invite_code) if t.invite_code else None,
        }
        for t in teams
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


def _build_tool(
    *,
    name: str,
    title: str,
    description: str,
    input_schema: dict[str, Any],
    read_only: bool,
) -> mcp_types.Tool:
    return mcp_types.Tool(
        name=name,
        title=title,
        description=description,
        inputSchema=input_schema,
        annotations=mcp_types.ToolAnnotations(
            readOnlyHint=read_only,
            destructiveHint=not read_only,
            idempotentHint=read_only,
        ),
    )


@_mcp_server.list_tools()
async def list_mcp_tools() -> list[mcp_types.Tool]:
    pagination_schema = {
        "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        "offset": {"type": "integer", "minimum": 0},
    }

    return [
        _build_tool(
            name=MCP_TOOL_DAILY_PAGE_DATA,
            title="Daily snippets page data",
            description="GET /daily-snippets/page-data 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"id": {"type": "integer", "minimum": 1}},
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_GET,
            title="Get daily snippet",
            description="GET /daily-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"snippet_id": {"type": "integer", "minimum": 1}},
                "required": ["snippet_id"],
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_LIST,
            title="List daily snippets",
            description="GET /daily-snippets 대응 툴",
            input_schema={
                "type": "object",
                "properties": {
                    **pagination_schema,
                    "order": {"type": "string", "enum": ["asc", "desc"]},
                    "from_date": {"type": "string", "format": "date"},
                    "to_date": {"type": "string", "format": "date"},
                    "id": {"type": "integer", "minimum": 1},
                    "q": {"type": "string"},
                    "scope": {"type": "string", "enum": ["own", "team"]},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_CREATE,
            title="Create daily snippet",
            description="POST /daily-snippets 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_ORGANIZE,
            title="Organize daily snippet",
            description="POST /daily-snippets/organize 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_FEEDBACK,
            title="Generate daily feedback",
            description="GET /daily-snippets/feedback 대응 툴",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_UPDATE,
            title="Update daily snippet",
            description="PUT /daily-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {
                    "snippet_id": {"type": "integer", "minimum": 1},
                    "content": {"type": "string"},
                },
                "required": ["snippet_id", "content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_DAILY_DELETE,
            title="Delete daily snippet",
            description="DELETE /daily-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"snippet_id": {"type": "integer", "minimum": 1}},
                "required": ["snippet_id"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_PAGE_DATA,
            title="Weekly snippets page data",
            description="GET /weekly-snippets/page-data 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"id": {"type": "integer", "minimum": 1}},
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_GET,
            title="Get weekly snippet",
            description="GET /weekly-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"snippet_id": {"type": "integer", "minimum": 1}},
                "required": ["snippet_id"],
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_LIST,
            title="List weekly snippets",
            description="GET /weekly-snippets 대응 툴",
            input_schema={
                "type": "object",
                "properties": {
                    **pagination_schema,
                    "order": {"type": "string", "enum": ["asc", "desc"]},
                    "from_week": {"type": "string", "format": "date"},
                    "to_week": {"type": "string", "format": "date"},
                    "id": {"type": "integer", "minimum": 1},
                    "q": {"type": "string"},
                    "scope": {"type": "string", "enum": ["own", "team"]},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_CREATE,
            title="Create weekly snippet",
            description="POST /weekly-snippets 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_ORGANIZE,
            title="Organize weekly snippet",
            description="POST /weekly-snippets/organize 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"content": {"type": "string"}},
                "required": ["content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_FEEDBACK,
            title="Generate weekly feedback",
            description="GET /weekly-snippets/feedback 대응 툴",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_UPDATE,
            title="Update weekly snippet",
            description="PUT /weekly-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {
                    "snippet_id": {"type": "integer", "minimum": 1},
                    "content": {"type": "string"},
                },
                "required": ["snippet_id", "content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_WEEKLY_DELETE,
            title="Delete weekly snippet",
            description="DELETE /weekly-snippets/{snippet_id} 대응 툴",
            input_schema={
                "type": "object",
                "properties": {"snippet_id": {"type": "integer", "minimum": 1}},
                "required": ["snippet_id"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_COMMENT_LIST,
            title="List comments",
            description="GET /comments?daily_snippet_id=N 또는 ?weekly_snippet_id=N 대응 툴. daily_snippet_id 또는 weekly_snippet_id 중 하나만 제공해야 합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "daily_snippet_id": {"type": "integer", "minimum": 1},
                    "weekly_snippet_id": {"type": "integer", "minimum": 1},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_COMMENT_CREATE,
            title="Create comment",
            description="POST /comments 대응 툴. daily_snippet_id 또는 weekly_snippet_id 중 하나만 제공해야 합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                    "daily_snippet_id": {"type": "integer", "minimum": 1},
                    "weekly_snippet_id": {"type": "integer", "minimum": 1},
                    "comment_type": {"type": "string", "enum": ["peer", "professor"]},
                },
                "required": ["content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_COMMENT_UPDATE,
            title="Update comment",
            description="PUT /comments/{comment_id} 대응 툴. 작성자 본인만 수정 가능합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "comment_id": {"type": "integer", "minimum": 1},
                    "content": {"type": "string"},
                },
                "required": ["comment_id", "content"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_COMMENT_DELETE,
            title="Delete comment",
            description="DELETE /comments/{comment_id} 대응 툴. 작성자 본인만 삭제 가능합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "comment_id": {"type": "integer", "minimum": 1},
                },
                "required": ["comment_id"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        # Notifications
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_LIST,
            title="List notifications",
            description="GET /notifications 대응 툴. 내 알림 목록을 페이지네이션으로 조회합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100},
                    "offset": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_UNREAD_COUNT,
            title="Unread notification count",
            description="GET /notifications/unread-count 대응 툴. 읽지 않은 알림 수를 반환합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_READ,
            title="Mark notification as read",
            description="PATCH /notifications/{notification_id}/read 대응 툴. 개별 알림을 읽음 처리합니다.",
            input_schema={
                "type": "object",
                "properties": {"notification_id": {"type": "integer", "minimum": 1}},
                "required": ["notification_id"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_READ_ALL,
            title="Mark all notifications as read",
            description="PATCH /notifications/read-all 대응 툴. 모든 알림을 읽음 처리합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_GET_SETTINGS,
            title="Get notification settings",
            description="GET /notifications/settings 대응 툴. 내 알림 설정을 조회합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_NOTIFICATION_UPDATE_SETTINGS,
            title="Update notification settings",
            description="PATCH /notifications/settings 대응 툴. 알림 설정을 수정합니다. 변경할 항목만 전달합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "notify_post_author": {"type": "boolean"},
                    "notify_mentions": {"type": "boolean"},
                    "notify_participants": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
            read_only=False,
        ),
        # Meeting rooms
        _build_tool(
            name=MCP_TOOL_MEETING_ROOM_LIST,
            title="List meeting rooms",
            description="GET /meeting-rooms 대응 툴. 예약 가능한 회의실 목록을 조회합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_MEETING_ROOM_RESERVATIONS,
            title="List meeting room reservations",
            description="GET /meeting-rooms/{room_id}/reservations 대응 툴. 특정 날짜의 회의실 예약 현황을 조회합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "minimum": 1},
                    "date": {"type": "string", "format": "date", "description": "YYYY-MM-DD 형식"},
                },
                "required": ["room_id", "date"],
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_MEETING_ROOM_RESERVE,
            title="Reserve meeting room",
            description="POST /meeting-rooms/{room_id}/reservations 대응 툴. 회의실을 예약합니다.",
            input_schema={
                "type": "object",
                "properties": {
                    "room_id": {"type": "integer", "minimum": 1},
                    "start_at": {"type": "string", "description": "ISO 8601 datetime (예: 2026-03-20T09:00:00+09:00)"},
                    "end_at": {"type": "string", "description": "ISO 8601 datetime (예: 2026-03-20T10:00:00+09:00)"},
                    "purpose": {"type": "string"},
                },
                "required": ["room_id", "start_at", "end_at"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        _build_tool(
            name=MCP_TOOL_MEETING_ROOM_CANCEL,
            title="Cancel meeting room reservation",
            description="DELETE /meeting-rooms/reservations/{reservation_id} 대응 툴. 예약을 취소합니다. 본인 또는 어드민만 가능합니다.",
            input_schema={
                "type": "object",
                "properties": {"reservation_id": {"type": "integer", "minimum": 1}},
                "required": ["reservation_id"],
                "additionalProperties": False,
            },
            read_only=False,
        ),
        # Achievements
        _build_tool(
            name=MCP_TOOL_ACHIEVEMENT_ME,
            title="My achievements",
            description="GET /achievements/me 대응 툴. 내 업적 목록을 조회합니다.",
            input_schema={"type": "object", "properties": {}, "additionalProperties": False},
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_ACHIEVEMENT_RECENT,
            title="Recent achievements",
            description="GET /achievements/recent 대응 툴. 최근 공개 업적 획득 목록을 조회합니다.",
            input_schema={
                "type": "object",
                "properties": {"limit": {"type": "integer", "minimum": 1, "maximum": 100}},
                "additionalProperties": False,
            },
            read_only=True,
        ),
        # Users (privileged)
        _build_tool(
            name=MCP_TOOL_USERS_LIST,
            title="List students",
            description="GET /students 대응 툴. 학생 목록을 조회합니다. 교수/어드민 권한 필요.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "offset": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_USERS_SEARCH,
            title="Search students",
            description="GET /students/search 대응 툴. 학생을 검색합니다. 교수/어드민 권한 필요.",
            input_schema={
                "type": "object",
                "properties": {
                    "q": {"type": "string", "description": "검색어"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 50},
                },
                "required": ["q"],
                "additionalProperties": False,
            },
            read_only=True,
        ),
        _build_tool(
            name=MCP_TOOL_USERS_TEAMS,
            title="List teams",
            description="GET /teams 대응 툴. 팀 목록을 조회합니다. 교수/어드민 권한 필요.",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "minimum": 1, "maximum": 200},
                    "offset": {"type": "integer", "minimum": 0},
                },
                "additionalProperties": False,
            },
            read_only=True,
        ),
    ]


@_mcp_server.call_tool(validate_input=False)
async def call_mcp_tool(name: str, arguments: dict[str, Any] | None) -> mcp_types.CallToolResult | dict[str, Any]:
    dispatch_start = perf_counter()
    if arguments is not None and not isinstance(arguments, dict):
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text="Invalid arguments: object expected")],
            isError=True,
        )

    args = arguments or {}
    handlers: dict[str, Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]] = {
        MCP_TOOL_DAILY_PAGE_DATA: _run_daily_page_data,
        MCP_TOOL_DAILY_GET: _run_daily_get,
        MCP_TOOL_DAILY_LIST: _run_daily_list,
        MCP_TOOL_DAILY_CREATE: _run_daily_create,
        MCP_TOOL_DAILY_ORGANIZE: _run_daily_organize,
        MCP_TOOL_DAILY_FEEDBACK: _run_daily_feedback,
        MCP_TOOL_DAILY_UPDATE: _run_daily_update,
        MCP_TOOL_DAILY_DELETE: _run_daily_delete,
        MCP_TOOL_WEEKLY_PAGE_DATA: _run_weekly_page_data,
        MCP_TOOL_WEEKLY_GET: _run_weekly_get,
        MCP_TOOL_WEEKLY_LIST: _run_weekly_list,
        MCP_TOOL_WEEKLY_CREATE: _run_weekly_create,
        MCP_TOOL_WEEKLY_ORGANIZE: _run_weekly_organize,
        MCP_TOOL_WEEKLY_FEEDBACK: _run_weekly_feedback,
        MCP_TOOL_WEEKLY_UPDATE: _run_weekly_update,
        MCP_TOOL_WEEKLY_DELETE: _run_weekly_delete,
        MCP_TOOL_COMMENT_LIST: _run_comment_list,
        MCP_TOOL_COMMENT_CREATE: _run_comment_create,
        MCP_TOOL_COMMENT_UPDATE: _run_comment_update,
        MCP_TOOL_COMMENT_DELETE: _run_comment_delete,
        MCP_TOOL_NOTIFICATION_LIST: _run_notifications_list,
        MCP_TOOL_NOTIFICATION_UNREAD_COUNT: _run_notifications_unread_count,
        MCP_TOOL_NOTIFICATION_READ: _run_notifications_read,
        MCP_TOOL_NOTIFICATION_READ_ALL: _run_notifications_read_all,
        MCP_TOOL_NOTIFICATION_GET_SETTINGS: _run_notifications_get_settings,
        MCP_TOOL_NOTIFICATION_UPDATE_SETTINGS: _run_notifications_update_settings,
        MCP_TOOL_MEETING_ROOM_LIST: _run_meeting_rooms_list,
        MCP_TOOL_MEETING_ROOM_RESERVATIONS: _run_meeting_rooms_reservations,
        MCP_TOOL_MEETING_ROOM_RESERVE: _run_meeting_rooms_reserve,
        MCP_TOOL_MEETING_ROOM_CANCEL: _run_meeting_rooms_cancel,
        MCP_TOOL_ACHIEVEMENT_ME: _run_achievements_me,
        MCP_TOOL_ACHIEVEMENT_RECENT: _run_achievements_recent,
        MCP_TOOL_USERS_LIST: _run_users_list,
        MCP_TOOL_USERS_SEARCH: _run_users_search,
        MCP_TOOL_USERS_TEAMS: _run_users_teams,
    }

    handler = handlers.get(name)
    if handler is None:
        logger.warning(
            "mcp.tool.dispatch",
            extra={
                "event": "mcp.tool.dispatch",
                "tool_name": name,
                "status": "error",
                "elapsed_ms": round((perf_counter() - dispatch_start) * 1000, 2),
                "error_type": "UnknownTool",
            },
        )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=f"Unknown tool: {name}")],
            isError=True,
        )

    try:
        result = await handler(args)
        logger.info(
            "mcp.tool.dispatch",
            extra={
                "event": "mcp.tool.dispatch",
                "tool_name": name,
                "status": "ok",
                "elapsed_ms": round((perf_counter() - dispatch_start) * 1000, 2),
            },
        )
        return result
    except HTTPException as exc:
        logger.warning(
            "mcp.tool.dispatch",
            extra={
                "event": "mcp.tool.dispatch",
                "tool_name": name,
                "status": "error",
                "elapsed_ms": round((perf_counter() - dispatch_start) * 1000, 2),
                "error_type": type(exc).__name__,
                "http_status": exc.status_code,
            },
        )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=f"HTTP {exc.status_code}: {exc.detail}")],
            isError=True,
        )
    except (ValueError, TypeError, RuntimeError) as exc:
        logger.warning(
            "mcp.tool.dispatch",
            extra={
                "event": "mcp.tool.dispatch",
                "tool_name": name,
                "status": "error",
                "elapsed_ms": round((perf_counter() - dispatch_start) * 1000, 2),
                "error_type": type(exc).__name__,
            },
        )
        return mcp_types.CallToolResult(
            content=[mcp_types.TextContent(type="text", text=f"Invalid arguments: {exc}")],
            isError=True,
        )


@_mcp_server.list_resources()
async def list_mcp_resources() -> list[mcp_types.Resource]:
    return [
        mcp_types.Resource(
            uri=mcp_types.AnyUrl(MCP_RESOURCE_MY_PROFILE),
            name="my-profile",
            title="My profile",
            description="인증 사용자 프로필과 기본 리그 정보를 제공합니다.",
            mimeType="application/json",
        ),
        mcp_types.Resource(
            uri=mcp_types.AnyUrl(MCP_RESOURCE_MY_ACHIEVEMENTS),
            name="my-achievements",
            title="My achievements",
            description="인증 사용자의 achievement 요약을 제공합니다.",
            mimeType="application/json",
        ),
    ]


@_mcp_server.read_resource()
async def read_mcp_resource(uri: Any) -> list[ReadResourceContents]:
    uri_str = str(uri)

    if uri_str == MCP_RESOURCE_MY_PROFILE:
        payload = await _load_my_profile()
    elif uri_str == MCP_RESOURCE_MY_ACHIEVEMENTS:
        payload = await _load_my_achievements()
    else:
        raise ValueError(f"Unknown resource: {uri_str}")

    return [
        ReadResourceContents(
            content=json.dumps(payload, ensure_ascii=False, indent=2),
            mime_type="application/json",
        )
    ]


@asynccontextmanager
async def _mcp_lifespan(app: Any) -> AsyncIterator[None]:
    session_manager = StreamableHTTPSessionManager(app=_mcp_server)
    app.state.mcp_session_manager = session_manager
    app.state.mcp_session_owner = {}
    async with session_manager.run():
        yield

    if hasattr(app.state, "mcp_session_manager"):
        delattr(app.state, "mcp_session_manager")
    if hasattr(app.state, "mcp_session_owner"):
        delattr(app.state, "mcp_session_owner")


router = APIRouter(prefix="", tags=["mcp"], lifespan=_mcp_lifespan)


async def get_mcp_user_from_bearer(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> BearerAuthContext:
    return await get_bearer_auth_or_401(request, db)


@limiter.limit(settings.MCP_HTTP_STREAM_LIMIT)
async def _enforce_mcp_get_limit(request: Request) -> None:
    return None


@limiter.limit(settings.MCP_HTTP_MESSAGES_LIMIT)
async def _enforce_mcp_mutation_limit(request: Request) -> None:
    return None


async def _apply_mcp_rate_limit(request: Request) -> None:
    if request.method in {"GET", "HEAD"}:
        await _enforce_mcp_get_limit(request=request)
        return

    if request.method in {"POST", "DELETE"}:
        await _enforce_mcp_mutation_limit(request=request)


def _get_session_manager(request: Request) -> StreamableHTTPSessionManager:
    session_manager = getattr(request.app.state, "mcp_session_manager", None)
    if session_manager is None:
        raise HTTPException(status_code=503, detail="MCP server unavailable")
    return session_manager


async def _authorize_request(request: Request, db: AsyncSession) -> None:
    auth_context = await get_mcp_user_from_bearer(request=request, db=db)
    request.state.mcp_user = auth_context.user
    request.state.mcp_api_token = auth_context.api_token


async def _handle_mcp_transport_request(scope: Scope, receive: Receive, send: Send) -> None:
    request = Request(scope, receive=receive)
    await _apply_mcp_rate_limit(request)

    async with AsyncSessionLocal() as db:
        await _authorize_request(request, db)

        session_id = request.headers.get(MCP_SESSION_ID_HEADER)
        session_owner_map = getattr(request.app.state, "mcp_session_owner", None)

        if session_id is not None:
            if not isinstance(session_owner_map, dict):
                raise HTTPException(status_code=503, detail="MCP session registry unavailable")

            owner_user_id = session_owner_map.get(session_id)
            if owner_user_id is None:
                raise HTTPException(status_code=404, detail="Session not found")
            if owner_user_id != request.state.mcp_user.id:
                raise HTTPException(status_code=403, detail="Forbidden")

        request.state.mcp_db = db
        request.state.mcp_now = get_request_now(request)

        response_session_id: str | None = None

        async def send_with_session_capture(message: dict[str, Any]) -> None:
            nonlocal response_session_id
            if message.get("type") == "http.response.start":
                for raw_name, raw_value in message.get("headers", []):
                    if raw_name.lower() == MCP_SESSION_ID_HEADER.encode("latin-1"):
                        response_session_id = raw_value.decode("latin-1")
                        break
            await send(message)

        session_manager = _get_session_manager(request)
        await session_manager.handle_request(scope, receive, send_with_session_capture)

        if (
            session_id is None
            and response_session_id
            and isinstance(session_owner_map, dict)
            and request.method == "POST"
        ):
            session_owner_map[response_session_id] = request.state.mcp_user.id

        if (
            session_id is not None
            and request.method == "DELETE"
            and isinstance(session_owner_map, dict)
        ):
            session_owner_map.pop(session_id, None)


class MCPHTTPTransportApp:
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await _handle_mcp_transport_request(scope, receive, send)


mcp_http_transport_app = MCPHTTPTransportApp()
router.add_route("/mcp", endpoint=mcp_http_transport_app, methods=["GET", "POST", "DELETE", "HEAD"])
