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
from app.utils_time import current_business_date, validate_snippet_date
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.routers import snippet_utils

router = APIRouter(prefix="/daily-snippets", tags=["daily-snippets"])
logger = logging.getLogger(__name__)


@router.get("/{snippet_id}", response_model=DailySnippetResponse)
async def get_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not snippet_utils.can_read_snippet(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

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
    q: str | None = None,
    scope: str = "own",
):
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    parsed_from = datetime.fromisoformat(from_date).date() if from_date else None
    parsed_to = datetime.fromisoformat(to_date).date() if to_date else None
    if parsed_from is None and parsed_to is None:
        now = datetime.now().astimezone()
        today = current_business_date(now)
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

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=DailySnippetResponse)
async def create_daily_snippet(
    request: Request,
    payload: DailySnippetCreate, 
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    now = datetime.now().astimezone()
    snippet_date = current_business_date(now)

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
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    now = datetime.now().astimezone()
    snippet_date = current_business_date(now)

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

    feedback_data = None
    try:
        feedback_data = json.loads(feedback_json)
        playbook_update = feedback_data.get("playbook_update_markdown")

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
    
    response = DailySnippetOrganizeResponse.model_validate(snippet)
    response.feedback = feedback_data
    return response


@router.put("/{snippet_id}", response_model=DailySnippetResponse)
async def update_daily_snippet(
    snippet_id: int,
    payload: DailySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    snippet_utils.require_snippet_owner_write(viewer, owner)
    now = datetime.now().astimezone()
    validate_snippet_date(snippet.date, now)

    return await crud.update_daily_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id}")
async def delete_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    snippet_utils.require_snippet_owner_write(viewer, owner)
    now = datetime.now().astimezone()
    validate_snippet_date(snippet.date, now)

    await crud.delete_daily_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
