from __future__ import annotations

import json
import logging
from datetime import date
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from starlette.requests import Request

logger = logging.getLogger(__name__)

_CACHE_KEY_PREFIX = "leaderboards:v1:"


def build_leaderboards_cache_key(
    *,
    mode: str,
    league_type: str,
    period: str,
    window_key: date,
    limit: int,
    offset: int,
) -> str:
    return (
        f"{_CACHE_KEY_PREFIX}mode:{mode}:league:{league_type}:period:{period}:"
        f"window:{window_key.isoformat()}:limit:{limit}:offset:{offset}"
    )


def get_leaderboards_cache(request: Request) -> LeaderboardsCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "leaderboards_cache", None)


class LeaderboardsCache:
    def __init__(self, redis_url: str, ttl_seconds: int):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds

    async def get(
        self,
        *,
        mode: str,
        league_type: str,
        period: str,
        window_key: date,
        limit: int,
        offset: int,
    ) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(
                build_leaderboards_cache_key(
                    mode=mode,
                    league_type=league_type,
                    period=period,
                    window_key=window_key,
                    limit=limit,
                    offset=offset,
                )
            )
            if raw is None:
                return None
            payload = json.loads(raw)
            if isinstance(payload, dict):
                return payload
        except Exception:
            logger.warning("Failed to read leaderboards cache", exc_info=True)
        return None

    async def set(
        self,
        *,
        mode: str,
        league_type: str,
        period: str,
        window_key: date,
        limit: int,
        offset: int,
        payload: dict[str, Any],
    ) -> None:
        if self._ttl_seconds <= 0:
            return
        try:
            await self._redis.set(
                build_leaderboards_cache_key(
                    mode=mode,
                    league_type=league_type,
                    period=period,
                    window_key=window_key,
                    limit=limit,
                    offset=offset,
                ),
                json.dumps(jsonable_encoder(payload)),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.warning("Failed to write leaderboards cache", exc_info=True)

    async def invalidate_all(self) -> None:
        try:
            keys: list[str] = []
            async for key in self._redis.scan_iter(f"{_CACHE_KEY_PREFIX}*"):
                keys.append(key)
            if keys:
                await self._redis.delete(*keys)
        except Exception:
            logger.warning("Failed to invalidate leaderboards cache", exc_info=True)

    async def close(self) -> None:
        await self._redis.aclose()


async def invalidate_all_leaderboards_cache(redis_url: str | None) -> None:
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
        logger.warning("Failed to invalidate leaderboards cache", exc_info=True)
    finally:
        await redis.aclose()
