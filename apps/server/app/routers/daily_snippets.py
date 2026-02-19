from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    DailySnippetCreate,
    DailySnippetListResponse,
    DailySnippetOrganizeResponse,
    DailySnippetResponse,
    DailySnippetUpdate,
)
from app.utils_time import current_business_key, validate_snippet_date
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.routers import snippet_utils

router = APIRouter(prefix="/daily-snippets", tags=["daily-snippets"])
logger = logging.getLogger(__name__)


@router.get("/{snippet_id}", response_model=DailySnippetResponse)
async def get_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not snippet_utils.can_read_snippet(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

    # attach editable flag for client
    try:
        setattr(snippet, "editable", snippet_utils.is_snippet_editable(viewer, owner, snippet.date, "daily", request=request))
    except Exception:
        # be conservative on error
        setattr(snippet, "editable", False)

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

    # attach editable flag to each item
    for s in items:
        try:
            owner = await crud.get_user_by_id(db, s.user_id)
            setattr(s, "editable", snippet_utils.is_snippet_editable(viewer, owner, s.date, "daily", request=request))
        except Exception:
            setattr(s, "editable", False)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=DailySnippetResponse)
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
async def organize_daily_snippet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    snippet = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, snippet_date)
    if not snippet:
        raise HTTPException(status_code=404, detail="Daily snippet not found")

    organized_content = await snippet_utils.organize_content_with_ai(snippet.content, copilot)

    feedback_json = await snippet_utils.generate_feedback_with_ai(
        daily_snippet_content=snippet.content,
        organized_content=organized_content,
        playbook_content=snippet.playbook,
        copilot=copilot,
    )

    import json

    try:
        parsed_feedback = json.loads(feedback_json)
        playbook_update = parsed_feedback.get("playbook_update_markdown")

        await crud.update_daily_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
            playbook=playbook_update,
            feedback=feedback_json,
        )
    except json.JSONDecodeError:
        logger.error(f"Failed to parse AI feedback JSON: {feedback_json}")
        await crud.update_daily_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
        )

    await db.refresh(snippet)
    return DailySnippetOrganizeResponse.model_validate(snippet)


@router.put("/{snippet_id}", response_model=DailySnippetResponse)
async def update_daily_snippet(
    snippet_id: int,
    payload: DailySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not snippet_utils.is_snippet_editable(viewer, owner, snippet.date, "daily", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

    return await crud.update_daily_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id}")
async def delete_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not snippet_utils.is_snippet_editable(viewer, owner, snippet.date, "daily", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

    await crud.delete_daily_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
