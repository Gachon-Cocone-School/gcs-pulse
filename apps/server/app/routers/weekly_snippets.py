from datetime import datetime
import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    WeeklySnippetCreate,
    WeeklySnippetListResponse,
    WeeklySnippetOrganizeResponse,
    WeeklySnippetResponse,
    WeeklySnippetUpdate,
)
from app.utils_time import current_business_week_start, validate_snippet_week
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient

router = APIRouter(prefix="/weekly-snippets", tags=["weekly-snippets"])
logger = logging.getLogger(__name__)


def _get_user_sub(request: Request) -> str:
    sub = request.session.get("user", {}).get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sub


def _can_read(viewer, owner) -> bool:
    # allow owner to read snippets
    if viewer.id == owner.id:
        return True
    return False


def _require_owner_write(viewer, owner) -> None:
    # Only the owner may write (create/update/delete) their own snippets
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


@router.get("/{snippet_id}", response_model=WeeklySnippetResponse)
async def get_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not _can_read(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

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
    q: str | None = None,
    scope: str = "own",
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    parsed_from = datetime.fromisoformat(from_week).date() if from_week else None
    parsed_to = datetime.fromisoformat(to_week).date() if to_week else None

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

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=WeeklySnippetResponse)
async def create_weekly_snippet(
    payload: WeeklySnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    now = datetime.now().astimezone()
    week = current_business_week_start(now)

    return await crud.upsert_weekly_snippet(
        db,
        user_id=viewer.id,
        week=week,
        content=payload.content,
    )


from app.routers import snippet_utils

@router.post("/organize", response_model=WeeklySnippetOrganizeResponse)
async def organize_weekly_snippet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    now = datetime.now().astimezone()
    week = current_business_week_start(now)

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    if not snippet:
        raise HTTPException(status_code=404, detail="Weekly snippet not found")

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

        await crud.update_weekly_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
            playbook=playbook_update,
            feedback=feedback_json,
        )
    except json.JSONDecodeError:
        logger.error(f"Failed to parse AI feedback JSON: {feedback_json}")
        await crud.update_weekly_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
        )

    await db.refresh(snippet)
    
    response = WeeklySnippetOrganizeResponse.model_validate(snippet)
    response.feedback = feedback_data
    return response


@router.put("/{snippet_id}", response_model=WeeklySnippetResponse)
async def update_weekly_snippet(
    snippet_id: int,
    payload: WeeklySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    _require_owner_write(viewer, owner)
    now = datetime.now().astimezone()
    validate_snippet_week(snippet.week, now)

    return await crud.update_weekly_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id}")
async def delete_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    sub = _get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    _require_owner_write(viewer, owner)
    now = datetime.now().astimezone()
    validate_snippet_week(snippet.week, now)

    await crud.delete_weekly_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
