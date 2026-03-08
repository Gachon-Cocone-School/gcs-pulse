from datetime import datetime, timedelta
import logging
from time import perf_counter

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    WeeklySnippetCreate,
    WeeklySnippetFeedbackResponse,
    WeeklySnippetListResponse,
    WeeklySnippetOrganizeRequest,
    WeeklySnippetOrganizeResponse,
    WeeklySnippetPageDataResponse,
    WeeklySnippetResponse,
    WeeklySnippetUpdate,
)
from app.utils_time import current_business_key
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.limiter import limiter
from app.core.config import settings
from app.dependencies import verify_csrf
from app.routers import snippet_flow_helpers as _flow
from app.routers import snippet_utils as _snippet_utils

router = APIRouter(prefix="/weekly-snippets", tags=["weekly-snippets"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)


def _can_read(viewer, owner) -> bool:
    return _snippet_utils.can_read_snippet(viewer, owner)


@router.get("/page-data", response_model=WeeklySnippetPageDataResponse)
async def get_weekly_snippet_page_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
):
    return await _flow.build_snippet_page_data_response(
        request=request,
        db=db,
        snippet_id=id,
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
        can_read_snippet_fn=_can_read,
    )


@router.get("/{snippet_id:int}", response_model=WeeklySnippetResponse)
async def get_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_readable_or_403(
        viewer,
        owner,
        can_read_snippet=_can_read,
    )

    _snippet_utils.set_snippet_editable(
        snippet,
        viewer,
        owner,
        "weekly",
        "week",
        request,
    )

    return snippet


@router.get("", response_model=WeeklySnippetListResponse)
async def list_weekly_snippets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
    from_week: str | None = None,
    to_week: str | None = None,
    id: int | None = None,
    q: str | None = None,
    scope: str = "own",
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    async def _get_snippet_by_id(snippet_id: int):
        return await crud.get_weekly_snippet_by_id(db, snippet_id)

    parsed_from, parsed_to, scope = await _flow.resolve_list_range_and_scope(
        from_key=from_week,
        to_key=to_week,
        snippet_id=id,
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

    await _snippet_utils.apply_editable_to_snippet_list(
        db,
        items,
        viewer,
        "weekly",
        "week",
        request,
    )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=WeeklySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def create_weekly_snippet(
    payload: WeeklySnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    return await _flow.create_snippet_for_current_key(
        request=request,
        db=db,
        content=payload.content,
        kind="weekly",
        key_arg_name="week",
        get_snippet_viewer_or_401=_snippet_utils.get_snippet_viewer_or_401,
        get_request_now=_snippet_utils.get_request_now,
        current_business_key=current_business_key,
        upsert_snippet=crud.upsert_weekly_snippet,
    )


@router.post("/organize", response_model=WeeklySnippetOrganizeResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def organize_weekly_snippet(
    payload: WeeklySnippetOrganizeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    total_start = perf_counter()
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    profile_context = {
        "channel": "http",
        "flow": "organize",
        "snippet_kind": "weekly",
        "user_id": viewer.id,
    }

    raw_content = payload.content

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

    _, organized_content = await _flow.resolve_source_and_organized_content(
        raw_content=raw_content,
        copilot=copilot,
        organize_content_with_ai=_snippet_utils.organize_content_with_ai,
        build_suggestion_source=_build_suggestion_source,
        suggestion_prompt_name="organize_weekly.md",
        direct_prompt_name="organize_weekly.md",
        profile_context=profile_context,
        logger=logger,
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

    return WeeklySnippetOrganizeResponse(
        week=week,
        organized_content=organized_content,
    )


@router.get("/feedback", response_model=WeeklySnippetFeedbackResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def generate_weekly_snippet_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
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

    playbook_content = snippet.playbook

    feedback_json = await _flow.generate_feedback_json_or_none(
        daily_snippet_content=content,
        organized_content=content,
        playbook_content=playbook_content,
        copilot=copilot,
        generate_feedback_with_ai=_snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
    )

    await _flow.persist_snippet_feedback(db, snippet, feedback_json)

    return WeeklySnippetFeedbackResponse(
        week=week,
        feedback=feedback_json,
    )


@router.put("/{snippet_id:int}", response_model=WeeklySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def update_weekly_snippet(
    snippet_id: int,
    payload: WeeklySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.week,
        kind="weekly",
        request=request,
        is_snippet_editable=_snippet_utils.is_snippet_editable,
    )

    return await crud.update_weekly_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id:int}")
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def delete_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

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
