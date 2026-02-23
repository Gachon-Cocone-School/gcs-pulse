from datetime import datetime
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import CommentCreate, CommentResponse, CommentUpdate
from app.routers import snippet_utils
from app.limiter import limiter
from app.core.config import settings
from app.dependencies import verify_csrf

router = APIRouter(prefix="/comments", tags=["comments"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)


@router.post("", response_model=CommentResponse)
@limiter.limit(settings.COMMENTS_WRITE_LIMIT)
async def create_comment(
    request: Request,
    payload: CommentCreate,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db, include_consents=False)

    # Validate that exactly one snippet ID is provided
    if not (bool(payload.daily_snippet_id) ^ bool(payload.weekly_snippet_id)):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of daily_snippet_id or weekly_snippet_id must be provided",
        )

    # Check snippet existence and permissions
    if payload.daily_snippet_id:
        snippet = await crud.get_daily_snippet_by_id(db, payload.daily_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Daily snippet not found")

        # Check if viewer can see the snippet (same team or owner)
        owner = snippet.user
        if not snippet_utils.can_read_snippet(viewer, owner):
            raise HTTPException(status_code=403, detail="Access denied")

    elif payload.weekly_snippet_id:
        snippet = await crud.get_weekly_snippet_by_id(db, payload.weekly_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Weekly snippet not found")

        owner = snippet.user
        if not snippet_utils.can_read_snippet(viewer, owner):
            raise HTTPException(status_code=403, detail="Access denied")

    return await crud.create_comment(
        db,
        user_id=viewer.id,
        content=payload.content,
        daily_snippet_id=payload.daily_snippet_id,
        weekly_snippet_id=payload.weekly_snippet_id,
    )


@router.get("", response_model=List[CommentResponse])
async def list_comments(
    request: Request,
    daily_snippet_id: Optional[int] = Query(None),
    weekly_snippet_id: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db, include_consents=False)

    if not (bool(daily_snippet_id) ^ bool(weekly_snippet_id)):
        raise HTTPException(
            status_code=400,
            detail="Exactly one of daily_snippet_id or weekly_snippet_id must be provided",
        )

    if daily_snippet_id:
        snippet = await crud.get_daily_snippet_by_id(db, daily_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Daily snippet not found")

        owner = snippet.user
        if not snippet_utils.can_read_snippet(viewer, owner):
            raise HTTPException(status_code=403, detail="Access denied")

        return await crud.list_comments(db, daily_snippet_id=daily_snippet_id)

    elif weekly_snippet_id:
        snippet = await crud.get_weekly_snippet_by_id(db, weekly_snippet_id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Weekly snippet not found")

        owner = snippet.user
        if not snippet_utils.can_read_snippet(viewer, owner):
            raise HTTPException(status_code=403, detail="Access denied")

        return await crud.list_comments(db, weekly_snippet_id=weekly_snippet_id)

    return []


@router.put("/{comment_id}", response_model=CommentResponse)
@limiter.limit(settings.COMMENTS_WRITE_LIMIT)
async def update_comment(
    comment_id: int,
    payload: CommentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db, include_consents=False)

    comment = await crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    if comment.user_id != viewer.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this comment")

    return await crud.update_comment(db, comment, payload.content)


@router.delete("/{comment_id}")
@limiter.limit(settings.COMMENTS_WRITE_LIMIT)
async def delete_comment(
    comment_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_viewer_or_401(request, db, include_consents=False)

    comment = await crud.get_comment_by_id(db, comment_id)
    if not comment:
        raise HTTPException(status_code=404, detail="Comment not found")

    # Allow author or admins/team leads (logic can be expanded later)
    # For now, strictly author
    if comment.user_id != viewer.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this comment")

    await crud.delete_comment(db, comment)
    return {"message": "Comment deleted"}
