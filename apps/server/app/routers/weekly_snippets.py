from datetime import datetime, timedelta
import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    WeeklySnippetCreate,
    WeeklySnippetListResponse,
    WeeklySnippetOrganizeResponse,
    WeeklySnippetPageDataResponse,
    WeeklySnippetResponse,
    WeeklySnippetUpdate,
)
from app.utils_time import current_business_key
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.limiter import limiter
from app.core.config import settings
from app.dependencies import verify_csrf

router = APIRouter(prefix="/weekly-snippets", tags=["weekly-snippets"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)


def _can_read(viewer, owner) -> bool:
    # allow owner or same-team members to read snippets (daily와 동일 정책)
    return _snippet_utils.can_read_snippet(viewer, owner)


def _require_owner_write(viewer, owner) -> None:
    # Only the owner may write (create/update/delete) their own snippets
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


from app.routers import snippet_utils as _snippet_utils


@router.get("/page-data", response_model=WeeklySnippetPageDataResponse)
async def get_weekly_snippet_page_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    server_key = current_business_key("weekly", now)

    current_snippet = None
    current_key = server_key
    read_only = current_key < server_key

    if id is not None:
        candidate = await crud.get_weekly_snippet_by_id(db, id)
        if candidate:
            owner = await crud.get_user_by_id(db, candidate.user_id)
            if owner and _can_read(viewer, owner):
                try:
                    editable = _snippet_utils.is_snippet_editable(
                        viewer,
                        owner,
                        candidate.week,
                        "weekly",
                        request=request,
                    )
                except Exception:
                    editable = False
                setattr(candidate, "editable", editable)
                current_snippet = candidate
                current_key = candidate.week
                read_only = not editable
    else:
        items, _ = await crud.list_weekly_snippets(
            db,
            viewer=viewer,
            limit=1,
            offset=0,
            order="desc",
            from_week=server_key,
            to_week=server_key,
            q=None,
            scope="own",
        )
        if items:
            candidate = items[0]
            try:
                owner = await crud.get_user_by_id(db, candidate.user_id)
                editable = _snippet_utils.is_snippet_editable(
                    viewer,
                    owner,
                    candidate.week,
                    "weekly",
                    request=request,
                )
            except Exception:
                editable = False
            setattr(candidate, "editable", editable)
            current_snippet = candidate
            current_key = candidate.week
            read_only = not editable

    prev_key = current_key - timedelta(days=7)
    next_key = current_key + timedelta(days=7)

    prev_items, _ = await crud.list_weekly_snippets(
        db,
        viewer=viewer,
        limit=1,
        offset=0,
        order="desc",
        from_week=None,
        to_week=prev_key,
        q=None,
        scope="own",
    )
    next_items, _ = await crud.list_weekly_snippets(
        db,
        viewer=viewer,
        limit=1,
        offset=0,
        order="asc",
        from_week=next_key,
        to_week=None,
        q=None,
        scope="own",
    )

    prev_id = prev_items[0].id if prev_items else None
    next_id = next_items[0].id if next_items else None

    return {
        "snippet": current_snippet,
        "read_only": read_only,
        "prev_id": prev_id,
        "next_id": next_id,
    }


@router.get("/{snippet_id}", response_model=WeeklySnippetResponse)
async def get_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    if not _can_read(viewer, owner):
        raise HTTPException(status_code=403, detail="Access denied")

    try:
        setattr(snippet, "editable", _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request))
    except Exception:
        setattr(snippet, "editable", False)

    return snippet


@router.get("", response_model=WeeklySnippetListResponse)
async def list_weekly_snippets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
    from_week: str | None = None,
    to_week: str | None = None,
    id: int | None = None,
    q: str | None = None,
    scope: str = "own",
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    parsed_from = datetime.fromisoformat(from_week).date() if from_week else None
    parsed_to = datetime.fromisoformat(to_week).date() if to_week else None

    # If id is provided, show the team snippets for the week of that snippet
    if id is not None:
        snippet = await crud.get_weekly_snippet_by_id(db, id)
        if not snippet:
            raise HTTPException(status_code=404, detail="Snippet not found")
        parsed_from = parsed_to = snippet.week
        scope = "team"

    if parsed_from is None and parsed_to is None:
        now = _snippet_utils.get_request_now(request)
        week_start = current_business_key("weekly", now)
        parsed_from = parsed_to = week_start

    items, total = await crud.list_weekly_snippets(
        db,
        viewer=viewer,
        limit=limit,
        offset=offset,
        order=order,
        from_week=parsed_from,
        to_week=parsed_to,
        q=q,
        scope=scope,
    )

    # attach editable flag per item
    for s in items:
        try:
            owner = await crud.get_user_by_id(db, s.user_id)
            setattr(s, "editable", _snippet_utils.is_snippet_editable(viewer, owner, s.week, "weekly", request=request))
        except Exception:
            setattr(s, "editable", False)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=WeeklySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def create_weekly_snippet(
    payload: WeeklySnippetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    return await crud.upsert_weekly_snippet(
        db,
        user_id=viewer.id,
        week=week,
        content=payload.content,
    )


@router.post("/organize", response_model=WeeklySnippetOrganizeResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def organize_weekly_snippet(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    now = _snippet_utils.get_request_now(request)
    week = current_business_key("weekly", now)

    snippet = await crud.get_weekly_snippet_by_user_and_week(db, viewer.id, week)
    if not snippet:
        snippet = await crud.upsert_weekly_snippet(
            db,
            user_id=viewer.id,
            week=week,
            content="",
        )

    if not snippet.content.strip():
        week_end = week + timedelta(days=6)
        daily_items, _ = await crud.list_daily_snippets(
            db,
            viewer=viewer,
            limit=7,
            offset=0,
            order="asc",
            from_date=week,
            to_date=week_end,
            q=None,
            scope="own",
        )

        weekly_context_parts: list[str] = []
        for daily_item in daily_items:
            daily_text = (daily_item.structured or daily_item.content or "").strip()
            if daily_text:
                weekly_context_parts.append(f"### {daily_item.date.isoformat()}\n{daily_text}")

        weekly_context = "\n\n".join(weekly_context_parts) if weekly_context_parts else "(이번 주 Daily Snippet 없음)"
        suggestion_source = (
            f"이번 주 시작일: {week.isoformat()}\n\n"
            f"이번 주 Daily Snippets:\n{weekly_context}"
        )

        suggested_content = await _snippet_utils.organize_content_with_ai(
            suggestion_source,
            copilot,
            prompt_name="organize_weekly.md",
        )

        feedback_json = await _snippet_utils.generate_feedback_with_ai(
            daily_snippet_content=suggestion_source,
            organized_content=suggested_content,
            playbook_content=snippet.playbook,
            copilot=copilot,
            prompt_name="weekly_feedback.md",
            snippet_label="Weekly Snippet",
        )

        try:
            parsed_feedback = _snippet_utils.parse_feedback_json(feedback_json)
            playbook_update = parsed_feedback.get("playbook_update_markdown")

            await crud.update_weekly_snippet(
                db,
                snippet=snippet,
                content=snippet.content,
                structured=suggested_content,
                playbook=playbook_update,
                feedback=feedback_json,
            )
        except ValueError:
            logger.error(f"Failed to parse AI feedback JSON: {feedback_json}")
            await crud.update_weekly_snippet(
                db,
                snippet=snippet,
                content=snippet.content,
                structured=suggested_content,
            )

        await db.refresh(snippet)
        return WeeklySnippetOrganizeResponse.model_validate(snippet)

    organized_content = await _snippet_utils.organize_content_with_ai(
        snippet.content,
        copilot,
        prompt_name="organize_weekly.md",
    )

    feedback_json = await _snippet_utils.generate_feedback_with_ai(
        daily_snippet_content=snippet.content,
        organized_content=organized_content,
        playbook_content=snippet.playbook,
        copilot=copilot,
        prompt_name="weekly_feedback.md",
        snippet_label="Weekly Snippet",
    )

    try:
        parsed_feedback = _snippet_utils.parse_feedback_json(feedback_json)
        playbook_update = parsed_feedback.get("playbook_update_markdown")

        await crud.update_weekly_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
            playbook=playbook_update,
            feedback=feedback_json,
        )
    except ValueError:
        logger.error(f"Failed to parse AI feedback JSON: {feedback_json}")
        await crud.update_weekly_snippet(
            db,
            snippet=snippet,
            content=snippet.content,
            structured=organized_content,
        )

    await db.refresh(snippet)
    return WeeklySnippetOrganizeResponse.model_validate(snippet)


@router.put("/{snippet_id}", response_model=WeeklySnippetResponse)
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def update_weekly_snippet(
    snippet_id: int,
    payload: WeeklySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

    return await crud.update_weekly_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id}")
@limiter.limit(settings.SNIPPET_WRITE_LIMIT)
async def delete_weekly_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await _snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_weekly_snippet_by_id(db, snippet_id)
    if not snippet:
        raise HTTPException(status_code=404, detail="Snippet not found")

    owner = await crud.get_user_by_id(db, snippet.user_id)
    if not owner:
        raise HTTPException(status_code=404, detail="Owner not found")

    # owner check + editable enforcement
    if not _snippet_utils.is_snippet_editable(viewer, owner, snippet.week, "weekly", request=request):
        raise HTTPException(status_code=403, detail="Not editable")

    await crud.delete_weekly_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
