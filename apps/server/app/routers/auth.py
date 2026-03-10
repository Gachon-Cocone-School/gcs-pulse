from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

import logging

from app.database import get_db
from app.schemas import MessageResponse, AuthStatusResponse
from app.limiter import limiter, auth_me_rate_limit_key
from app.core.config import settings
from app.dependencies import ensure_csrf_token, verify_csrf

from app import crud

router = APIRouter(dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)

ME_RATE_LIMIT = "300/minute" if settings.ENVIRONMENT == "test" else settings.ME_LIMIT

# OAuth Setup
oauth = OAuth()
oauth.register(
    name="google",
    server_metadata_url=settings.GOOGLE_CONF_URL,
    client_kwargs={"scope": settings.GOOGLE_CLIENT_SCOPE},
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
)


@router.get("/auth/google/login", summary="구글 로그인")
@limiter.limit(settings.LOGIN_LIMIT)
async def login(request: Request):
    redirect_uri = request.url_for("auth_callback")
    client = oauth.create_client("google")
    if not client:
        raise HTTPException(status_code=500, detail="OAuth client not configured")
    return await client.authorize_redirect(request, redirect_uri)


@router.get("/auth/google/callback", summary="구글 로그인 콜백", name="auth_callback")
async def auth_callback(request: Request, db: AsyncSession = Depends(get_db)):
    try:
        is_test_auth_bypass = (
            settings.ENVIRONMENT == "test" and settings.TEST_AUTH_BYPASS_ENABLED
        )
        if is_test_auth_bypass:
            bypass_email = (
                str(request.query_params.get("test_email") or "").strip().lower()
                or settings.TEST_AUTH_BYPASS_EMAIL
            )
            bypass_name = (
                str(request.query_params.get("test_name") or "").strip()
                or settings.TEST_AUTH_BYPASS_NAME
            )

            user_info = {
                "email": bypass_email,
                "name": bypass_name,
                "picture": "",
                "email_verified": True,
            }
            await crud.create_or_update_user(db, user_info)
            request.session["user"] = {
                "email": user_info["email"],
                "name": user_info["name"],
                "picture": user_info["picture"],
                "email_verified": user_info["email_verified"],
            }
            request.session.pop("csrf_token", None)
            ensure_csrf_token(request)
            return RedirectResponse(url=settings.AUTH_SUCCESS_URL)

        client = oauth.create_client("google")
        if not client:
            raise HTTPException(status_code=500, detail="OAuth client not configured")

        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo")

        if user_info:
            # Create or update user
            await crud.create_or_update_user(db, user_info)

            request.session["user"] = {
                "email": user_info.get("email"),
                "name": user_info.get("name"),
                "picture": user_info.get("picture") or "",
                "email_verified": bool(user_info.get("email_verified", True)),
            }
            request.session.pop("csrf_token", None)
            ensure_csrf_token(request)

        return RedirectResponse(url=settings.AUTH_SUCCESS_URL)
    except DBAPIError:
        logger.exception("OAuth callback failed due to database connectivity")
        return JSONResponse({"error": "Authentication failed"}, status_code=400)
    except SQLAlchemyError:
        logger.exception("OAuth callback failed due to database error")
        return JSONResponse({"error": "Authentication failed"}, status_code=400)
    except Exception:
        logger.exception("OAuth callback failed due to OAuth provider/client error")
        return JSONResponse({"error": "Authentication failed"}, status_code=400)


@router.get("/auth/csrf", summary="CSRF 토큰 발급")
async def get_csrf_token(request: Request):
    csrf_token = ensure_csrf_token(request)
    return {"csrf_token": csrf_token}


@router.post("/auth/logout", summary="로그아웃", response_model=MessageResponse)
async def logout(request: Request):
    request.session.pop("user", None)
    request.session.pop("csrf_token", None)
    return JSONResponse({"message": "Successfully logged out"})


@router.get("/auth/me", summary="내 정보 조회", response_model=AuthStatusResponse)
@limiter.limit(ME_RATE_LIMIT, key_func=auth_me_rate_limit_key)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    session_user = request.session.get("user", {})
    user_email = session_user.get("email")
    if not user_email:
        return JSONResponse({"authenticated": False, "user": None}, status_code=401)

    db_user = await crud.get_user_by_email(db, user_email)

    if not db_user:
        request.session.pop("user", None)
        return JSONResponse({"authenticated": False, "user": None}, status_code=401)

    user_response = {
        "name": db_user.name,
        "email": db_user.email,
        "picture": db_user.picture,
        "email_verified": True,
        "roles": db_user.roles,
        "league_type": db_user.league_type,
        "consents": db_user.consents,
    }

    return {"authenticated": True, "user": user_response}
