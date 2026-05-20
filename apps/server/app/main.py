import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.limiter import limiter
from app.routers import auth, daily_snippets, snippet_utils, snippet_ai, terms, weekly_snippets, tokens, comments, teams, leaderboards, users, achievements, notifications, notifications_sse, notifications_public_sse, mcp, peer_reviews, meeting_rooms, tournaments
from app.core.config import settings
from app.core.logging_config import configure_logging
from app.middleware.logging_middleware import LoggingMiddleware

if settings.SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    from starlette.requests import ClientDisconnect

    def _before_send(event, hint):
        exc = hint.get("exc_info")
        if exc and issubclass(exc[0], ClientDisconnect):
            return None
        return event

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1 if settings.ENVIRONMENT == "production" else 1.0,
        before_send=_before_send,
        integrations=[
            StarletteIntegration(transaction_style="url"),
            FastApiIntegration(transaction_style="url"),
            SqlalchemyIntegration(),
        ],
    )

configure_logging(
    environment=settings.ENVIRONMENT,
    log_file=settings.LOG_FILE,
)

import structlog
logger = structlog.get_logger(__name__)

# Copilot client will be attached to app.state at startup
from app.core.copilot_settings import settings as copilot_settings
from app.lib.achievements_recent_cache import AchievementsRecentCache
from app.lib.active_user_cache import (
    ActiveUserHardContextCache,
    ActiveUserProfileCache,
    ActiveUserUiRolesCache,
)
from app.lib.copilot_client import CopilotClient
from app.lib.copilot_token_manager import token_manager as copilot_token_manager
from app.lib.leaderboards_cache import LeaderboardsCache
from app.database import engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.active_user_profile_cache = None
    app.state.active_user_ui_roles_cache = None
    app.state.active_user_hard_context_cache = None
    app.state.achievements_recent_cache = None
    app.state.leaderboards_cache = None

    client = CopilotClient(timeout=copilot_settings.COPILOT_REQUEST_TIMEOUT)
    app.state.copilot_client = client
    app.state.copilot_token_manager = copilot_token_manager
    snippet_ai.preload_prompts()

    if settings.REDIS_URL:
        if settings.ACTIVE_USER_PROFILE_CACHE_TTL_SECONDS > 0:
            try:
                app.state.active_user_profile_cache = ActiveUserProfileCache(
                    redis_url=settings.REDIS_URL,
                    ttl_seconds=settings.ACTIVE_USER_PROFILE_CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to initialize active-user profile cache", exc_info=True)
                app.state.active_user_profile_cache = None

        if settings.ACTIVE_USER_UI_ROLES_CACHE_TTL_SECONDS > 0:
            try:
                app.state.active_user_ui_roles_cache = ActiveUserUiRolesCache(
                    redis_url=settings.REDIS_URL,
                    ttl_seconds=settings.ACTIVE_USER_UI_ROLES_CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to initialize active-user ui-roles cache", exc_info=True)
                app.state.active_user_ui_roles_cache = None

        if settings.ACTIVE_USER_HARD_CONTEXT_CACHE_TTL_SECONDS > 0:
            try:
                app.state.active_user_hard_context_cache = ActiveUserHardContextCache(
                    redis_url=settings.REDIS_URL,
                    ttl_seconds=settings.ACTIVE_USER_HARD_CONTEXT_CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to initialize active-user hard-context cache", exc_info=True)
                app.state.active_user_hard_context_cache = None

        if settings.ACHIEVEMENTS_RECENT_CACHE_TTL_SECONDS > 0:
            try:
                app.state.achievements_recent_cache = AchievementsRecentCache(
                    redis_url=settings.REDIS_URL,
                    ttl_seconds=settings.ACHIEVEMENTS_RECENT_CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to initialize achievements/recent cache", exc_info=True)
                app.state.achievements_recent_cache = None

        if settings.LEADERBOARDS_CACHE_TTL_SECONDS > 0:
            try:
                app.state.leaderboards_cache = LeaderboardsCache(
                    redis_url=settings.REDIS_URL,
                    ttl_seconds=settings.LEADERBOARDS_CACHE_TTL_SECONDS,
                )
            except Exception:
                logger.warning("Failed to initialize leaderboards cache", exc_info=True)
                app.state.leaderboards_cache = None

    try:
        yield
    finally:
        active_user_profile_cache = getattr(app.state, "active_user_profile_cache", None)
        if active_user_profile_cache:
            await active_user_profile_cache.close()

        active_user_ui_roles_cache = getattr(app.state, "active_user_ui_roles_cache", None)
        if active_user_ui_roles_cache:
            await active_user_ui_roles_cache.close()

        active_user_hard_context_cache = getattr(app.state, "active_user_hard_context_cache", None)
        if active_user_hard_context_cache:
            await active_user_hard_context_cache.close()

        achievements_recent_cache = getattr(app.state, "achievements_recent_cache", None)
        if achievements_recent_cache:
            await achievements_recent_cache.close()

        leaderboards_cache = getattr(app.state, "leaderboards_cache", None)
        if leaderboards_cache:
            await leaderboards_cache.close()

        await engine.dispose()

        client = getattr(app.state, "copilot_client", None)
        if client:
            await client.close()


app = FastAPI(lifespan=lifespan)

# Rate Limiting Setup
app.state.limiter = limiter


def _rate_limit_handler(request: Request, exc: Exception):
    if isinstance(exc, RateLimitExceeded):
        return _rate_limit_exceeded_handler(request, exc)
    logger.exception("Unhandled rate limit handler exception")
    return JSONResponse({"detail": "Internal server error"}, status_code=500)


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


def _validate_production_secret_key() -> None:
    if settings.ENVIRONMENT != "production":
        return

    secret_key = settings.SECRET_KEY.strip()
    if not secret_key or secret_key == "your-secret-key":
        raise RuntimeError("SECRET_KEY must be configured in production")


def _resolve_cors_origins() -> list[str]:
    origins = list(settings.CORS_ORIGINS)
    if settings.ENVIRONMENT == "production":
        return origins

    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ):
        if origin not in origins:
            origins.append(origin)

    return origins


# Trusted Host Middleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.ALLOWED_HOSTS)

# Session Middleware
_validate_production_secret_key()
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    https_only=(settings.ENVIRONMENT == "production"),
    same_site="lax",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=_resolve_cors_origins(),
    allow_credentials=True,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 요청 로깅 미들웨어 (가장 바깥쪽에 위치시켜 모든 요청을 기록)
app.add_middleware(LoggingMiddleware)

# Include Routers
app.include_router(auth.router)
app.include_router(terms.router)
app.include_router(tokens.router)
app.include_router(teams.router)
app.include_router(users.router)
app.include_router(leaderboards.router)
app.include_router(achievements.router)
app.include_router(snippet_utils.router)
app.include_router(daily_snippets.router)
app.include_router(weekly_snippets.router)
app.include_router(comments.router)
app.include_router(notifications.router)
app.include_router(notifications_sse.router)
app.include_router(notifications_public_sse.router)
app.include_router(mcp.router)
app.include_router(peer_reviews.router)
app.include_router(meeting_rooms.router)
app.include_router(tournaments.router)

if __name__ == "__main__":
    import uvicorn

    # 로컬 개발용 실행 코드 (프로덕션에서는 보통 CLI로 실행)
    uvicorn.run(app, host="0.0.0.0", port=8000)
