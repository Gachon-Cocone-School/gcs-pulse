from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.core.config import settings
from app.database import get_db
from app.dependencies import (
    get_active_user,
    require_privileged_api_role,
    verify_csrf,
)
from app.limiter import limiter
from app.models import ApiToken, ProxySetting, ResetState, User

router = APIRouter(prefix="/users", tags=["users"], dependencies=[Depends(verify_csrf)])


@router.get("/me/league", response_model=schemas.MeLeagueResponse)
async def get_my_league(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is not None:
        raise HTTPException(status_code=409, detail="Team members cannot change personal league")

    updated = await crud.update_user_league_type(db, user, payload.league_type.value)
    return {
        "league_type": updated.league_type,
        "can_update": True,
        "managed_by_team": False,
    }


@router.get("/students", response_model=schemas.StudentListResponse)
async def list_students(
    limit: int = 100,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    require_privileged_api_role(user)

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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if not (user.roles and "gcs" in user.roles):
        raise HTTPException(status_code=403, detail="Forbidden")

    # proxy_setting, reset_state (단일 행)
    proxy = (await db.execute(select(ProxySetting).where(ProxySetting.id == 1))).scalar_one_or_none()
    reset = (await db.execute(select(ResetState).where(ResetState.id == 1))).scalar_one_or_none()
    if not proxy or not reset:
        raise HTTPException(status_code=503, detail="Token usage configuration not available")

    # 활성 사용자 수 (revoked_at IS NULL 인 api_tokens 발급자 수)
    active_count_row = await db.execute(
        select(func.count(func.distinct(ApiToken.user_id))).where(ApiToken.revoked_at.is_(None))
    )
    active_count = active_count_row.scalar_one() or 1

    # 전체 weekly 사용량 합산
    total_weekly_used_row = await db.execute(select(func.sum(User.token_usage_weekly)))
    total_weekly_used = int(total_weekly_used_row.scalar_one() or 0)

    # Short 계산
    short_allocated = proxy.total_short // active_count
    short_used = user.token_usage_short
    short_next_reset = reset.last_short_reset + timedelta(hours=proxy.interval_hours)

    # Weekly 계산
    weekly_remaining_pool = max(proxy.total_weekly - total_weekly_used, 0)
    per_user_allocated = weekly_remaining_pool // active_count

    # Weekly 다음 리셋: reset_state.last_weekly_reset 기준 다음 weekly_day/weekly_hour
    last_wr = reset.last_weekly_reset
    # 항상 interval_hours(5시간) 단위로 업데이트되므로 next는 마지막 weekly 리셋 기준 다음 월요일
    days_ahead = {"MON": 0, "TUE": 1, "WED": 2, "THU": 3, "FRI": 4, "SAT": 5, "SUN": 6}
    target_weekday = days_ahead.get(proxy.weekly_day.upper(), 0)
    current_weekday = last_wr.weekday()  # 0=Mon
    delta_days = (target_weekday - current_weekday) % 7 or 7
    weekly_next_reset = (last_wr + timedelta(days=delta_days)).replace(
        hour=proxy.weekly_hour, minute=0, second=0, microsecond=0
    )

    return {
        "short": {
            "allocated": short_allocated,
            "used": short_used,
            "remaining": max(short_allocated - short_used, 0),
            "last_reset": reset.last_short_reset,
            "next_reset": short_next_reset,
        },
        "weekly": {
            "total_quota": proxy.total_weekly,
            "total_used": total_weekly_used,
            "total_remaining": weekly_remaining_pool,
            "my_used": user.token_usage_weekly,
            "per_user_allocated": per_user_allocated,
            "last_reset": reset.last_weekly_reset,
            "next_reset": weekly_next_reset,
        },
    }


@router.get("/students/search", response_model=schemas.StudentSearchResponse)
async def search_students(
    q: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    require_privileged_api_role(user)

    normalized_query = q.strip()
    if len(normalized_query) < 1:
        return {
            "items": [],
            "total": 0,
        }

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
