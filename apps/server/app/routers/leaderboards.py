from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.database import get_db
from app.dependencies import get_active_user
from app.models import User
from app.routers import snippet_utils
from app.utils_time import current_business_date, current_business_week_start

router = APIRouter(prefix="/leaderboards", tags=["leaderboards"])


@router.get("", response_model=schemas.LeaderboardResponse)
async def get_leaderboard(
    request: Request,
    period: str = Query("daily", pattern="^(daily|weekly)$"),
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    now = snippet_utils.get_request_now(request)
    if period == "daily":
        target_key = current_business_date(now) - timedelta(days=1)
        window_label = "yesterday"
    else:
        target_key = current_business_week_start(now) - timedelta(days=7)
        window_label = "last_week"

    if user.team_id is not None:
        team = await crud.get_team_by_id(db, user.team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")
        league_type = team.league_type or schemas.LeagueType.NONE.value
        if league_type == schemas.LeagueType.NONE.value:
            return {
                "period": period,
                "window": {"label": window_label, "key": target_key},
                "league_type": league_type,
                "excluded_by_league": True,
                "items": [],
                "total": 0,
            }
        items = await crud.build_team_leaderboard(
            db=db,
            league_type=league_type,
            period=period,
            target_key=target_key,
        )
    else:
        league_type = user.league_type or schemas.LeagueType.NONE.value
        if league_type == schemas.LeagueType.NONE.value:
            return {
                "period": period,
                "window": {"label": window_label, "key": target_key},
                "league_type": league_type,
                "excluded_by_league": True,
                "items": [],
                "total": 0,
            }
        items = await crud.build_individual_leaderboard(
            db=db,
            league_type=league_type,
            period=period,
            target_key=target_key,
        )

    total = len(items)
    paged_items = items[offset : offset + limit]

    return {
        "period": period,
        "window": {"label": window_label, "key": target_key},
        "league_type": league_type,
        "excluded_by_league": False,
        "items": paged_items,
        "total": total,
    }
