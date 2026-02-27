import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud
from app.routers import notifications


def _make_request(
    path: str,
    method: str,
    headers: dict[str, str] | None = None,
) -> Request:
    encoded_headers = [
        (key.lower().encode("utf-8"), value.encode("utf-8"))
        for key, value in (headers or {}).items()
    ]

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": encoded_headers,
            "query_string": b"",
            "session": {},
        },
        receive=receive,
    )


def _notification_row(notification_id: int, user_id: int, *, is_read: bool = False):
    return SimpleNamespace(
        id=notification_id,
        user_id=user_id,
        actor_user_id=99,
        actor_user=None,
        type="comment_on_my_snippet",
        daily_snippet_id=10,
        weekly_snippet_id=None,
        comment_id=77,
        is_read=is_read,
        read_at=None,
        created_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
    )


def test_notifications_list_returns_items_with_total(monkeypatch):
    viewer = SimpleNamespace(id=7)
    rows = [_notification_row(1, viewer.id), _notification_row(2, viewer.id, is_read=True)]

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_list_notifications(db, user_id, limit, offset):
        assert user_id == 7
        assert limit == 20
        assert offset == 0
        return rows, 42

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "list_notifications", fake_list_notifications)

    result = asyncio.run(
        inspect.unwrap(notifications.list_notifications)(
            request=_make_request("/notifications", "GET"),
            limit=20,
            offset=0,
            db=object(),
        )
    )

    assert result["items"] == rows
    assert result["total"] == 42
    assert result["limit"] == 20
    assert result["offset"] == 0


def test_notifications_patch_read_returns_404_for_other_user(monkeypatch):
    viewer = SimpleNamespace(id=7)

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_get_notification_by_id_for_user(db, notification_id, user_id):
        assert notification_id == 101
        assert user_id == 7
        return None

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_notification_by_id_for_user", fake_get_notification_by_id_for_user)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(notifications.mark_notification_read)(
                notification_id=101,
                request=_make_request("/notifications/101/read", "PATCH"),
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Notification not found"


def test_notifications_patch_read_marks_single_item(monkeypatch):
    viewer = SimpleNamespace(id=7)
    row = _notification_row(11, viewer.id)

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_get_notification_by_id_for_user(db, notification_id, user_id):
        return row

    async def fake_mark_notification_as_read(db, notification):
        notification.is_read = True
        notification.read_at = datetime(2026, 2, 27, 16, 0, tzinfo=timezone.utc)
        return notification

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_notification_by_id_for_user", fake_get_notification_by_id_for_user)
    monkeypatch.setattr(crud, "mark_notification_as_read", fake_mark_notification_as_read)

    result = asyncio.run(
        inspect.unwrap(notifications.mark_notification_read)(
            notification_id=11,
            request=_make_request("/notifications/11/read", "PATCH"),
            db=object(),
        )
    )

    assert result.id == 11
    assert result.is_read is True


def test_notifications_patch_read_all_returns_updated_count(monkeypatch):
    viewer = SimpleNamespace(id=7)

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_mark_all_notifications_as_read(db, user_id):
        assert user_id == 7
        return 5

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "mark_all_notifications_as_read", fake_mark_all_notifications_as_read)

    result = asyncio.run(
        inspect.unwrap(notifications.mark_all_notifications_read)(
            request=_make_request("/notifications/read-all", "PATCH"),
            db=object(),
        )
    )

    assert result == {"updated_count": 5}


def test_notifications_unread_count_returns_count(monkeypatch):
    viewer = SimpleNamespace(id=7)

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_count_unread_notifications(db, user_id):
        assert user_id == 7
        return 3

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "count_unread_notifications", fake_count_unread_notifications)

    result = asyncio.run(
        inspect.unwrap(notifications.get_unread_notifications_count)(
            request=_make_request("/notifications/unread-count", "GET"),
            db=object(),
        )
    )

    assert result == {"unread_count": 3}


def test_notifications_get_settings_creates_default(monkeypatch):
    viewer = SimpleNamespace(id=7)
    setting = SimpleNamespace(
        user_id=7,
        notify_post_author=True,
        notify_mentions=True,
        notify_participants=True,
        created_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
    )

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_get_or_create_notification_setting(db, user_id):
        assert user_id == 7
        return setting

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_or_create_notification_setting", fake_get_or_create_notification_setting)

    result = asyncio.run(
        inspect.unwrap(notifications.get_notification_settings)(
            request=_make_request("/notifications/settings", "GET"),
            db=object(),
        )
    )

    assert result.user_id == 7
    assert result.notify_mentions is True


def test_notifications_patch_settings_updates_fields(monkeypatch):
    viewer = SimpleNamespace(id=7)
    setting = SimpleNamespace(
        user_id=7,
        notify_post_author=True,
        notify_mentions=True,
        notify_participants=True,
        created_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
        updated_at=datetime(2026, 2, 27, 15, 0, tzinfo=timezone.utc),
    )
    updated = SimpleNamespace(
        user_id=7,
        notify_post_author=False,
        notify_mentions=True,
        notify_participants=False,
        created_at=setting.created_at,
        updated_at=datetime(2026, 2, 27, 16, 0, tzinfo=timezone.utc),
    )

    async def fake_get_viewer(request, db):
        return viewer

    async def fake_get_or_create_notification_setting(db, user_id):
        assert user_id == 7
        return setting

    async def fake_update_notification_setting(
        db,
        saved_setting,
        notify_post_author=None,
        notify_mentions=None,
        notify_participants=None,
    ):
        assert saved_setting is setting
        assert notify_post_author is False
        assert notify_mentions is None
        assert notify_participants is False
        return updated

    monkeypatch.setattr(notifications.snippet_utils, "get_snippet_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_or_create_notification_setting", fake_get_or_create_notification_setting)
    monkeypatch.setattr(crud, "update_notification_setting", fake_update_notification_setting)

    payload = SimpleNamespace(
        notify_post_author=False,
        notify_mentions=None,
        notify_participants=False,
    )

    result = asyncio.run(
        inspect.unwrap(notifications.update_notification_settings)(
            payload=payload,
            request=_make_request("/notifications/settings", "PATCH"),
            db=object(),
        )
    )

    assert result.notify_post_author is False
    assert result.notify_mentions is True
    assert result.notify_participants is False
