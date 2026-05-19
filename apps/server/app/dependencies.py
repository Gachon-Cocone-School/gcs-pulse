import asyncio
import logging
import secrets
from types import SimpleNamespace

from fastapi import Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder

logger = logging.getLogger(__name__)
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.database import AsyncSessionLocal
from app.lib.active_user_cache import (
    get_active_user_hard_context_cache,
    get_active_user_profile_cache,
    get_active_user_ui_roles_cache,
)
from app import crud
from app.models import User as UserModel
from app.models import Term as TermModel

SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}
PRIVILEGED_API_ROLES = frozenset({"gcs", "교수", "admin"})
SNIPPET_FULL_READ_ROLES = frozenset({"교수", "admin"})
SNIPPET_TEAM_READ_ROLES = frozenset({"gcs"})
SNIPPET_ACCESS_ROLES = SNIPPET_FULL_READ_ROLES | SNIPPET_TEAM_READ_ROLES


def _extract_roles(user: object | None) -> set[str]:
    if user is None:
        return set()

    if isinstance(user, dict):
        raw_roles = user.get("roles")
    else:
        raw_roles = getattr(user, "roles", None)

    if not isinstance(raw_roles, (list, tuple, set)):
        return set()

    roles: set[str] = set()
    for role in raw_roles:
        normalized = str(role).strip()
        if normalized:
            roles.add(normalized)
    return roles


def has_privileged_api_role(user: object | None) -> bool:
    return bool(_extract_roles(user) & PRIVILEGED_API_ROLES)


def has_professor_role(user: object | None) -> bool:
    return "교수" in _extract_roles(user)


def has_professor_or_admin_role(user: object | None) -> bool:
    roles = _extract_roles(user)
    return "교수" in roles or "admin" in roles


def require_privileged_api_role(user: object | None) -> None:
    if not has_privileged_api_role(user):
        raise HTTPException(status_code=403, detail="Forbidden")


def require_professor_role(user: object | None) -> None:
    if not has_professor_role(user):
        raise HTTPException(status_code=403, detail="Professor only")


def require_professor_or_admin_role(user: object | None) -> None:
    if not has_professor_or_admin_role(user):
        raise HTTPException(status_code=403, detail="Professor or admin only")


def has_snippet_full_read_role(user: object | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_FULL_READ_ROLES)


def has_snippet_team_read_role(user: object | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_TEAM_READ_ROLES)


def has_snippet_access_role(user: object | None) -> bool:
    return bool(_extract_roles(user) & SNIPPET_ACCESS_ROLES)


def require_snippet_access_role(user: object | None) -> None:
    if not has_snippet_access_role(user):
        raise HTTPException(status_code=403, detail="Forbidden")


def ensure_csrf_token(request: Request) -> str:
    token = request.session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        request.session["csrf_token"] = token
    return token


def get_bearer_token_from_request(
    request: Request,
    *,
    invalid_detail: str | None = None,
) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    if not token:
        if invalid_detail is None:
            return None
        raise HTTPException(status_code=401, detail=invalid_detail)

    return token


def is_bearer_request(request: Request) -> bool:
    return get_bearer_token_from_request(request) is not None


def verify_csrf(request: Request) -> None:
    if request.method.upper() in SAFE_METHODS:
        return

    if is_bearer_request(request):
        return

    session_token = request.session.get("csrf_token")
    header_token = request.headers.get("x-csrf-token")
    logger.warning(
        "[CSRF DEBUG] method=%s path=%s session_token=%r header_token=%r cookie=%r",
        request.method,
        request.url.path,
        session_token,
        header_token,
        request.headers.get("cookie", "")[:80],
    )
    if not session_token or not header_token or session_token != header_token:
        raise HTTPException(status_code=403, detail="CSRF validation failed")


def get_session_user_info_or_401(request: Request) -> dict:
    user_info = request.session.get("user")
    if not isinstance(user_info, dict) or not user_info:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user_info


def get_session_email_or_401(request: Request) -> str:
    user_info = get_session_user_info_or_401(request)
    email = user_info.get("email")
    if not isinstance(email, str) or not email.strip():
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email.strip().lower()


async def load_session_user_or_401(request: Request, db, *, basic: bool = True):
    email = get_session_email_or_401(request)
    user = (
        await crud.get_user_by_email_basic(db, email)
        if basic
        else await crud.get_user_by_email(db, email)
    )
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


# Dependency for getting current user (session 또는 Bearer 토큰)
async def get_current_user(request: Request):
    if is_bearer_request(request):
        from app.routers.snippet_access import load_bearer_identity_or_401

        async with AsyncSessionLocal() as db:
            auth_context = await load_bearer_identity_or_401(
                request,
                db,
                invalid_detail="Not authenticated",
                require_snippet_role=False,
                include_consents=False,
            )
            user = auth_context.user
            return {"email": user.email, "name": user.name, "roles": user.roles}

    return get_session_user_info_or_401(request)


async def get_missing_required_term_ids(db, db_user: UserModel) -> list[int]:
    terms_result = await db.execute(
        select(TermModel.id).filter(
            TermModel.is_active == True, TermModel.is_required == True
        )
    )
    required_term_ids = set(terms_result.scalars().all())
    agreed_term_ids = {c.term_id for c in db_user.consents}
    return [tid for tid in required_term_ids if tid not in agreed_term_ids]


def _build_active_user_profile_payload(db_user: UserModel) -> dict:
    return jsonable_encoder(
        {
            "id": db_user.id,
            "email": db_user.email,
            "name": db_user.name,
            "picture": db_user.picture,
            "is_provisional": db_user.is_provisional,
        }
    )


def _build_active_user_ui_roles_payload(db_user: UserModel) -> dict:
    return jsonable_encoder(
        {
            "roles": db_user.roles or ["user"],
            "league_type": db_user.league_type or "none",
            "token_usage_short": db_user.token_usage_short,
        }
    )


def _build_active_user_hard_context_payload(
    db_user: UserModel, missing_required_term_ids: list[int]
) -> dict:
    return jsonable_encoder(
        {
            "id": db_user.id,
            "email": db_user.email,
            "team_id": db_user.team_id,
            "consents": db_user.consents,
            "has_required_consents": not missing_required_term_ids,
            "missing_required_term_ids": list(missing_required_term_ids),
        }
    )


def _merge_active_user_payloads(
    profile_payload: dict,
    ui_roles_payload: dict,
    hard_context_payload: dict,
) -> dict:
    return {
        **profile_payload,
        **ui_roles_payload,
        **hard_context_payload,
    }


def _restore_active_user_payload(payload: dict) -> SimpleNamespace:
    consents = [SimpleNamespace(**consent) for consent in payload.get("consents", [])]
    return SimpleNamespace(**{**payload, "consents": consents})


async def _read_cached_active_user_payload(
    request: Request,
    user_email: str,
) -> dict | None:
    profile_cache = get_active_user_profile_cache(request)
    ui_roles_cache = get_active_user_ui_roles_cache(request)
    hard_context_cache = get_active_user_hard_context_cache(request)

    if not (profile_cache and ui_roles_cache and hard_context_cache):
        return None

    cached_profile, cached_ui_roles, cached_hard_context = await asyncio.gather(
        profile_cache.get(user_email),
        ui_roles_cache.get(user_email),
        hard_context_cache.get(user_email),
    )
    if (
        cached_profile is None
        or cached_ui_roles is None
        or cached_hard_context is None
    ):
        return None

    return _merge_active_user_payloads(
        cached_profile,
        cached_ui_roles,
        cached_hard_context,
    )


async def _write_active_user_payload(
    request: Request,
    user_email: str,
    profile_payload: dict,
    ui_roles_payload: dict,
    hard_context_payload: dict,
) -> None:
    profile_cache = get_active_user_profile_cache(request)
    ui_roles_cache = get_active_user_ui_roles_cache(request)
    hard_context_cache = get_active_user_hard_context_cache(request)

    if not (profile_cache and ui_roles_cache and hard_context_cache):
        return

    await asyncio.gather(
        profile_cache.set(user_email, profile_payload),
        ui_roles_cache.set(user_email, ui_roles_payload),
        hard_context_cache.set(user_email, hard_context_payload),
    )


async def load_active_user_payload(request: Request, user_email: str) -> dict:
    cached_payload = await _read_cached_active_user_payload(request, user_email)
    if cached_payload is not None:
        return cached_payload

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(UserModel)
            .options(selectinload(UserModel.consents))
            .filter(func.lower(UserModel.email) == user_email.strip().lower())
        )
        db_user = result.scalars().first()

        if not db_user:
            raise HTTPException(status_code=401, detail="User not found")

        missing_terms = await get_missing_required_term_ids(db, db_user)
        profile_payload = _build_active_user_profile_payload(db_user)
        ui_roles_payload = _build_active_user_ui_roles_payload(db_user)
        hard_context_payload = _build_active_user_hard_context_payload(
            db_user,
            missing_terms,
        )

    await _write_active_user_payload(
        request,
        user_email,
        profile_payload,
        ui_roles_payload,
        hard_context_payload,
    )

    return _merge_active_user_payloads(
        profile_payload,
        ui_roles_payload,
        hard_context_payload,
    )


async def _load_active_user(request: Request, user_email: str):
    payload = await load_active_user_payload(request, user_email)
    restored = _restore_active_user_payload(payload)
    require_privileged_api_role(restored)

    if not restored.has_required_consents:
        raise HTTPException(
            status_code=403,
            detail={
                "message": "Terms agreement required",
                "missing_terms": list(restored.missing_required_term_ids),
            },
        )

    return restored


# Dependency for checking if user has agreed to all required terms
async def get_active_user(request: Request, user: dict = Depends(get_current_user)):
    user_email = user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return await _load_active_user(request, user_email)
