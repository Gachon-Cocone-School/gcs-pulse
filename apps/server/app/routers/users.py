from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app import crud, schemas
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.lib.active_user_cache import get_active_user_cache
from app.lib.auth_me_cache import get_auth_me_cache
from app.lib.leaderboards_cache import get_leaderboards_cache
from app.dependencies import (
    get_active_user,
    require_privileged_api_role,
    verify_csrf,
)
from app.limiter import limiter
from app.models import ProxySetting, ResetState, User

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_csrf)])


@router.get("/me/league", response_model=schemas.MeLeagueResponse)
async def get_my_league(
    user: User = Depends(get_active_user),
):
    async with AsyncSessionLocal() as db:
        if user.team_id is not None:
            team = await crud.get_team_by_id(db, user.team_id)
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
            return {
                "league_type": team.league_type,
                "can_update": False,
                "managed_by_team": True,
            }

    return {
        "league_type": user.league_type,
        "can_update": True,
        "managed_by_team": False,
    }


@router.patch("/me/league", response_model=schemas.MeLeagueResponse)
@limiter.limit(settings.USERS_LEAGUE_UPDATE_LIMIT)
async def update_my_league(
    payload: schemas.LeagueUpdate,
    request: Request,
    user: User = Depends(get_active_user),
):
    async with AsyncSessionLocal() as db:
        if user.team_id is not None:
            raise HTTPException(status_code=409, detail="Team members cannot change personal league")

        db_user = await crud.get_user_by_id(db, user.id)
        if not db_user:
            raise HTTPException(status_code=404, detail="User not found")

        updated = await crud.update_user_league_type(db, db_user, payload.league_type.value)

    active_user_cache = get_active_user_cache(request)
    if active_user_cache:
        await active_user_cache.invalidate(updated.email)

    auth_me_cache = get_auth_me_cache(request)
    if auth_me_cache:
        await auth_me_cache.invalidate(updated.email)

    leaderboards_cache = get_leaderboards_cache(request)
    if leaderboards_cache:
        await leaderboards_cache.invalidate_all()

    return {
        "league_type": updated.league_type,
        "can_update": True,
        "managed_by_team": False,
    }


@router.get("/students", response_model=schemas.StudentListResponse)
async def list_students(
    limit: int = 100,
    offset: int = 0,
    user: User = Depends(get_active_user),
):
    require_privileged_api_role(user)

    async with AsyncSessionLocal() as db:
        clamped_limit = min(max(limit, 1), 200)
        clamped_offset = max(offset, 0)
        rows, total = await crud.list_students(db, limit=clamped_limit, offset=clamped_offset)

    items = [
        {
            "student_user_id": student.id,
            "student_name": student.name or student.email,
            "student_email": student.email,
            "team_name": team.name if team else None,
        }
        for student, team in rows
    ]

    return {
        "items": items,
        "total": total,
        "limit": clamped_limit,
        "offset": clamped_offset,
    }


@router.get("/me/token-usage", response_model=schemas.TokenUsageResponse)
async def get_my_token_usage(
    user: User = Depends(get_active_user),
):
    if not (user.roles and "token" in user.roles):
        raise HTTPException(status_code=403, detail="Forbidden")

    async with AsyncSessionLocal() as db:
        proxy = (await db.execute(select(ProxySetting).where(ProxySetting.id == 1))).scalar_one_or_none()
        reset = (await db.execute(select(ResetState).where(ResetState.id == 1))).scalar_one_or_none()
        if not proxy or not reset:
            raise HTTPException(status_code=503, detail="Token usage configuration not available")

        allocated = proxy.total_short
        used = user.token_usage_short
        next_reset = reset.last_short_reset + timedelta(hours=proxy.interval_hours)

    return {
        "short": {
            "allocated": allocated,
            "used": used,
            "remaining": max(allocated - used, 0),
            "last_reset": reset.last_short_reset,
            "next_reset": next_reset,
        },
    }


@router.get("/students/search", response_model=schemas.StudentSearchResponse)
async def search_students(
    q: str,
    limit: int = 20,
    user: User = Depends(get_active_user),
):
    require_privileged_api_role(user)

    normalized_query = q.strip()
    if len(normalized_query) < 1:
        return {
            "items": [],
            "total": 0,
        }

    async with AsyncSessionLocal() as db:
        clamped_limit = min(max(limit, 1), 50)
        rows, total = await crud.search_students(db, normalized_query, clamped_limit)

    items = [
        {
            "student_user_id": student.id,
            "student_name": student.name or student.email,
            "student_email": student.email,
            "team_name": team.name if team else None,
        }
        for student, team in rows
    ]

    return {
        "items": items,
        "total": total,
    }
