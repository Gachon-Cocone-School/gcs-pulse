from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app import crud, schemas
from app.database import get_db
from app.dependencies import get_active_user, verify_csrf
from app.models import Team, User

router = APIRouter(prefix="/teams", tags=["teams"], dependencies=[Depends(verify_csrf)])


def _validate_team_name(value: str) -> str:
    normalized = value.strip()
    if not normalized:
        raise HTTPException(status_code=400, detail="Team name is required")
    if len(normalized) > 100:
        raise HTTPException(status_code=400, detail="Team name must be 100 characters or less")
    return normalized


def _normalize_invite_code(value: str) -> str:
    normalized = value.strip().upper()
    if not normalized:
        raise HTTPException(status_code=400, detail="Invite code is required")
    return normalized


async def _serialize_me(db: AsyncSession, user: User) -> schemas.TeamMeResponse:
    if not user.team_id:
        return schemas.TeamMeResponse(team=None)

    team = await crud.get_team_with_members(db, user.team_id)
    if not team:
        return schemas.TeamMeResponse(team=None)

    return schemas.TeamMeResponse(team=schemas.TeamResponse.model_validate(team))


@router.get("/me", response_model=schemas.TeamMeResponse)
async def get_my_team(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    return await _serialize_me(db, user)


@router.post("", response_model=schemas.TeamResponse)
async def create_team(
    payload: schemas.TeamCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is not None:
        raise HTTPException(status_code=409, detail="Leave your current team before creating a new one")

    team_name = _validate_team_name(payload.name)

    for _ in range(5):
        code = crud.generate_invite_code()
        try:
            team = Team(name=team_name, invite_code=code)
            db.add(team)
            await db.flush()

            user.team_id = team.id
            await db.commit()

            team_with_members = await crud.get_team_with_members(db, team.id)
            if not team_with_members:
                raise HTTPException(status_code=500, detail="Failed to load team")
            return schemas.TeamResponse.model_validate(team_with_members)
        except IntegrityError:
            await db.rollback()
        except Exception:
            await db.rollback()
            raise

    raise HTTPException(status_code=500, detail="Failed to generate unique invite code")


@router.post("/join", response_model=schemas.TeamResponse)
async def join_team(
    payload: schemas.TeamJoin,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is not None:
        raise HTTPException(status_code=409, detail="Leave your current team before joining another one")

    code = _normalize_invite_code(payload.invite_code)
    team = await crud.get_team_by_invite_code(db, code)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user.team_id = team.id
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(user)

    team_with_members = await crud.get_team_with_members(db, team.id)
    if not team_with_members:
        raise HTTPException(status_code=500, detail="Failed to load team")

    return schemas.TeamResponse.model_validate(team_with_members)


@router.post("/leave", response_model=schemas.MessageResponse)
async def leave_team(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is None:
        raise HTTPException(status_code=400, detail="You are not in a team")

    team_id = user.team_id
    team = await crud.get_team_by_id(db, team_id)

    user.team_id = None
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(user)

    if team:
        member_count = await crud.count_team_members(db, team_id)
        if member_count == 0:
            await crud.delete_team(db, team)

    return {"message": "Left team"}


@router.patch("/me", response_model=schemas.TeamResponse)
async def rename_my_team(
    payload: schemas.TeamUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is None:
        raise HTTPException(status_code=400, detail="You are not in a team")

    if payload.name is None:
        raise HTTPException(status_code=400, detail="Team name is required")

    team = await crud.get_team_by_id(db, user.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    updated = await crud.update_team(db, team, name=_validate_team_name(payload.name))
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update team")

    return schemas.TeamResponse.model_validate(updated)


@router.patch("/me/league", response_model=schemas.TeamResponse)
async def update_my_team_league(
    payload: schemas.LeagueUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if user.team_id is None:
        raise HTTPException(status_code=400, detail="You are not in a team")

    team = await crud.get_team_by_id(db, user.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    updated = await crud.update_team(db, team, league_type=payload.league_type.value)
    if not updated:
        raise HTTPException(status_code=500, detail="Failed to update team league")

    return schemas.TeamResponse.model_validate(updated)
