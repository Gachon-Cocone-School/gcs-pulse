import logging

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

logger = logging.getLogger(__name__)

app = FastAPI()

# Copilot client will be attached to app.state at startup
from app.core.copilot_settings import settings as copilot_settings
from app.lib.copilot_client import CopilotClient
from app.lib.copilot_token_manager import token_manager as copilot_token_manager


@app.on_event("startup")
async def startup_copilot_client():
    client = CopilotClient(timeout=copilot_settings.COPILOT_REQUEST_TIMEOUT)
    app.state.copilot_client = client
    app.state.copilot_token_manager = copilot_token_manager
    snippet_ai.preload_prompts()


@app.on_event("shutdown")
async def shutdown_copilot_client():
    client = getattr(app.state, "copilot_client", None)
    if client:
        await client.close()

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
