from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import TeamCreate, TeamResponse, TeamUpdate

router = APIRouter(prefix="/admin/teams", tags=["teams"])


def _require_admin(user) -> None:
    roles = user.roles or []
    if "admin" not in roles:
        raise HTTPException(status_code=403, detail="Admin only")


@router.get("", response_model=list[TeamResponse])
async def list_teams(request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)
    teams, _ = await crud.list_teams(db, limit=1000, offset=0)
    return teams


@router.post("", response_model=TeamResponse)
async def create_team(team: TeamCreate, request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)
    return await crud.create_team(db, name=team.name)


@router.get("/{team_id}", response_model=TeamResponse)
async def get_team(team_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)
    team = await crud.get_team_with_members(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_id}", response_model=TeamResponse)
async def update_team(
    team_id: int, team_update: TeamUpdate, request: Request, db: AsyncSession = Depends(get_db)
):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)
    team = await crud.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return await crud.update_team(db, team=team, name=team_update.name)


@router.delete("/{team_id}")
async def delete_team(team_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)
    team = await crud.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    await crud.delete_team(db, team=team)
    return {"message": "Team deleted"}


@router.post("/{team_id}/members/{user_id}")
async def add_member(team_id: int, user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)

    team = await crud.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await crud.set_user_team(db, user=user, team_id=team_id)
    return {"message": "Member added"}


@router.delete("/{team_id}/members/{user_id}")
async def remove_member(team_id: int, user_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        raise HTTPException(status_code=401, detail="Not authenticated")

    viewer = await crud.get_user_by_sub(db, user_sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    _require_admin(viewer)

    team = await crud.get_team_by_id(db, team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user = await crud.get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.team_id != team_id:
        raise HTTPException(status_code=400, detail="User is not a member of this team")

    await crud.set_user_team(db, user=user, team_id=None)
    return {"message": "Member removed"}
