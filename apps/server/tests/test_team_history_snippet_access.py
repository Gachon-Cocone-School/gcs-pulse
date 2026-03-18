"""
팀 이력 기반 스니펫 접근 제어 테스트.

can_read_snippet 이 UserTeamHistory 를 기반으로
스니펫 작성 당시 같은 팀이었는지를 판단하는지 검증.
"""
import asyncio
import inspect
from datetime import date, datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.routers import snippet_access
from app import crud


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(path: str = "/daily-snippets/1", method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {},
        }
    )


class _MockResult:
    """db.execute() 결과를 시뮬레이션."""

    def __init__(self, has_row: bool):
        self._has_row = has_row

    def first(self):
        return (1,) if self._has_row else None


class _MockDB:
    """UserTeamHistory 쿼리 결과를 제어하는 mock DB."""

    def __init__(self, has_overlap: bool):
        self._has_overlap = has_overlap

    async def execute(self, stmt):
        return _MockResult(self._has_overlap)


# ---------------------------------------------------------------------------
# can_read_snippet 단위 테스트
# ---------------------------------------------------------------------------

def test_can_read_snippet_professor_always_true():
    """교수 역할은 이력 조회 없이 항상 True."""
    viewer = SimpleNamespace(id=1, roles=["교수"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=False)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 1), db)
    )
    assert result is True


def test_can_read_snippet_admin_always_true():
    """admin 역할도 항상 True."""
    viewer = SimpleNamespace(id=1, roles=["admin"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=False)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 1), db)
    )
    assert result is True


def test_can_read_snippet_own_snippet_always_true():
    """본인 스니펫은 이력 조회 없이 True."""
    viewer = SimpleNamespace(id=5, roles=["gcs"])
    owner = SimpleNamespace(id=5)
    db = _MockDB(has_overlap=False)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 1), db)
    )
    assert result is True


def test_can_read_snippet_same_team_at_snippet_date_returns_true():
    """스니펫 작성 당시 같은 팀이었으면 True."""
    viewer = SimpleNamespace(id=1, roles=["gcs"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=True)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 15), db)
    )
    assert result is True


def test_can_read_snippet_different_team_at_snippet_date_returns_false():
    """스니펫 작성 당시 다른 팀이었으면 False."""
    viewer = SimpleNamespace(id=1, roles=["gcs"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=False)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 15), db)
    )
    assert result is False


def test_can_read_snippet_no_role_returns_false():
    """접근 역할 없으면 무조건 False."""
    viewer = SimpleNamespace(id=1, roles=["가천대학교"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=True)

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer, owner, date(2026, 1, 15), db)
    )
    assert result is False


# ---------------------------------------------------------------------------
# ensure_snippet_readable_or_403 테스트
# ---------------------------------------------------------------------------

def test_ensure_readable_raises_403_when_no_overlap():
    from app.routers import snippet_flow_helpers as _flow

    viewer = SimpleNamespace(id=1, roles=["gcs"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=False)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            _flow.ensure_snippet_readable_or_403(
                viewer, owner, date(2026, 1, 15), db,
                can_read_snippet=snippet_access.can_read_snippet,
            )
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Access denied"


def test_ensure_readable_passes_when_overlap():
    from app.routers import snippet_flow_helpers as _flow

    viewer = SimpleNamespace(id=1, roles=["gcs"])
    owner = SimpleNamespace(id=2)
    db = _MockDB(has_overlap=True)

    # Should not raise
    asyncio.run(
        _flow.ensure_snippet_readable_or_403(
            viewer, owner, date(2026, 1, 15), db,
            can_read_snippet=snippet_access.can_read_snippet,
        )
    )


# ---------------------------------------------------------------------------
# 팀 이탈 시나리오: 팀1에서 작성한 스니펫은 팀1 전 팀원도 볼 수 있어야 함
# (이 시나리오는 DB 레벨 쿼리에 의존하므로 Mock 으로 표현)
# ---------------------------------------------------------------------------

def test_ex_teammate_can_read_snippet_written_during_shared_period():
    """
    A 와 B 가 팀1에서 2026-01-01 ~ 2026-01-31 함께 근무.
    A 가 2026-01-15 에 스니펫 작성.
    B 가 팀1을 이탈한 후에도 해당 스니펫을 볼 수 있어야 함.
    (DB가 overlap=True 를 반환하면 True)
    """
    viewer_b = SimpleNamespace(id=2, roles=["gcs"])
    owner_a = SimpleNamespace(id=1)
    snippet_date = date(2026, 1, 15)
    db = _MockDB(has_overlap=True)  # 당시 같은 팀이었음을 나타냄

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer_b, owner_a, snippet_date, db)
    )
    assert result is True


def test_new_team_cannot_read_snippet_from_before_join():
    """
    A 가 팀1에 있다가 팀2로 이동.
    팀2 멤버 C 는 A 의 팀1 시절 스니펫을 볼 수 없어야 함.
    (DB가 overlap=False 를 반환)
    """
    viewer_c = SimpleNamespace(id=3, roles=["gcs"])
    owner_a = SimpleNamespace(id=1)
    snippet_date = date(2026, 1, 15)  # A 가 팀1 시절에 작성한 날짜
    db = _MockDB(has_overlap=False)  # 팀2 멤버이므로 팀1 시절과 겹치지 않음

    result = asyncio.run(
        snippet_access.can_read_snippet(viewer_c, owner_a, snippet_date, db)
    )
    assert result is False


# ---------------------------------------------------------------------------
# teams.py 엔드포인트: 이력 기록 동작 검증
# ---------------------------------------------------------------------------

def test_join_team_records_history(monkeypatch):
    """join_team 엔드포인트가 record_team_join 을 호출하는지 검증."""
    from app.routers import teams as teams_router

    recorded_joins = []

    viewer = SimpleNamespace(id=10, team_id=None, roles=["gcs"])
    team = SimpleNamespace(id=5, name="팀A", invite_code="ABCD1234", league_type="none")

    async def fake_get_active_user(request):
        return viewer

    async def fake_get_team_by_invite_code(db, code):
        return team

    async def fake_commit(db=None):
        pass

    class FakeDB:
        async def commit(self):
            pass

        async def rollback(self):
            pass

        async def refresh(self, obj):
            pass

    async def fake_get_team_with_members(db, team_id):
        return team

    async def fake_record_team_join(db, user_id, team_id, joined_at):
        recorded_joins.append((user_id, team_id))

    from app import schemas as app_schemas

    monkeypatch.setattr(crud, "get_team_by_invite_code", fake_get_team_by_invite_code)
    monkeypatch.setattr(crud, "get_team_with_members", fake_get_team_with_members)
    monkeypatch.setattr(crud, "record_team_join", fake_record_team_join)
    monkeypatch.setattr(app_schemas.TeamResponse, "model_validate", classmethod(lambda cls, obj: obj))

    payload = SimpleNamespace(invite_code="ABCD1234")

    db = FakeDB()
    asyncio.run(
        inspect.unwrap(teams_router.join_team)(payload, request=_make_request(), db=db, user=viewer)
    )

    assert len(recorded_joins) == 1
    assert recorded_joins[0] == (viewer.id, team.id)


def test_leave_team_records_history(monkeypatch):
    """leave_team 엔드포인트가 record_team_leave 를 호출하는지 검증."""
    from app.routers import teams as teams_router

    recorded_leaves = []

    viewer = SimpleNamespace(id=10, team_id=5, roles=["gcs"])
    team = SimpleNamespace(id=5)

    async def fake_get_team_by_id(db, team_id):
        return team

    async def fake_count_team_members(db, team_id):
        return 2  # 팀에 다른 멤버 있음 → 팀 삭제 안 함

    async def fake_record_team_leave(db, user_id, team_id, left_at):
        recorded_leaves.append((user_id, team_id))

    class FakeDB:
        async def commit(self):
            pass

        async def rollback(self):
            pass

        async def refresh(self, obj):
            pass

    monkeypatch.setattr(crud, "get_team_by_id", fake_get_team_by_id)
    monkeypatch.setattr(crud, "count_team_members", fake_count_team_members)
    monkeypatch.setattr(crud, "record_team_leave", fake_record_team_leave)

    db = FakeDB()
    asyncio.run(
        inspect.unwrap(teams_router.leave_team)(request=_make_request(), db=db, user=viewer)
    )

    assert len(recorded_leaves) == 1
    assert recorded_leaves[0] == (viewer.id, 5)
