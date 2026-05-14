from __future__ import annotations

import json
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from starlette.requests import Request

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "achievements:recent:v1:"


def build_achievements_recent_cache_key(limit: int) -> str:
    return f"{_CACHE_KEY_PREFIX}limit:{limit}"


def get_achievements_recent_cache(request: Request) -> AchievementsRecentCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "achievements_recent_cache", None)


class AchievementsRecentCache:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get(self, limit: int) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(build_achievements_recent_cache_key(limit))
            if raw is None:
                return None
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception:
            logger.warning("Failed to read achievements/recent cache", exc_info=True)
        return None

    async def set(self, limit: int, payload: dict[str, Any]) -> None:
        if self._ttl_seconds <= 0:
            return
        try:
            await self._redis.set(
                build_achievements_recent_cache_key(limit),
                json.dumps(jsonable_encoder(payload)),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.warning("Failed to write achievements/recent cache", exc_info=True)

    async def invalidate_all(self) -> None:
        try:
            keys: list[str] = []
            async for key in self._redis.scan_iter(f"{_CACHE_KEY_PREFIX}*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            logger.warning("Failed to invalidate achievements/recent cache", exc_info=True)

    async def close(self) -> None:
        await self._redis.aclose()


async def invalidate_all_recent_achievements_cache(redis_url: str | None) -> None:
    if not redis_url:
        return
    redis = Redis.from_url(redis_url, decode_responses=True)
    try:
        keys: list[str] = []
        async for key in redis.scan_iter(f"{_CACHE_KEY_PREFIX}*"):
            keys.append(key)
        if keys:
            await redis.delete(*keys)
    except Exception:
        logger.warning("Failed to invalidate achievements/recent cache", exc_info=True)
    finally:
        await redis.aclose()
