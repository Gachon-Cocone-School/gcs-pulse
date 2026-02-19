from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.responses import JSONResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from authlib.integrations.starlette_client import OAuth

from app.database import get_db
from app.schemas import MessageResponse, AuthStatusResponse
from app.limiter import limiter
from app.core.config import settings
from app import crud

router = APIRouter()

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
            user_info = {
                "sub": settings.TEST_AUTH_BYPASS_SUB,
                "email": settings.TEST_AUTH_BYPASS_EMAIL,
                "name": settings.TEST_AUTH_BYPASS_NAME,
                "picture": "",
                "email_verified": True,
            }
            await crud.create_or_update_user(db, user_info)
            request.session["user"] = user_info
            return RedirectResponse(url=settings.AUTH_SUCCESS_URL)

        client = oauth.create_client("google")
        if not client:
            raise HTTPException(status_code=500, detail="OAuth client not configured")

        token = await client.authorize_access_token(request)
        user_info = token.get("userinfo")

        if user_info:
            # Create or update user
            user = await crud.create_or_update_user(db, user_info)

            request.session["user"] = user_info

        return RedirectResponse(url=settings.AUTH_SUCCESS_URL)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@router.get("/auth/logout", summary="로그아웃", response_model=MessageResponse)
async def logout(request: Request):
    request.session.pop("user", None)
    return JSONResponse({"message": "Successfully logged out"})


@router.get("/auth/me", summary="내 정보 조회", response_model=AuthStatusResponse)
@limiter.limit(settings.ME_LIMIT)
async def me(request: Request, db: AsyncSession = Depends(get_db)):
    user_sub = request.session.get("user", {}).get("sub")
    if not user_sub:
        return JSONResponse({"authenticated": False, "user": None}, status_code=401)

    # CRUD 함수 사용
    db_user = await crud.get_user_by_sub(db, user_sub)

    if not db_user:
        request.session.pop("user", None)
        return JSONResponse({"authenticated": False, "user": None}, status_code=401)

    user_response = {
        "sub": db_user.google_sub,
        "name": db_user.name,
        "email": db_user.email,
        "picture": db_user.picture,
        "email_verified": True,
        "roles": db_user.roles,
        "consents": db_user.consents,
    }

    return {"authenticated": True, "user": user_response}
