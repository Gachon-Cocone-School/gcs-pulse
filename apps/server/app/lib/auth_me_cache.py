from __future__ import annotations

import json
import logging
from typing import Any

from redis.asyncio import Redis
from starlette.requests import Request

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "auth:me:v1:"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_auth_me_cache_key(email: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{normalize_email(email)}"


def get_auth_me_cache(request: Request) -> AuthMeCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "auth_me_cache", None)


class AuthMeCache:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get(self, email: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(build_auth_me_cache_key(email))
            if raw is None:
                return None
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception:
            logger.warning("Failed to read auth/me cache", exc_info=True)
        return None

    async def set(self, email: str, payload: dict[str, Any]) -> None:
        if self._ttl_seconds <= 0:
            return
        try:
            await self._redis.set(
                build_auth_me_cache_key(email),
                json.dumps(payload),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.warning("Failed to write auth/me cache", exc_info=True)

    async def invalidate(self, email: str) -> None:
        try:
            await self._redis.delete(build_auth_me_cache_key(email))
        except Exception:
            logger.warning("Failed to invalidate auth/me cache", exc_info=True)

    async def close(self) -> None:
        await self._redis.aclose()
