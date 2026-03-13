import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User as UserModel
from app.models import Term as TermModel

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
PRIVILEGED_API_ROLES = frozenset({"gcs", "교수", "admin"})
SNIPPET_FULL_READ_ROLES = frozenset({"교수", "admin"})
SNIPPET_TEAM_READ_ROLES = frozenset({"gcs"})
SNIPPET_ACCESS_ROLES = SNIPPET_FULL_READ_ROLES | SNIPPET_TEAM_READ_ROLES


def _extract_roles(user: UserModel | dict | None) -> set[str]:
    if user is None:
        return set()

    if isinstance(user, dict):
        raw_roles = user.get("roles")
    else:
        raw_roles = getattr(user, "roles", None)

    if not isinstance(raw_roles, (list, tuple, set)):
        return set()

    roles: set[str] = set()
    for role in raw_roles:
        normalized = str(role).strip()
        if normalized:
            roles.add(normalized)
    return roles


def has_privileged_api_role(user: UserModel | dict | None) -> bool:
    return bool(_extract_roles(user) & PRIVILEGED_API_ROLES)


def has_professor_role(user: UserModel | dict | None) -> bool:
    return "교수" in _extract_roles(user)


def has_professor_or_admin_role(user: UserModel | dict | None) -> bool:
    roles = _extract_roles(user)
    return "교수" in roles or "admin" in roles


def require_privileged_api_role(user: UserModel | dict | None) -> None:
    if not has_privileged_api_role(user):
        raise HTTPException(status_code=403, detail="Forbidden")


def require_professor_role(user: UserModel | dict | None) -> None:
    if not has_professor_role(user):
        raise HTTPException(status_code=403, detail="Professor only")


def require_professor_or_admin_role(user: UserModel | dict | None) -> None:
    if not has_professor_or_admin_role(user):
        raise HTTPException(status_code=403, detail="Professor or admin only")


def has_snippet_full_read_role(user: UserModel | dict | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_FULL_READ_ROLES)


def has_snippet_team_read_role(user: UserModel | dict | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_TEAM_READ_ROLES)


def has_snippet_access_role(user: UserModel | dict | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_ACCESS_ROLES)


def require_snippet_access_role(user: UserModel | dict | None) -> None:
    if not has_snippet_access_role(user):
        raise HTTPException(status_code=403, detail="Forbidden")


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def is_bearer_request(request: Request) -> bool:
    authorization = request.headers.get("authorization")
    if not authorization:
        return False

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return False

    return bool(token.strip())


def verify_csrf(request: Request) -> None:
    if request.method.upper() in SAFE_METHODS:
        return

    if is_bearer_request(request):
        return

    session_token = request.session.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")
    if not session_token or not header_token or session_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")


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
    user_email = user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await db.execute(
        select(UserModel)
        .options(selectinload(UserModel.consents))
        .filter(func.lower(UserModel.email) == user_email.strip().lower())
    )
    db_user = result.scalars().first()

    if not db_user:
        raise HTTPException(status_code=401, detail="User not found")

    require_privileged_api_role(db_user)

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
