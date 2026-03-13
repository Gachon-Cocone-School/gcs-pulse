from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MeetingRoom, MeetingRoomReservation


async def list_meeting_rooms(db: AsyncSession) -> list[MeetingRoom]:
    result = await db.execute(select(MeetingRoom).order_by(MeetingRoom.id.asc()))
    return list(result.scalars().all())


async def get_meeting_room_by_id(db: AsyncSession, room_id: int) -> MeetingRoom | None:
    result = await db.execute(select(MeetingRoom).filter(MeetingRoom.id == room_id))
    return result.scalars().first()


async def list_room_reservations_for_day(
    db: AsyncSession,
    *,
    room_id: int,
    day_start,
    day_end,
) -> list[MeetingRoomReservation]:
    result = await db.execute(
        select(MeetingRoomReservation)
        .filter(
            MeetingRoomReservation.meeting_room_id == room_id,
            MeetingRoomReservation.start_at < day_end,
            MeetingRoomReservation.end_at > day_start,
        )
        .order_by(MeetingRoomReservation.start_at.asc(), MeetingRoomReservation.id.asc())
    )
    return list(result.scalars().all())


async def has_overlapping_reservation(
    db: AsyncSession,
    *,
    room_id: int,
    start_at,
    end_at,
) -> bool:
    result = await db.execute(
        select(MeetingRoomReservation.id)
        .filter(
            MeetingRoomReservation.meeting_room_id == room_id,
            MeetingRoomReservation.start_at < end_at,
            MeetingRoomReservation.end_at > start_at,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def create_reservation(
    db: AsyncSession,
    *,
    room_id: int,
    reserved_by_user_id: int,
    start_at,
    end_at,
    purpose: str | None,
) -> MeetingRoomReservation:
    reservation = MeetingRoomReservation(
        meeting_room_id=room_id,
        reserved_by_user_id=reserved_by_user_id,
        start_at=start_at,
        end_at=end_at,
        purpose=purpose,
    )
    db.add(reservation)
    await db.commit()
    await db.refresh(reservation)
    return reservation


async def get_reservation_by_id(db: AsyncSession, reservation_id: int) -> MeetingRoomReservation | None:
    result = await db.execute(
        select(MeetingRoomReservation).filter(MeetingRoomReservation.id == reservation_id)
    )
    return result.scalars().first()


async def delete_reservation(db: AsyncSession, reservation: MeetingRoomReservation) -> None:
    await db.delete(reservation)
    await db.commit()
