import asyncio
import inspect
from datetime import date, datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException

from app.routers import meeting_rooms as _meeting_rooms

meeting_rooms = cast(Any, _meeting_rooms)


def test_list_meeting_rooms_success(monkeypatch):
    async def fake_list_meeting_rooms(_db):
        now = datetime.now(timezone.utc)
        return [
            SimpleNamespace(
                id=1,
                name='A 회의실',
                location='본관 3층',
                description='프로젝트 미팅용',
                image_url=None,
                created_at=now,
                updated_at=now,
            )
        ]

    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'list_meeting_rooms', fake_list_meeting_rooms)

    result = asyncio.run(
        inspect.unwrap(meeting_rooms.list_meeting_rooms)(
            db=object(),
            user=SimpleNamespace(id=10, roles=['gcs']),
        )
    )

    assert len(result) == 1
    assert result[0].id == 1
    assert result[0].name == 'A 회의실'


def test_list_room_reservations_for_day_uses_day_window(monkeypatch):
    captured: dict[str, datetime] = {}

    async def fake_list_room_reservations_for_day(_db, *, room_id, day_start, day_end):
        captured['room_id'] = room_id
        captured['day_start'] = day_start
        captured['day_end'] = day_end
        return []

    monkeypatch.setattr(
        meeting_rooms.crud_meeting_rooms,
        'list_room_reservations_for_day',
        fake_list_room_reservations_for_day,
    )

    target_day = date(2026, 3, 13)
    result = asyncio.run(
        inspect.unwrap(meeting_rooms.list_room_reservations)(
            room_id=5,
            date=target_day,
            db=object(),
            user=SimpleNamespace(id=10, roles=['교수']),
        )
    )

    assert result == []
    assert captured['room_id'] == 5
    assert captured['day_start'].isoformat() == '2026-03-13T00:00:00'
    assert captured['day_end'].isoformat() == '2026-03-14T00:00:00'


def test_create_reservation_rejects_invalid_time_range():
    payload = SimpleNamespace(
        start_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        purpose='회의',
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(meeting_rooms.create_reservation)(
                room_id=1,
                payload=payload,
                db=object(),
                user=SimpleNamespace(id=11, roles=['admin']),
            )
        )

    assert exc_info.value.status_code == 400


def test_create_reservation_rejects_overlap(monkeypatch):
    async def fake_has_overlapping_reservation(_db, *, room_id, start_at, end_at):
        assert room_id == 2
        assert start_at.isoformat() == '2026-03-13T09:00:00+00:00'
        assert end_at.isoformat() == '2026-03-13T10:00:00+00:00'
        return True

    monkeypatch.setattr(
        meeting_rooms.crud_meeting_rooms,
        'has_overlapping_reservation',
        fake_has_overlapping_reservation,
    )

    payload = SimpleNamespace(
        start_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        purpose='중복 테스트',
    )

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(meeting_rooms.create_reservation)(
                room_id=2,
                payload=payload,
                db=object(),
                user=SimpleNamespace(id=11, roles=['gcs']),
            )
        )

    assert exc_info.value.status_code == 409


def test_create_reservation_success_trims_purpose(monkeypatch):
    async def fake_has_overlapping_reservation(_db, *, room_id, start_at, end_at):
        return False

    async def fake_create_reservation(
        _db,
        *,
        room_id,
        reserved_by_user_id,
        start_at,
        end_at,
        purpose,
    ):
        now = datetime.now(timezone.utc)
        return SimpleNamespace(
            id=77,
            meeting_room_id=room_id,
            reserved_by_user_id=reserved_by_user_id,
            start_at=start_at,
            end_at=end_at,
            purpose=purpose,
            created_at=now,
            updated_at=now,
        )

    monkeypatch.setattr(
        meeting_rooms.crud_meeting_rooms,
        'has_overlapping_reservation',
        fake_has_overlapping_reservation,
    )
    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'create_reservation', fake_create_reservation)

    payload = SimpleNamespace(
        start_at=datetime(2026, 3, 13, 9, 0, tzinfo=timezone.utc),
        end_at=datetime(2026, 3, 13, 10, 0, tzinfo=timezone.utc),
        purpose='  킥오프 미팅  ',
    )

    result = asyncio.run(
        inspect.unwrap(meeting_rooms.create_reservation)(
            room_id=3,
            payload=payload,
            db=object(),
            user=SimpleNamespace(id=15, roles=['교수']),
        )
    )

    assert result.id == 77
    assert result.meeting_room_id == 3
    assert result.reserved_by_user_id == 15
    assert result.purpose == '킥오프 미팅'


def test_cancel_reservation_returns_404_when_not_found(monkeypatch):
    async def fake_get_reservation_by_id(_db, reservation_id):
        assert reservation_id == 999
        return None

    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'get_reservation_by_id', fake_get_reservation_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(meeting_rooms.cancel_reservation)(
                reservation_id=999,
                db=object(),
                user=SimpleNamespace(id=1, roles=['gcs']),
            )
        )

    assert exc_info.value.status_code == 404


def test_cancel_reservation_requires_owner_or_admin(monkeypatch):
    async def fake_get_reservation_by_id(_db, reservation_id):
        return SimpleNamespace(id=reservation_id, reserved_by_user_id=200)

    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'get_reservation_by_id', fake_get_reservation_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(meeting_rooms.cancel_reservation)(
                reservation_id=10,
                db=object(),
                user=SimpleNamespace(id=100, roles=['gcs']),
            )
        )

    assert exc_info.value.status_code == 403


def test_cancel_reservation_allows_owner(monkeypatch):
    deleted: dict[str, bool] = {'called': False}

    reservation_obj = SimpleNamespace(id=10, reserved_by_user_id=100)

    async def fake_get_reservation_by_id(_db, reservation_id):
        return reservation_obj

    async def fake_delete_reservation(_db, reservation):
        assert reservation is reservation_obj
        deleted['called'] = True

    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'get_reservation_by_id', fake_get_reservation_by_id)
    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'delete_reservation', fake_delete_reservation)

    result = asyncio.run(
        inspect.unwrap(meeting_rooms.cancel_reservation)(
            reservation_id=10,
            db=object(),
            user=SimpleNamespace(id=100, roles=['gcs']),
        )
    )

    assert result.message == 'Deleted'
    assert deleted['called'] is True


def test_cancel_reservation_allows_admin(monkeypatch):
    deleted: dict[str, bool] = {'called': False}

    reservation_obj = SimpleNamespace(id=12, reserved_by_user_id=201)

    async def fake_get_reservation_by_id(_db, reservation_id):
        return reservation_obj

    async def fake_delete_reservation(_db, reservation):
        assert reservation is reservation_obj
        deleted['called'] = True

    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'get_reservation_by_id', fake_get_reservation_by_id)
    monkeypatch.setattr(meeting_rooms.crud_meeting_rooms, 'delete_reservation', fake_delete_reservation)

    result = asyncio.run(
        inspect.unwrap(meeting_rooms.cancel_reservation)(
            reservation_id=12,
            db=object(),
            user=SimpleNamespace(id=300, roles=['admin']),
        )
    )

    assert result.message == 'Deleted'
    assert deleted['called'] is True
