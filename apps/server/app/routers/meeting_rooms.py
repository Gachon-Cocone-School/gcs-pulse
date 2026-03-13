from datetime import date, datetime, time, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
import app.crud_meeting_rooms as crud_meeting_rooms
from app.database import get_db
from app.dependencies import get_active_user
from app.models import User

router = APIRouter(prefix="/meeting-rooms", tags=["meeting-rooms"])


def _is_admin(user: User) -> bool:
    return bool(user.roles and "admin" in user.roles)


def _reservation_display_name(reservation) -> str:
    if reservation.reserved_by and reservation.reserved_by.name:
        return reservation.reserved_by.name
    if reservation.reserved_by and reservation.reserved_by.email:
        return reservation.reserved_by.email
    return f"user:{reservation.reserved_by_user_id}"


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
    day_start = datetime.combine(date, time.min)
    day_end = day_start + timedelta(days=1)
    reservations = await crud_meeting_rooms.list_room_reservations_for_day(
        db,
        room_id=room_id,
        day_start=day_start,
        day_end=day_end,
    )

    is_admin = _is_admin(user)
    return [
        schemas.MeetingRoomReservationResponse(
            id=reservation.id,
            meeting_room_id=reservation.meeting_room_id,
            reserved_by_user_id=reservation.reserved_by_user_id,
            reserved_by_name=_reservation_display_name(reservation),
            start_at=reservation.start_at,
            end_at=reservation.end_at,
            purpose=reservation.purpose,
            can_cancel=(reservation.reserved_by_user_id == user.id or is_admin),
            created_at=reservation.created_at,
            updated_at=reservation.updated_at,
        )
        for reservation in reservations
    ]


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
    is_admin = _is_admin(user)
    if not is_owner and not is_admin:
        raise HTTPException(status_code=403, detail="Only owner or admin can cancel this reservation")

    await crud_meeting_rooms.delete_reservation(db, reservation)
    return schemas.MessageResponse(message="Deleted")
