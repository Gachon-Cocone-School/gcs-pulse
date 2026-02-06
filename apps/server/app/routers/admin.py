from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database import get_db
from app.models import RoutePermission
from app.schemas import (
    RoutePermissionCreate,
    RoutePermissionUpdate,
    RoutePermissionResponse,
    UserAdminResponse,
    UserUpdate,
    TermCreate,
    TermUpdate,
    TermResponse,
    ConsentResponse,
)
from sqlalchemy.orm import selectinload

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/permissions", response_model=List[RoutePermissionResponse])
async def list_permissions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RoutePermission))
    return result.scalars().all()


@router.post("/permissions", response_model=RoutePermissionResponse)
async def create_permission(
    permission: RoutePermissionCreate, db: AsyncSession = Depends(get_db)
):
    # Check if exists
    result = await db.execute(
        select(RoutePermission).filter(
            RoutePermission.path == permission.path,
            RoutePermission.method == permission.method,
        )
    )
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="Permission already exists")

    db_permission = RoutePermission(**permission.model_dump())
    db.add(db_permission)
    await db.commit()
    await db.refresh(db_permission)
    return db_permission


@router.put("/permissions/{permission_id}", response_model=RoutePermissionResponse)
async def update_permission(
    permission_id: int,
    permission_update: RoutePermissionUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoutePermission).filter(RoutePermission.id == permission_id)
    )
    db_permission = result.scalars().first()
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    update_data = permission_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_permission, key, value)

    await db.commit()
    await db.refresh(db_permission)
    return db_permission


@router.delete("/permissions/{permission_id}")
async def delete_permission(permission_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoutePermission).filter(RoutePermission.id == permission_id)
    )
    db_permission = result.scalars().first()
    if not db_permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    await db.delete(db_permission)
    await db.commit()
    return {"message": "Permission deleted"}


# Role Assignment Rules Endpoints
from app.models import RoleAssignmentRule
from app.schemas import (
    RoleAssignmentRuleCreate,
    RoleAssignmentRuleUpdate,
    RoleAssignmentRuleResponse,
)


@router.get("/role-rules", response_model=List[RoleAssignmentRuleResponse])
async def list_role_rules(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoleAssignmentRule).order_by(RoleAssignmentRule.priority.asc())
    )
    return result.scalars().all()


@router.post("/role-rules", response_model=RoleAssignmentRuleResponse)
async def create_role_rule(
    rule: RoleAssignmentRuleCreate, db: AsyncSession = Depends(get_db)
):
    db_rule = RoleAssignmentRule(**rule.model_dump())
    db.add(db_rule)
    await db.commit()
    await db.refresh(db_rule)
    return db_rule


@router.put("/role-rules/{rule_id}", response_model=RoleAssignmentRuleResponse)
async def update_role_rule(
    rule_id: int,
    rule_update: RoleAssignmentRuleUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(RoleAssignmentRule).filter(RoleAssignmentRule.id == rule_id)
    )
    db_rule = result.scalars().first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    update_data = rule_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_rule, key, value)

    await db.commit()
    await db.refresh(db_rule)
    return db_rule


@router.delete("/role-rules/{rule_id}")
async def delete_role_rule(rule_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(RoleAssignmentRule).filter(RoleAssignmentRule.id == rule_id)
    )
    db_rule = result.scalars().first()
    if not db_rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    await db.delete(db_rule)
    await db.commit()
    return {"message": "Rule deleted"}


# User Management
from app.models import User, Consent


@router.get("/users", response_model=List[UserAdminResponse])
async def list_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.consents)).order_by(User.id.desc())
    )
    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserAdminResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(User).options(selectinload(User.consents)).filter(User.id == user_id)
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    user_id: int, user_update: UserUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    await db.commit()
    # Re-fetch with consents to avoid MissingGreenlet during serialization
    result = await db.execute(
        select(User).options(selectinload(User.consents)).filter(User.id == user_id)
    )
    user = result.scalars().first()
    return user


@router.delete("/users/{user_id}")
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await db.delete(user)
    await db.commit()
    return {"message": "User deleted"}


# Term Management
from app.models import Term


@router.get("/terms", response_model=List[TermResponse])
async def list_terms(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Term).order_by(Term.id.desc()))
    return result.scalars().all()


@router.post("/terms", response_model=TermResponse)
async def create_term(term: TermCreate, db: AsyncSession = Depends(get_db)):
    db_term = Term(**term.model_dump())
    db.add(db_term)
    await db.commit()
    await db.refresh(db_term)
    return db_term


@router.put("/terms/{term_id}", response_model=TermResponse)
async def update_term(
    term_id: int, term_update: TermUpdate, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Term).filter(Term.id == term_id))
    db_term = result.scalars().first()
    if not db_term:
        raise HTTPException(status_code=404, detail="Term not found")

    update_data = term_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_term, key, value)

    await db.commit()
    await db.refresh(db_term)
    return db_term


@router.delete("/terms/{term_id}")
async def delete_term(term_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Term).filter(Term.id == term_id))
    db_term = result.scalars().first()
    if not db_term:
        raise HTTPException(status_code=404, detail="Term not found")

    await db.delete(db_term)
    await db.commit()
    return {"message": "Term deleted"}
