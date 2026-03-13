from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
import app.crud_meeting_rooms as crud_meeting_rooms
from app.database import get_db
from app.dependencies import get_active_user
from app.models import User

router = APIRouter(prefix="/meeting-rooms", tags=["meeting-rooms"])


@router.get("", response_model=list[schemas.MeetingRoomResponse])
async def list_meeting_rooms(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    del user
    return await crud_meeting_rooms.list_meeting_rooms(db)


@router.get("/{room_id}/reservations", response_model=list[schemas.MeetingRoomReservationResponse])
async def list_room_reservations(
    room_id: int,
    date: date,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    del user
    day_start = datetime.combine(date, time.min)
    day_end = day_start + timedelta(days=1)
    return await crud_meeting_rooms.list_room_reservations_for_day(
        db,
        room_id=room_id,
        day_start=day_start,
        day_end=day_end,
    )


@router.post("/{room_id}/reservations", response_model=schemas.MeetingRoomReservationResponse)
async def create_reservation(
    room_id: int,
    payload: schemas.MeetingRoomReservationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    if payload.start_at >= payload.end_at:
        raise HTTPException(status_code=400, detail="start_at must be earlier than end_at")

    has_overlap = await crud_meeting_rooms.has_overlapping_reservation(
        db,
        room_id=room_id,
        start_at=payload.start_at,
        end_at=payload.end_at,
    )
    if has_overlap:
        raise HTTPException(status_code=409, detail="Reservation time overlaps with an existing booking")

    return await crud_meeting_rooms.create_reservation(
        db,
        room_id=room_id,
        reserved_by_user_id=user.id,
        start_at=payload.start_at,
        end_at=payload.end_at,
        purpose=(payload.purpose or "").strip() or None,
    )


@router.delete("/reservations/{reservation_id}", response_model=schemas.MessageResponse)
async def cancel_reservation(
    reservation_id: int,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    reservation = await crud_meeting_rooms.get_reservation_by_id(db, reservation_id)
    if reservation is None:
        raise HTTPException(status_code=404, detail="Reservation not found")

    is_owner = reservation.reserved_by_user_id == user.id
    is_admin = bool(user.roles and "admin" in user.roles)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only owner or admin can cancel this reservation")

    await crud_meeting_rooms.delete_reservation(db, reservation)
    return schemas.MessageResponse(message="Deleted")
