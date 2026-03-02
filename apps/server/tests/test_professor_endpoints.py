import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud
from app.routers import professor


def _make_request(path: str, method: str = "GET") -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {},
        },
        receive=receive,
    )


def _viewer():
    return SimpleNamespace(id=10, roles=["교수"], team_id=99)


def _student(user_id: int):
    return SimpleNamespace(id=user_id, roles=["가천대학교"], team_id=1)


def _prof_user(user_id: int):
    return SimpleNamespace(id=user_id, roles=["교수"], team_id=1)


def test_professor_overview_returns_counts(monkeypatch):
    request = _make_request("/professor/overview")

    async def fake_get_viewer(request_arg, db, include_consents=False):
        assert include_consents is False
        return _viewer()

    async def fake_ensure_latest(db):
        return None

    async def fake_build_counts(db):
        return {
            "high_or_critical_count": 3,
            "high_count": 2,
            "critical_count": 1,
            "medium_count": 4,
            "low_count": 5,
        }

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "ensure_latest_snapshots_for_all_students", fake_ensure_latest)
    monkeypatch.setattr(crud, "build_overview_counts", fake_build_counts)

    result = asyncio.run(
        inspect.unwrap(professor.get_professor_overview)(
            request=request,
            db=object(),
        )
    )

    assert result["critical_count"] == 1
    assert result["high_or_critical_count"] == 3


def test_professor_risk_queue_returns_items(monkeypatch):
    request = _make_request("/professor/risk-queue")
    now = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

    async def fake_get_viewer(request_arg, db, include_consents=False):
        return _viewer()

    async def fake_ensure_latest(db):
        return None

    async def fake_build_queue(db, limit):
        assert limit == 30
        return [
            {
                "user_id": 21,
                "user_name": "학생 A",
                "user_email": "a@example.com",
                "risk_score": 82.1,
                "risk_band": "Critical",
                "evaluated_at": now,
                "confidence": 0.87,
                "reasons": [],
                "tone_policy": None,
            }
        ]

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "ensure_latest_snapshots_for_all_students", fake_ensure_latest)
    monkeypatch.setattr(crud, "build_risk_queue", fake_build_queue)

    result = asyncio.run(
        inspect.unwrap(professor.get_professor_risk_queue)(
            request=request,
            limit=30,
            db=object(),
        )
    )

    assert result["total"] == 1
    assert result["items"][0]["risk_band"] == "Critical"


def test_professor_history_rejects_non_student(monkeypatch):
    request = _make_request("/professor/students/9/risk-history")

    async def fake_get_viewer(request_arg, db, include_consents=False):
        return _viewer()

    async def fake_get_user_by_id(db, user_id):
        return _prof_user(user_id)

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(professor.get_professor_student_risk_history)(
                user_id=9,
                request=request,
                limit=12,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Student not found"


def test_professor_history_returns_payload(monkeypatch):
    request = _make_request("/professor/students/9/risk-history")
    now = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

    async def fake_get_viewer(request_arg, db, include_consents=False):
        return _viewer()

    async def fake_get_user_by_id(db, user_id):
        return _student(user_id)

    async def fake_ensure_latest(db, user_id):
        assert user_id == 9
        return {
            "user_id": 9,
            "evaluated_at": now,
            "l1": 70.0,
            "l2": 60.0,
            "l3": 50.0,
            "risk_score": 64.5,
            "risk_band": "High",
            "daily_subscores": {},
            "weekly_subscores": {},
            "trend_subscores": {},
            "confidence": {
                "score": 0.8,
                "data_coverage": 0.9,
                "signal_agreement": 0.8,
                "history_depth": 0.7,
            },
            "reasons": [],
            "tone_policy": {
                "primary": "질문",
                "secondary": ["제안"],
                "suppressed": ["훈계"],
                "trigger_patterns": [],
                "policy_confidence": 0.8,
            },
            "needs_professor_review": True,
        }

    async def fake_history(db, user_id, limit=12):
        assert user_id == 9
        assert limit == 12
        return [
            {
                "user_id": 9,
                "evaluated_at": now,
                "l1": 70.0,
                "l2": 60.0,
                "l3": 50.0,
                "risk_score": 64.5,
                "risk_band": "High",
                "daily_subscores": {},
                "weekly_subscores": {},
                "trend_subscores": {},
                "confidence": {
                    "score": 0.8,
                    "data_coverage": 0.9,
                    "signal_agreement": 0.8,
                    "history_depth": 0.7,
                },
                "reasons": [],
                "tone_policy": {
                    "primary": "질문",
                    "secondary": ["제안"],
                    "suppressed": ["훈계"],
                    "trigger_patterns": [],
                    "policy_confidence": 0.8,
                },
                "needs_professor_review": True,
            }
        ]

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(crud, "ensure_latest_snapshot_for_user", fake_ensure_latest)
    monkeypatch.setattr(crud, "build_risk_history_payload", fake_history)

    result = asyncio.run(
        inspect.unwrap(professor.get_professor_student_risk_history)(
            user_id=9,
            request=request,
            limit=12,
            db=object(),
        )
    )

    assert result["total"] == 1
    assert result["items"][0]["risk_band"] == "High"


def test_professor_evaluate_returns_snapshot(monkeypatch):
    request = _make_request("/professor/students/9/risk-evaluate", method="POST")
    now = datetime(2026, 3, 2, 9, 0, tzinfo=timezone.utc)

    async def fake_get_viewer(request_arg, db, include_consents=False):
        return _viewer()

    async def fake_get_user_by_id(db, user_id):
        return _student(user_id)

    async def fake_evaluate(db, user_id):
        assert user_id == 9
        return {
            "user_id": 9,
            "evaluated_at": now,
            "l1": 70.0,
            "l2": 60.0,
            "l3": 50.0,
            "risk_score": 64.5,
            "risk_band": "High",
            "daily_subscores": {},
            "weekly_subscores": {},
            "trend_subscores": {},
            "confidence": {
                "score": 0.8,
                "data_coverage": 0.9,
                "signal_agreement": 0.8,
                "history_depth": 0.7,
            },
            "reasons": [],
            "tone_policy": {
                "primary": "질문",
                "secondary": ["제안"],
                "suppressed": ["훈계"],
                "trigger_patterns": [],
                "policy_confidence": 0.8,
            },
            "needs_professor_review": True,
        }

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)
    monkeypatch.setattr(crud, "evaluate_student_and_create_snapshot", fake_evaluate)

    result = asyncio.run(
        inspect.unwrap(professor.evaluate_professor_student_risk)(
            user_id=9,
            request=request,
            db=object(),
        )
    )

    assert result["snapshot"]["risk_band"] == "High"


def test_professor_evaluate_rejects_non_student(monkeypatch):
    request = _make_request("/professor/students/9/risk-evaluate", method="POST")

    async def fake_get_viewer(request_arg, db, include_consents=False):
        return _viewer()

    async def fake_get_user_by_id(db, user_id):
        return _prof_user(user_id)

    monkeypatch.setattr(professor.snippet_utils, "get_viewer_or_401", fake_get_viewer)
    monkeypatch.setattr(crud, "get_user_by_id", fake_get_user_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(professor.evaluate_professor_student_risk)(
                user_id=9,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Student not found"
