from __future__ import annotations

import json
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from starlette.requests import Request

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "active-user:v1:"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_active_user_cache_key(email: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{normalize_email(email)}"


def get_active_user_cache(request: Request) -> ActiveUserCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "active_user_cache", None)


class ActiveUserCache:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get(self, email: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(build_active_user_cache_key(email))
            if raw is None:
                return None
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception:
            logger.warning("Failed to read active-user cache", exc_info=True)
        return None

    async def set(self, email: str, payload: dict[str, Any]) -> None:
        if self._ttl_seconds <= 0:
            return
        try:
            await self._redis.set(
                build_active_user_cache_key(email),
                json.dumps(jsonable_encoder(payload)),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.warning("Failed to write active-user cache", exc_info=True)

    async def invalidate(self, email: str) -> None:
        try:
            await self._redis.delete(build_active_user_cache_key(email))
        except Exception:
            logger.warning("Failed to invalidate active-user cache", exc_info=True)

    async def close(self) -> None:
        await self._redis.aclose()
