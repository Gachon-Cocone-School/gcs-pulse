from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    DailySnippetCreate,
    DailySnippetFeedbackResponse,
    DailySnippetListResponse,
    DailySnippetOrganizeRequest,
    DailySnippetOrganizeResponse,
    DailySnippetPageDataResponse,
    DailySnippetResponse,
    DailySnippetUpdate,
)
from app.utils_time import current_business_key
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.routers import snippet_flow_helpers as _flow
from app.routers import snippet_utils
from app.limiter import limiter
from app.core.config import settings
from app.dependencies import verify_csrf

router = APIRouter(prefix="/daily-snippets", tags=["daily-snippets"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)


@router.get("/page-data", response_model=DailySnippetPageDataResponse)
async def get_daily_snippet_page_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    server_key = current_business_key("daily", now)

    async def _list_daily_for_range(*, db, viewer, order, from_key, to_key):
        return await crud.list_daily_snippets(
            db,
            viewer=viewer,
            limit=1,
            offset=0,
            order=order,
            from_date=from_key,
            to_date=to_key,
            q=None,
            scope="own",
        )

    return await snippet_utils.build_snippet_page_data(
        db=db,
        viewer=viewer,
        request=request,
        snippet_id=id,
        server_key=server_key,
        kind="daily",
        key_attr="date",
        key_step=timedelta(days=1),
        get_snippet_by_id=crud.get_daily_snippet_by_id,
        list_snippets_for_range=_list_daily_for_range,
    )


@router.get("/{snippet_id:int}", response_model=DailySnippetResponse)
async def get_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )
    _flow.ensure_snippet_readable_or_403(
        viewer,
        owner,
        can_read_snippet=snippet_utils.can_read_snippet,
    )

    snippet_utils.set_snippet_editable(
        snippet,
        viewer,
        owner,
        "daily",
        "date",
        request,
    )

    return snippet


@router.get("", response_model=DailySnippetListResponse)
async def list_daily_snippets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
    from_date: str | None = None,
    to_date: str | None = None,
    id: int | None = None,
    q: str | None = None,
    scope: str = "own",
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    parsed_from = datetime.fromisoformat(from_date).date() if from_date else None
    parsed_to = datetime.fromisoformat(to_date).date() if to_date else None

    # If id is provided, show the team snippets for the date of that snippet
    if id is not None:
        snippet = await crud.get_daily_snippet_by_id(db, id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        parsed_from = parsed_to = snippet.date
        scope = "team"

    if parsed_from is None and parsed_to is None:
        now = snippet_utils.get_request_now(request)
        today = current_business_key("daily", now)
        parsed_from = parsed_to = today

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

    await snippet_utils.apply_editable_to_snippet_list(
        db,
        items,
        viewer,
        "daily",
        "date",
        request,
    )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=DailySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def create_daily_snippet(
    request: Request,
    payload: DailySnippetCreate,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    # Upsert logic
    return await crud.upsert_daily_snippet(
        db,
        user_id=viewer.id,
        snippet_date=snippet_date,
        content=payload.content,
    )


@router.post("/organize", response_model=DailySnippetOrganizeResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def organize_daily_snippet(
    payload: DailySnippetOrganizeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    snippet = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, snippet_date)
    playbook_content = snippet.playbook if snippet else None

    raw_content = payload.content
    if raw_content.strip():
        source_content = raw_content
        organized_content = await snippet_utils.organize_content_with_ai(raw_content, copilot)
    else:
        previous_date = snippet_date - timedelta(days=1)
        previous = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, previous_date)
        previous_context = previous.content.strip() if previous else ""

        source_content = _flow.build_daily_suggestion_source(snippet_date, previous_context)
        organized_content = await snippet_utils.organize_content_with_ai(
            source_content,
            copilot,
            prompt_name="suggest_daily_from_previous.md",
        )

    feedback_json = await _flow.generate_feedback_json_or_none(
        daily_snippet_content=source_content,
        organized_content=organized_content,
        playbook_content=playbook_content,
        copilot=copilot,
        generate_feedback_with_ai=snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=snippet_utils.parse_feedback_json,
        logger=logger,
    )

    return DailySnippetOrganizeResponse(
        date=snippet_date,
        organized_content=organized_content,
        feedback=feedback_json,
    )


@router.get("/feedback", response_model=DailySnippetFeedbackResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def generate_daily_snippet_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    snippet = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, snippet_date)
    content = _flow.require_snippet_content_or_400(snippet)

    playbook_content = snippet.playbook

    feedback_json = await _flow.generate_feedback_json_or_none(
        daily_snippet_content=content,
        organized_content=content,
        playbook_content=playbook_content,
        copilot=copilot,
        generate_feedback_with_ai=snippet_utils.generate_feedback_with_ai,
        parse_feedback_json=snippet_utils.parse_feedback_json,
        logger=logger,
    )

    await _flow.persist_snippet_feedback(db, snippet, feedback_json)

    return DailySnippetFeedbackResponse(
        date=snippet_date,
        feedback=feedback_json,
    )


@router.put("/{snippet_id:int}", response_model=DailySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def update_daily_snippet(
    snippet_id: int,
    payload: DailySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=snippet_utils.is_snippet_editable,
    )

    return await crud.update_daily_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id:int}")
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def delete_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=snippet_utils.is_snippet_editable,
    )

    await crud.delete_daily_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
