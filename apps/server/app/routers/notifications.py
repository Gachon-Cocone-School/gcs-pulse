from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.core.config import settings
from app.database import get_db
from app.dependencies import verify_csrf
from app.limiter import limiter
from app.routers import snippet_utils

router = APIRouter(prefix="/notifications", tags=["notifications"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=schemas.NotificationListResponse)
async def list_notifications(
    request: Request,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    items, total = await crud.list_notifications(
        db,
        user_id=viewer.id,
        limit=limit,
        offset=offset,
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/{notification_id}/read", response_model=schemas.NotificationResponse)
async def mark_notification_read(
    notification_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    notification = await crud.get_notification_by_id_for_user(db, notification_id, viewer.id)
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    return await crud.mark_notification_as_read(db, notification)


@router.patch("/read-all", response_model=schemas.NotificationReadAllResponse)
async def mark_all_notifications_read(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    updated_count = await crud.mark_all_notifications_as_read(db, viewer.id)
    return {"updated_count": updated_count}


@router.get("/unread-count", response_model=schemas.NotificationUnreadCountResponse)
async def get_unread_notifications_count(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    unread_count = await crud.count_unread_notifications(db, viewer.id)
    return {"unread_count": unread_count}


@router.get("/settings", response_model=schemas.NotificationSettingResponse)
async def get_notification_settings(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)
    setting = await crud.get_or_create_notification_setting(db, viewer.id)
    return setting


@router.patch("/settings", response_model=schemas.NotificationSettingResponse)
@limiter.limit(settings.NOTIFICATIONS_WRITE_LIMIT)
async def update_notification_settings(
    payload: schemas.NotificationSettingUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    viewer = await snippet_utils.get_snippet_viewer_or_401(request, db)

    setting = await crud.get_or_create_notification_setting(db, viewer.id)
    updated = await crud.update_notification_setting(
        db,
        setting,
        notify_post_author=payload.notify_post_author,
        notify_mentions=payload.notify_mentions,
        notify_participants=payload.notify_participants,
    )
    return updated
