from __future__ import annotations

from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import Consent, Term


async def get_active_terms(db: AsyncSession) -> List[Term]:
    result = await db.execute(select(Term).filter(Term.is_active == True))
    return list(result.scalars().all())


async def get_term_by_id(db: AsyncSession, term_id: int) -> Optional[Term]:
    result = await db.execute(select(Term).filter(Term.id == term_id))
    return result.scalars().first()


async def get_consent(
    db: AsyncSession, user_id: int, term_id: int
) -> Optional[Consent]:
    result = await db.execute(
        select(Consent).filter(Consent.user_id == user_id, Consent.term_id == term_id)
    )
    return result.scalars().first()


async def create_consent(db: AsyncSession, user_id: int, term_id: int) -> Consent:
    new_consent = Consent(user_id=user_id, term_id=term_id)
    db.add(new_consent)
    await db.commit()
    await db.refresh(new_consent)
    return new_consent
