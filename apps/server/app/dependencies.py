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
