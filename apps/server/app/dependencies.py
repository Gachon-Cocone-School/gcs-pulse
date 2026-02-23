import secrets

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import User as UserModel
from app.models import Term as TermModel

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}


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
