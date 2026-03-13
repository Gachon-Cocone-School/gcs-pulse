from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.core.config import settings
from app.database import get_db
from app.dependencies import (
    get_active_user,
    require_professor_or_admin_role,
    require_professor_role,
    verify_csrf,
)
from app.limiter import limiter
from app.models import User

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
    require_professor_or_admin_role(user)

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


@router.get("/students/search", response_model=schemas.StudentSearchResponse)
async def search_students(
    q: str,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    require_professor_role(user)

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
