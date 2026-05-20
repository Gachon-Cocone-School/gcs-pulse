from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from app.models import ApiToken, User


API_TOKEN_LAST_USED_AT_THROTTLE = timedelta(minutes=5)


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


async def get_api_token_with_user_by_raw_token(
    db: AsyncSession,
    raw_token: str,
    *,
    include_consents: bool = False,
) -> Optional[ApiToken]:
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
    user_loader = joinedload(ApiToken.user)
    if include_consents:
        user_loader = user_loader.joinedload(User.consents)

    result = await db.execute(
        select(ApiToken)
        .options(user_loader)
        .filter(ApiToken.token_hash == token_hash)
    )
    return result.unique().scalars().first()


async def touch_api_token_last_used_at(
    db: AsyncSession,
    token: ApiToken,
    used_at: Optional[datetime] = None,
    *,
    throttle: timedelta = API_TOKEN_LAST_USED_AT_THROTTLE,
) -> ApiToken:
    now = used_at or datetime.now().astimezone()
    last_used_at = token.last_used_at
    if last_used_at is not None:
        if last_used_at.tzinfo is None and now.tzinfo is not None:
            last_used_at = last_used_at.replace(tzinfo=now.tzinfo)
        if now - last_used_at < throttle:
            return token

    await db.execute(
        update(ApiToken)
        .where(ApiToken.id == token.id)
        .values(last_used_at=now)
    )
    await db.commit()
    token.last_used_at = now
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
