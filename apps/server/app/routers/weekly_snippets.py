from datetime import datetime
import logging

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
from app.utils_time import current_business_key
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient

router = APIRouter(prefix="/weekly-snippets", tags=["weekly-snippets"])
logger = logging.getLogger(__name__)


def _can_read(viewer, owner) -> bool:
    # allow owner to read snippets
    if viewer.id == owner.id:
        return True
    return False


def _require_owner_write(viewer, owner) -> None:
    # Only the owner may write (create/update/delete) their own snippets
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


from app.routers import snippet_utils as _snippet_utils


@router.get("/{snippet_id}", response_model=WeeklySnippetResponse)
async def get_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not _can_read(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        setattr(snippet, "editable", _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request))
    except Exception:
        setattr(snippet, "editable", False)

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
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

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

    # attach editable flag per item
    for s in items:
        try:
            owner = await crud.get_user_by_id(db, s.user_id)
            setattr(s, "editable", _snippet_utils.is_snippet_editable(viewer, owner, s.week, "weekly", request=request))
        except Exception:
            setattr(s, "editable", False)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=WeeklySnippetResponse)
async def create_weekly_snippet(
    payload: WeeklySnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    return await crud.upsert_weekly_snippet(
        db,
        user_id=viewer.id,
        week=week,
        content=payload.content,
    )


@router.post("/organize", response_model=WeeklySnippetOrganizeResponse)
async def organize_weekly_snippet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    if not snippet:
        raise HTTPException(status_code=404, detail="Weekly snippet not found")

    organized_content = await _snippet_utils.organize_content_with_ai(snippet.content, copilot)

    feedback_json = await _snippet_utils.generate_feedback_with_ai(
        daily_snippet_content=snippet.content,
        organized_content=organized_content,
        playbook_content=snippet.playbook,
        copilot=copilot,
    )

    import json

    try:
        parsed_feedback = json.loads(feedback_json)
        playbook_update = parsed_feedback.get("playbook_update_markdown")

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
    return WeeklySnippetOrganizeResponse.model_validate(snippet)


@router.put("/{snippet_id}", response_model=WeeklySnippetResponse)
async def update_weekly_snippet(
    snippet_id: int,
    payload: WeeklySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

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


@router.delete("/{snippet_id}")
async def delete_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_viewer_or_401(request, db)

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
