from __future__ import annotations

import hashlib
import secrets
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models import ApiToken


async def create_api_token(
    db: AsyncSession, user_id: int, description: str, idempotency_key: Optional[str] = None
) -> Tuple[ApiToken, str]:
    # If idempotency_key provided, check for an existing token for this user
    if idempotency_key:
        result = await db.execute(
            select(ApiToken).filter(ApiToken.user_id == user_id, ApiToken.idempotency_key == idempotency_key)
        )
        existing = result.scalars().first()
        if existing:
            # Return existing token without revealing raw token again
            return existing, ""

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    db_token = ApiToken(
        user_id=user_id,
        token_hash=token_hash,
        description=description,
        idempotency_key=idempotency_key,
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token, raw_token


async def list_api_tokens(db: AsyncSession, user_id: int) -> List[ApiToken]:
    result = await db.execute(
        select(ApiToken).filter(ApiToken.user_id == user_id).order_by(ApiToken.created_at.desc())
    )
    return list(result.scalars().all())


async def get_api_token_by_raw_token(db: AsyncSession, raw_token: str) -> Optional[ApiToken]:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    result = await db.execute(select(ApiToken).filter(ApiToken.token_hash == token_hash))
    return result.scalars().first()


async def touch_api_token_last_used_at(
    db: AsyncSession, token: ApiToken, used_at: Optional[datetime] = None
) -> ApiToken:
    setattr(token, "last_used_at", used_at or datetime.now().astimezone())
    await db.commit()
    await db.refresh(token)
    return token


async def delete_api_token(db: AsyncSession, token_id: int, user_id: int) -> bool:
    result = await db.execute(
        select(ApiToken).filter(ApiToken.id == token_id, ApiToken.user_id == user_id)
    )
    token = result.scalars().first()
    if token:
        await db.delete(token)
        await db.commit()
        return True
    return False
