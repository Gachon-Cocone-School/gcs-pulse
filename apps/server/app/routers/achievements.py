from fastapi import APIRouter, Depends, Query
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.database import get_db
from app.dependencies import get_active_user
from app.models import User
from app.routers.snippet_utils import get_request_now

router = APIRouter(prefix="/achievements", tags=["achievements"])


@router.get("/me", response_model=schemas.MyAchievementGroupsResponse)
async def get_my_achievements(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    items = await crud.list_my_achievement_groups(db, user_id=user.id)
    return {
        "items": items,
        "total": len(items),
    }


@router.get("/recent", response_model=schemas.RecentAchievementGrantsResponse)
async def get_recent_achievements(
    request: Request,
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    now = get_request_now(request)
    items, total = await crud.list_recent_public_achievement_grants(db, now=now, limit=limit)
    return {
        "items": items,
        "total": total,
        "limit": limit,
    }
