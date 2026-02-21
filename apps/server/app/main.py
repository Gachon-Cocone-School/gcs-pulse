from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.sessions import SessionMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.limiter import limiter
from app.routers import auth, daily_snippets, snippet_utils, terms, weekly_snippets, tokens, comments, teams
from app.core.config import settings

app = FastAPI()

# Copilot client will be attached to app.state at startup
from app.core.copilot_settings import settings as copilot_settings
from app.lib.copilot_client import CopilotClient
from app.lib.copilot_token_manager import token_manager as copilot_token_manager


@app.on_event("startup")
async def startup_copilot_client():
    # Debug: Print CWD and DB Path
    import os
    print(f"DEBUG: Current Working Directory: {os.getcwd()}")
    print(f"DEBUG: Configured DATABASE_URL: {settings.DATABASE_URL}")

    client = CopilotClient(timeout=copilot_settings.COPILOT_REQUEST_TIMEOUT)
    app.state.copilot_client = client
    app.state.copilot_token_manager = copilot_token_manager


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
    return JSONResponse({"detail": str(exc)}, status_code=500)


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)


def _validate_production_secret_key() -> None:
    if settings.ENVIRONMENT != "production":
        return

    secret_key = settings.SECRET_KEY.strip()
    if not secret_key or secret_key == "your-secret-key":
        raise RuntimeError("SECRET_KEY must be configured in production")


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
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(terms.router)
app.include_router(tokens.router)
app.include_router(teams.router)
app.include_router(snippet_utils.router)
app.include_router(daily_snippets.router)
app.include_router(weekly_snippets.router)
app.include_router(comments.router)

if __name__ == "__main__":
    import uvicorn

    # 로컬 개발용 실행 코드 (프로덕션에서는 보통 CLI로 실행)
    uvicorn.run(app, host="0.0.0.0", port=8000)
