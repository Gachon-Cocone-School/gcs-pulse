from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User as UserModel
from app.models import Term as TermModel


# Dependency for getting current user
async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)):
    user_info = request.session.get("user")
    if not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user_info


# Dependency for checking if user has agreed to all required terms
async def get_active_user(
    user: dict = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    # 1. Get user from DB with consents
    result = await db.execute(
        select(UserModel)
        .options(selectinload(UserModel.consents))
        .filter(UserModel.google_sub == user["sub"])
    )
    db_user = result.scalars().first()

    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    # 2. Get all required active terms
    terms_result = await db.execute(
        select(TermModel.id).filter(
            TermModel.is_active == True, TermModel.is_required == True
        )
    )
    required_term_ids = set(terms_result.scalars().all())

    # 3. Check user consents
    agreed_term_ids = {c.term_id for c in db_user.consents}
    missing_terms = [tid for tid in required_term_ids if tid not in agreed_term_ids]

    if missing_terms:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Terms agreement required",
                "missing_terms": list(missing_terms),
            },
        )

    return db_user


async def check_route_permissions(
    request: Request, db: AsyncSession = Depends(get_db)
):
    # 1. Identify route
    # Use request.url.path for exact match or request.scope['route'].path for template match
    # Usually for permissions we want the template path (e.g. /users/{id})
    # But if the route is not found in router, scope['route'] might be missing.
    # We should handle that.
    
    # Ideally we use the router's path template.
    route = request.scope.get("route")
    if not route:
        # If no route matched (404), we might not want to enforce permissions?
        # Or we enforce on the raw path?
        # Let's assume we enforce on the matched path template.
        # If 404, FastAPI handles it before this dependency if it's global?
        # Actually global dependencies run before routing? No, after routing match.
        path = request.url.path
    else:
        path = route.path

    method = request.method

    # 2. Fetch permission
    from app.models import RoutePermission
    
    result = await db.execute(
        select(RoutePermission).filter(
            RoutePermission.path == path,
            RoutePermission.method == method
        )
    )
    permission = result.scalars().first()

    # 3. Default DISALLOW
    if not permission:
        raise HTTPException(status_code=403, detail="Access denied: No permission rule found")

    # 4. Check Public
    if permission.is_public:
        return

    # 5. Check Auth & Roles
    user_info = request.session.get("user")
    if not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated")

    # Fetch user roles from DB to be safe/fresh? 
    # Or trust session? Session might be stale.
    # Let's fetch user from DB.
    result = await db.execute(
        select(UserModel).filter(UserModel.google_sub == user_info["sub"])
    )
    db_user = result.scalars().first()
    
    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    user_roles = set(db_user.roles)
    allowed_roles = set(permission.roles)

    if not user_roles.intersection(allowed_roles):
        raise HTTPException(status_code=403, detail="Access denied: Insufficient permissions")

