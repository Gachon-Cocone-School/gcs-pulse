from __future__ import annotations

import json
import logging
from typing import Any

from fastapi.encoders import jsonable_encoder
from redis.asyncio import Redis
from starlette.requests import Request

logger = logging.getLogger(__name__)

_PROFILE_CACHE_KEY_PREFIX = "active-user:profile:v1:"
_UI_ROLES_CACHE_KEY_PREFIX = "active-user:ui-roles:v1:"
_HARD_CONTEXT_CACHE_KEY_PREFIX = "active-user:hard-context:v1:"


def normalize_email(email: str) -> str:
    return email.strip().lower()


def build_active_user_profile_cache_key(email: str) -> str:
    return f"{_PROFILE_CACHE_KEY_PREFIX}{normalize_email(email)}"


def build_active_user_ui_roles_cache_key(email: str) -> str:
    return f"{_UI_ROLES_CACHE_KEY_PREFIX}{normalize_email(email)}"


def build_active_user_hard_context_cache_key(email: str) -> str:
    return f"{_HARD_CONTEXT_CACHE_KEY_PREFIX}{normalize_email(email)}"


class _JsonRedisCache:
    def __init__(self, redis_url: str, ttl_seconds: int, key_prefix: str):
        self._redis = Redis.from_url(redis_url, decode_responses=True)
        self._ttl_seconds = ttl_seconds
        self._key_prefix = key_prefix

    def _build_key(self, email: str) -> str:
        return f"{self._key_prefix}{normalize_email(email)}"

    async def get(self, email: str) -> dict[str, Any] | None:
        try:
            raw = await self._redis.get(self._build_key(email))
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
                self._build_key(email),
                json.dumps(jsonable_encoder(payload)),
                ex=self._ttl_seconds,
            )
        except Exception:
            logger.warning("Failed to write active-user cache", exc_info=True)

    async def invalidate(self, email: str) -> None:
        try:
            await self._redis.delete(self._build_key(email))
        except Exception:
            logger.warning("Failed to invalidate active-user cache", exc_info=True)

    async def close(self) -> None:
        await self._redis.aclose()


class ActiveUserProfileCache(_JsonRedisCache):
    def __init__(self, redis_url: str, ttl_seconds: int):
        super().__init__(redis_url=redis_url, ttl_seconds=ttl_seconds, key_prefix=_PROFILE_CACHE_KEY_PREFIX)


class ActiveUserUiRolesCache(_JsonRedisCache):
    def __init__(self, redis_url: str, ttl_seconds: int):
        super().__init__(redis_url=redis_url, ttl_seconds=ttl_seconds, key_prefix=_UI_ROLES_CACHE_KEY_PREFIX)


class ActiveUserHardContextCache(_JsonRedisCache):
    def __init__(self, redis_url: str, ttl_seconds: int):
        super().__init__(redis_url=redis_url, ttl_seconds=ttl_seconds, key_prefix=_HARD_CONTEXT_CACHE_KEY_PREFIX)


def get_active_user_profile_cache(request: Request) -> ActiveUserProfileCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "active_user_profile_cache", None)


def get_active_user_ui_roles_cache(request: Request) -> ActiveUserUiRolesCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "active_user_ui_roles_cache", None)


def get_active_user_hard_context_cache(request: Request) -> ActiveUserHardContextCache | None:
    app = request.scope.get("app")
    if app is None:
        return None
    state = getattr(app, "state", None)
    if state is None:
        return None
    return getattr(state, "active_user_hard_context_cache", None)


async def invalidate_active_user_caches(
    request: Request,
    email: str,
    *,
    profile: bool = False,
    ui_roles: bool = False,
    hard_context: bool = False,
) -> None:
    if profile:
        cache = get_active_user_profile_cache(request)
        if cache is not None:
            await cache.invalidate(email)

    if ui_roles:
        cache = get_active_user_ui_roles_cache(request)
        if cache is not None:
            await cache.invalidate(email)

    if hard_context:
        cache = get_active_user_hard_context_cache(request)
        if cache is not None:
            await cache.invalidate(email)
