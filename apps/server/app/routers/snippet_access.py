from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core.config import settings
from app.models import ApiToken, User
from app.dependencies import require_privileged_api_role
from app.utils_time import current_business_date, to_business_timezone


@dataclass(frozen=True)
class BearerAuthContext:
    user: User
    api_token: ApiToken


def get_request_now(request: Request | None = None) -> datetime:
    if (
        request
        and settings.ENVIRONMENT == "test"
        and (override := request.headers.get("x-test-now"))
    ):
        try:
            parsed = datetime.fromisoformat(override)
            return to_business_timezone(parsed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid x-test-now header") from exc
    return to_business_timezone(datetime.now().astimezone())


def get_user_email(request: Request) -> str:
    email = request.session.get("user", {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email


async def get_viewer_or_401(
    request: Request,
    db: AsyncSession,
    include_consents: bool = True,
):
    email = get_user_email(request)
    viewer = (
        await crud.get_user_by_email(db, email)
        if include_consents
        else await crud.get_user_by_email_basic(db, email)
    )
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    require_privileged_api_role(viewer)
    return viewer


def get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    return token


async def get_bearer_auth_or_401(request: Request, db: AsyncSession) -> BearerAuthContext:
    bearer_token = get_bearer_token(request)
    if bearer_token is None:
        raise HTTPException(status_code=401, detail="Invalid API token")

    api_token = await crud.get_api_token_by_raw_token(db, bearer_token)
    if not api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    viewer = await crud.get_user_by_id(db, api_token.user_id)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    require_privileged_api_role(viewer)

    await crud.touch_api_token_last_used_at(db, api_token)
    return BearerAuthContext(user=viewer, api_token=api_token)


async def get_snippet_viewer_or_401(request: Request, db: AsyncSession):
    bearer_token = get_bearer_token(request)
    if bearer_token is not None:
        auth_context = await get_bearer_auth_or_401(request, db)
        return auth_context.user

    return await get_viewer_or_401(request, db)


def can_read_snippet(viewer, owner) -> bool:
    # allow owner or same-team members to read snippets
    if viewer.id == owner.id:
        return True
    if viewer.team_id and owner.team_id and viewer.team_id == owner.team_id:
        return True
    return False


def require_snippet_owner_write(viewer, owner) -> None:
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


def is_snippet_editable(
    viewer,
    owner,
    target_date_or_week,
    kind: str,
    now: datetime | None = None,
    request: Request | None = None,
) -> bool:
    """
    Return True if the snippet should be editable by viewer.
    Rules:
    - Only owner can edit (viewer.id == owner.id)
    - For daily: editable only if target_date == current_business_date(now)
    - For weekly: editable only if target_week == current_business_week_start(now)

    Does NOT raise: returns bool so callers can decide on 403 vs 400.
    """
    if viewer.id != owner.id:
        return False
    now = now or get_request_now(request)
    # import locally to avoid circular imports
    from app.utils_time import current_business_week_start

    if kind == "daily":
        return target_date_or_week == current_business_date(now)
    elif kind == "weekly":
        return target_date_or_week == current_business_week_start(now)
    else:
        return False


def is_snippet_editable_safe(
    viewer,
    owner,
    target_date_or_week,
    kind: str,
    request: Request | None = None,
) -> bool:
    try:
        return is_snippet_editable(
            viewer,
            owner,
            target_date_or_week,
            kind,
            request=request,
        )
    except Exception:
        return False


def set_snippet_editable(
    snippet,
    viewer,
    owner,
    kind: str,
    key_attr: str,
    request: Request,
    is_snippet_editable_fn=is_snippet_editable,
) -> bool:
    editable = is_snippet_editable_fn(
        viewer,
        owner,
        getattr(snippet, key_attr),
        kind,
        request=request,
    )
    setattr(snippet, "editable", editable)
    return editable


async def apply_editable_to_snippet_list(
    db: AsyncSession,
    snippets,
    viewer,
    kind: str,
    key_attr: str,
    request: Request,
) -> None:
    for snippet in snippets:
        try:
            owner = await crud.get_user_by_id(db, snippet.user_id)
            set_snippet_editable(
                snippet,
                viewer,
                owner,
                kind,
                key_attr,
                request,
            )
        except Exception:
            setattr(snippet, "editable", False)


async def build_snippet_page_data(
    db: AsyncSession,
    viewer,
    request: Request,
    snippet_id: int | None,
    server_key,
    kind: str,
    key_attr: str,
    key_step: timedelta,
    get_snippet_by_id,
    list_snippets_for_range,
    can_read_snippet_fn=can_read_snippet,
    is_snippet_editable_fn=None,
) -> dict:
    current_snippet = None
    current_key = server_key
    read_only = current_key < server_key
    editability_fn = is_snippet_editable_fn or is_snippet_editable

    if snippet_id is not None:
        candidate = await get_snippet_by_id(db, snippet_id)
        if candidate:
            owner = await crud.get_user_by_id(db, candidate.user_id)
            if owner and can_read_snippet_fn(viewer, owner):
                editable = set_snippet_editable(
                    candidate,
                    viewer,
                    owner,
                    kind,
                    key_attr,
                    request,
                    is_snippet_editable_fn=editability_fn,
                )
                current_snippet = candidate
                current_key = getattr(candidate, key_attr)
                read_only = not editable
    else:
        items, _ = await list_snippets_for_range(
            db=db,
            viewer=viewer,
            order="desc",
            from_key=server_key,
            to_key=server_key,
        )
        if items:
            candidate = items[0]
            try:
                owner = await crud.get_user_by_id(db, candidate.user_id)
                editable = set_snippet_editable(
                    candidate,
                    viewer,
                    owner,
                    kind,
                    key_attr,
                    request,
                    is_snippet_editable_fn=editability_fn,
                )
            except Exception:
                editable = False
                setattr(candidate, "editable", False)
            current_snippet = candidate
            current_key = getattr(candidate, key_attr)
            read_only = not editable

    prev_key = current_key - key_step
    next_key = current_key + key_step

    prev_items, _ = await list_snippets_for_range(
        db=db,
        viewer=viewer,
        order="desc",
        from_key=None,
        to_key=prev_key,
    )
    next_items, _ = await list_snippets_for_range(
        db=db,
        viewer=viewer,
        order="asc",
        from_key=next_key,
        to_key=None,
    )

    return {
        "snippet": current_snippet,
        "read_only": read_only,
        "prev_id": prev_items[0].id if prev_items else None,
        "next_id": next_items[0].id if next_items else None,
    }
