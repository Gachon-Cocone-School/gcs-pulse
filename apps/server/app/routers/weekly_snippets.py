from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
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

router = APIRouter(prefix="/weekly-snippets", tags=["weekly-snippets"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)


def _can_read(viewer, owner) -> bool:
    # allow owner or same-team members to read snippets (daily와 동일 정책)
    return _snippet_utils.can_read_snippet(viewer, owner)


def _require_owner_write(viewer, owner) -> None:
    # Only the owner may write (create/update/delete) their own snippets
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


from app.routers import snippet_utils as _snippet_utils


@router.get("/page-data", response_model=WeeklySnippetPageDataResponse)
async def get_weekly_snippet_page_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    server_key = current_business_key("weekly", now)

    async def _list_weekly_for_range(*, db, viewer, order, from_key, to_key):
        return await crud.list_weekly_snippets(
            db,
            viewer=viewer,
            limit=1,
            offset=0,
            order=order,
            from_week=from_key,
            to_week=to_key,
            q=None,
            scope="own",
        )

    return await _snippet_utils.build_snippet_page_data(
        db=db,
        viewer=viewer,
        request=request,
        snippet_id=id,
        server_key=server_key,
        kind="weekly",
        key_attr="week",
        key_step=timedelta(days=7),
        get_snippet_by_id=crud.get_weekly_snippet_by_id,
        list_snippets_for_range=_list_weekly_for_range,
        can_read_snippet_fn=_can_read,
    )


@router.get("/{snippet_id:int}", response_model=WeeklySnippetResponse)
async def get_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not _can_read(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

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

    parsed_from = datetime.fromisoformat(from_week).date() if from_week else None
    parsed_to = datetime.fromisoformat(to_week).date() if to_week else None

    # If id is provided, show the team snippets for the week of that snippet
    if id is not None:
        snippet = await crud.get_weekly_snippet_by_id(db, id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        parsed_from = parsed_to = snippet.week
        scope = "team"

    if parsed_from is None and parsed_to is None:
        now = _snippet_utils.get_request_now(request)
        week_start = current_business_key("weekly", now)
        parsed_from = parsed_to = week_start

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
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    return await crud.upsert_weekly_snippet(
        db,
        user_id=viewer.id,
        week=week,
        content=payload.content,
    )


@router.post("/organize", response_model=WeeklySnippetOrganizeResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def organize_weekly_snippet(
    payload: WeeklySnippetOrganizeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    playbook_content = snippet.playbook if snippet else None

    raw_content = payload.content
    if raw_content.strip():
        source_content = raw_content
        organized_content = await _snippet_utils.organize_content_with_ai(
            raw_content,
            copilot,
            prompt_name="organize_weekly.md",
        )
    else:
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

        source_content = _flow.build_weekly_suggestion_source(week, daily_items)

        organized_content = await _snippet_utils.organize_content_with_ai(
            source_content,
            copilot,
            prompt_name="organize_weekly.md",
        )

    feedback_json = await _snippet_utils.generate_feedback_with_ai(
        daily_snippet_content=source_content,
        organized_content=organized_content,
        playbook_content=playbook_content,
        copilot=copilot,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
    )

    feedback_json = _flow.parse_feedback_json_or_none(
        feedback_json,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
    )

    return WeeklySnippetOrganizeResponse(
        week=week,
        organized_content=organized_content,
        feedback=feedback_json,
    )


@router.get("/feedback", response_model=WeeklySnippetFeedbackResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def generate_weekly_snippet_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    content = _flow.require_snippet_content_or_400(snippet)

    playbook_content = snippet.playbook

    feedback_json = await _snippet_utils.generate_feedback_with_ai(
        daily_snippet_content=content,
        organized_content=content,
        playbook_content=playbook_content,
        copilot=copilot,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
    )

    feedback_json = _flow.parse_feedback_json_or_none(
        feedback_json,
        parse_feedback_json=_snippet_utils.parse_feedback_json,
        logger=logger,
    )

    setattr(snippet, "feedback", feedback_json)
    await db.commit()
    await db.refresh(snippet)

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
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

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
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

    await crud.delete_weekly_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
