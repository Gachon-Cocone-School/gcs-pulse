from datetime import datetime, timedelta
import json
import logging
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException
from starlette.requests import Request
from starlette.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import get_db
from app.schemas import (
    DailySnippetCreate,
    DailySnippetFeedbackResponse,
    DailySnippetListResponse,
    DailySnippetOrganizeRequest,
    DailySnippetOrganizeResponse,
    DailySnippetPageDataResponse,
    DailySnippetResponse,
    DailySnippetUpdate,
)
from app.utils_time import current_business_key
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.routers import snippet_flow_helpers as _flow
from app.routers import snippet_utils
from app.limiter import limiter
from app.core.config import settings
from app.dependencies import require_professor_role, verify_csrf

router = APIRouter(prefix="/daily-snippets", tags=["daily-snippets"], dependencies=[Depends(verify_csrf)])
logger = logging.getLogger(__name__)
SNIPPET_WRITE_RATE_LIMIT = "300/minute" if settings.ENVIRONMENT == "test" else settings.SNIPPET_WRITE_LIMIT


def _wants_stream(request: Request, stream: bool | None) -> bool:
    if stream is not None:
        return stream

    accept = request.headers.get("accept", "")
    return "text/event-stream" in accept.lower()


def _sse_event(event: str, payload: dict) -> bytes:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n".encode("utf-8")


@router.get("/page-data", response_model=DailySnippetPageDataResponse)
async def get_daily_snippet_page_data(
    request: Request,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
    date: str | None = None,
):
    requested_key = None
    if date:
        try:
            requested_key = datetime.fromisoformat(date).date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date parameter") from exc

    return await _flow.build_snippet_page_data_response(
        request=request,
        db=db,
        snippet_id=id,
        requested_key=requested_key,
        kind="daily",
        key_attr="date",
        key_step=timedelta(days=1),
        get_snippet_viewer_or_401=snippet_utils.get_snippet_viewer_or_401,
        get_request_now=snippet_utils.get_request_now,
        current_business_key=current_business_key,
        build_snippet_page_data=snippet_utils.build_snippet_page_data,
        get_snippet_by_id=crud.get_daily_snippet_by_id,
        list_snippets=crud.list_daily_snippets,
        list_from_key_name="from_date",
        list_to_key_name="to_date",
    )


@router.get("/professor/page-data", response_model=DailySnippetPageDataResponse)
async def get_daily_snippet_page_data_for_professor(
    request: Request,
    student_user_id: int,
    db: AsyncSession = Depends(get_db),
    id: int | None = None,
    date: str | None = None,
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    require_professor_role(viewer)

    requested_key = None
    if date:
        try:
            requested_key = datetime.fromisoformat(date).date()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid date parameter") from exc

    now = snippet_utils.get_request_now(request)
    server_key = current_business_key("daily", now)
    if requested_key is not None and requested_key > server_key:
        raise HTTPException(status_code=400, detail="Future key is not allowed")

    async def _list_snippets_for_range(*, order, from_key, to_key):
        return await crud.list_daily_snippets_for_student(
            db,
            student_user_id=student_user_id,
            limit=1,
            offset=0,
            order=order,
            from_date=from_key,
            to_date=to_key,
        )

    async def _get_snippet_by_id(*args):
        snippet_id = args[-1]
        snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
        if not snippet or snippet.user_id != student_user_id:
            return None
        return snippet

    resolved_snippet_id = id
    if resolved_snippet_id is None and requested_key is None:
        latest_items, _ = await _list_snippets_for_range(
            order="desc",
            from_key=None,
            to_key=None,
        )
        if latest_items:
            resolved_snippet_id = latest_items[0].id

    return await snippet_utils.build_snippet_page_data(
        db=db,
        viewer=viewer,
        request=request,
        snippet_id=resolved_snippet_id,
        requested_key=requested_key,
        server_key=server_key,
        kind="daily",
        key_attr="date",
        key_step=timedelta(days=1),
        get_snippet_by_id=_get_snippet_by_id,
        list_snippets_for_range=lambda **kwargs: _list_snippets_for_range(
            order=kwargs["order"],
            from_key=kwargs["from_key"],
            to_key=kwargs["to_key"],
        ),
    )


@router.get("/{snippet_id:int}", response_model=DailySnippetResponse)
async def get_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )
    _flow.ensure_snippet_readable_or_403(
        viewer,
        owner,
        can_read_snippet=snippet_utils.can_read_snippet,
    )

    snippet_utils.set_snippet_editable(
        snippet,
        viewer,
        owner,
        "daily",
        "date",
        request,
    )

    return snippet


@router.get("", response_model=DailySnippetListResponse)
async def list_daily_snippets(
    request: Request,
    db: AsyncSession = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    order: str = "desc",
    from_date: str | None = None,
    to_date: str | None = None,
    id: int | None = None,
    q: str | None = None,
    scope: str = "own",
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    async def _get_snippet_by_id(snippet_id: int):
        return await crud.get_daily_snippet_by_id(db, snippet_id)

    # When a search query is provided, bypass the default date range restriction
    # so all matching snippets across all dates are returned.
    if q and not from_date and not to_date and id is None:
        parsed_from, parsed_to = None, None
    else:
        parsed_from, parsed_to, scope = await _flow.resolve_list_range_and_scope(
            from_key=from_date,
            to_key=to_date,
            snippet_id=id,
            scope=scope,
            request=request,
            kind="daily",
            key_attr="date",
            parse_key=lambda key: datetime.fromisoformat(key).date(),
            get_snippet_by_id=_get_snippet_by_id,
            get_request_now=snippet_utils.get_request_now,
            current_business_key=current_business_key,
        )

    items, total = await crud.list_daily_snippets(
        db,
        viewer=viewer,
        limit=limit,
        offset=offset,
        order=order,
        from_date=parsed_from,
        to_date=parsed_to,
        q=q,
        scope=scope,
    )

    await snippet_utils.apply_editable_to_snippet_list(
        db,
        items,
        viewer,
        "daily",
        "date",
        request,
    )

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.post("", response_model=DailySnippetResponse)
@limiter.limit(SNIPPET_WRITE_RATE_LIMIT)
async def create_daily_snippet(
    request: Request,
    payload: DailySnippetCreate,
    db: AsyncSession = Depends(get_db),
):
    return await _flow.create_snippet_for_current_key(
        request=request,
        db=db,
        content=payload.content,
        kind="daily",
        key_arg_name="snippet_date",
        get_snippet_viewer_or_401=snippet_utils.get_snippet_viewer_or_401,
        get_request_now=snippet_utils.get_request_now,
        current_business_key=current_business_key,
        upsert_snippet=crud.upsert_daily_snippet,
    )


@router.post("/organize", response_model=DailySnippetOrganizeResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def organize_daily_snippet(
    payload: DailySnippetOrganizeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
    stream: bool | None = None,
):
    total_start = perf_counter()
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    now = snippet_utils.get_request_now(request)
    snippet_date = current_business_key("daily", now)

    profile_context = {
        "channel": "http",
        "flow": "organize",
        "snippet_kind": "daily",
        "user_id": viewer.id,
    }

    raw_content = payload.content

    async def _build_suggestion_source() -> str:
        previous_date = snippet_date - timedelta(days=1)
        previous = await crud.get_daily_snippet_by_user_and_date(db, viewer.id, previous_date)
        previous_context = previous.content.strip() if previous else ""
        return _flow.build_daily_suggestion_source(snippet_date, previous_context)

    should_stream = _wants_stream(request, stream)

    if not should_stream:
        _, organized_content = await _flow.resolve_source_and_organized_content(
            raw_content=raw_content,
            copilot=copilot,
            organize_content_with_ai=snippet_utils.organize_content_with_ai,
            build_suggestion_source=_build_suggestion_source,
            suggestion_prompt_name="suggest_daily_from_previous.md",
            profile_context=profile_context,
            logger=logger,
        )

        logger.info(
            "snippet.organize.total",
            extra={
                **profile_context,
                "event": "snippet.organize.total",
                "status": "ok",
                "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
            },
        )

        return DailySnippetOrganizeResponse(
            date=snippet_date,
            organized_content=organized_content,
        )

    async def _event_stream():
        organized_chunks: list[str] = []
        prompt_name = "suggest_daily_from_previous.md"
        source_content = raw_content

        try:
            if not raw_content.strip():
                source_start = perf_counter()
                source_content = await _build_suggestion_source()
                logger.info(
                    "snippet.organize.stage",
                    extra={
                        **profile_context,
                        "event": "snippet.organize.stage",
                        "stage": "build_suggestion_source",
                        "status": "ok",
                        "elapsed_ms": round((perf_counter() - source_start) * 1000, 2),
                    },
                )

            stage_context = {
                **profile_context,
                "event": "snippet.organize.stage",
                "stage": "organize_ai",
                "prompt_name": prompt_name,
            }

            async for chunk in snippet_utils.organize_content_with_ai_stream(
                source_content,
                copilot,
                prompt_name=prompt_name,
                profile_context=stage_context,
            ):
                organized_chunks.append(chunk)
                yield _sse_event("chunk", {"content": chunk})

            organized_content = "".join(organized_chunks)
            logger.info(
                "snippet.organize.total",
                extra={
                    **profile_context,
                    "event": "snippet.organize.total",
                    "status": "ok",
                    "stream": True,
                    "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
                },
            )
            yield _sse_event(
                "done",
                {
                    "date": snippet_date.isoformat(),
                    "organized_content": organized_content,
                },
            )
        except HTTPException as exc:
            yield _sse_event("error", {"detail": exc.detail})
        except Exception:
            logger.exception(
                "snippet.organize.stream.failed",
                extra={
                    **profile_context,
                    "event": "snippet.organize.total",
                    "status": "error",
                    "stream": True,
                    "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
                },
            )
            yield _sse_event("error", {"detail": "AI processing failed"})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.get("/feedback", response_model=DailySnippetFeedbackResponse)
@limiter.limit(settings.SNIPPET_ORGANIZE_LIMIT)
async def generate_daily_snippet_feedback(
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
    stream: bool | None = None,
):
    total_start = perf_counter()
    snippet_date, snippet = await _flow.get_snippet_feedback_context(
        request=request,
        db=db,
        kind="daily",
        get_snippet_viewer_or_401=snippet_utils.get_snippet_viewer_or_401,
        get_request_now=snippet_utils.get_request_now,
        current_business_key=current_business_key,
        get_snippet=crud.get_daily_snippet_by_user_and_date,
    )
    content = _flow.require_snippet_content_or_400(snippet)

    playbook_content = snippet.playbook

    profile_context = {
        "channel": "http",
        "flow": "feedback",
        "snippet_kind": "daily",
        "user_id": snippet.user_id,
    }

    should_stream = _wants_stream(request, stream)

    if not should_stream:
        feedback_json = await _flow.generate_feedback_json_or_none(
            snippet_content=content,
            playbook_content=playbook_content,
            copilot=copilot,
            generate_feedback_with_ai=snippet_utils.generate_feedback_with_ai,
            parse_feedback_json=snippet_utils.parse_feedback_json,
            logger=logger,
            profile_context=profile_context,
        )

        await _flow.persist_snippet_feedback(db, snippet, feedback_json)

        return DailySnippetFeedbackResponse(
            date=snippet_date,
            feedback=feedback_json,
        )

    async def _event_stream():
        feedback_chunks: list[str] = []

        try:
            stage_context = {
                **profile_context,
                "event": "snippet.organize.stage",
                "stage": "feedback_ai",
                "prompt_name": "daily_feedback.md",
            }

            async for chunk in snippet_utils.generate_feedback_with_ai_stream(
                snippet_content=content,
                playbook_content=playbook_content,
                copilot=copilot,
                profile_context=stage_context,
            ):
                feedback_chunks.append(chunk)
                yield _sse_event("chunk", {"content": chunk})

            feedback_json = _flow.parse_feedback_json_or_none(
                "".join(feedback_chunks),
                parse_feedback_json=snippet_utils.parse_feedback_json,
                logger=logger,
                profile_context={
                    **profile_context,
                    "event": "snippet.organize.stage",
                    "stage": "feedback_parse",
                },
            )

            await _flow.persist_snippet_feedback(db, snippet, feedback_json)

            logger.info(
                "snippet.feedback.total",
                extra={
                    **profile_context,
                    "event": "snippet.feedback.total",
                    "status": "ok",
                    "stream": True,
                    "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
                },
            )
            yield _sse_event(
                "done",
                {
                    "date": snippet_date.isoformat(),
                    "feedback": feedback_json,
                },
            )
        except HTTPException as exc:
            yield _sse_event("error", {"detail": exc.detail})
        except Exception:
            logger.exception(
                "snippet.feedback.stream.failed",
                extra={
                    **profile_context,
                    "event": "snippet.feedback.total",
                    "status": "error",
                    "stream": True,
                    "elapsed_ms": round((perf_counter() - total_start) * 1000, 2),
                },
            )
            yield _sse_event("error", {"detail": "AI processing failed"})

    return StreamingResponse(
        _event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.put("/{snippet_id:int}", response_model=DailySnippetResponse)
@limiter.limit(SNIPPET_WRITE_RATE_LIMIT)
async def update_daily_snippet(
    snippet_id: int,
    payload: DailySnippetUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=snippet_utils.is_snippet_editable,
    )

    return await crud.update_daily_snippet(
        db,
        snippet=snippet,
        content=payload.content,
    )


@router.delete("/{snippet_id:int}")
@limiter.limit(SNIPPET_WRITE_RATE_LIMIT)
async def delete_daily_snippet(
    snippet_id: int, request: Request, db: AsyncSession = Depends(get_db)
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    snippet = await crud.get_daily_snippet_by_id(db, snippet_id)
    owner = await _flow.get_snippet_owner_or_404(
        db,
        snippet,
        get_user_by_id=crud.get_user_by_id,
    )

    _flow.ensure_snippet_editable_or_403(
        viewer,
        owner,
        snippet.date,
        kind="daily",
        request=request,
        is_snippet_editable=snippet_utils.is_snippet_editable,
    )

    await crud.delete_daily_snippet(db, snippet=snippet)
    return {"message": "Snippet deleted"}
