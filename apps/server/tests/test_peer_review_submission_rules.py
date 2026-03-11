import asyncio
import inspect
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any, cast

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.routers import peer_reviews as _peer_reviews

peer_reviews = cast(Any, _peer_reviews)


def _make_request(path: str, method: str = "POST") -> Request:
    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "query_string": b"",
            "session": {"user": {"email": "student@example.com"}},
        },
        receive=receive,
    )


def _entry(evaluatee_user_id: int, contribution_percent: int, fit_yes_no: bool):
    return SimpleNamespace(
        evaluatee_user_id=evaluatee_user_id,
        contribution_percent=contribution_percent,
        fit_yes_no=fit_yes_no,
    )


def _patch_form_context(monkeypatch, *, is_open: bool = True, team_user_ids=None):
    if team_user_ids is None:
        team_user_ids = [101, 102]

    async def fake_get_user_by_email_basic(_db, _email):
        return SimpleNamespace(id=101, email="student@example.com", name="학생", picture=None)

    async def fake_get_session_by_access_token(_db, _token):
        return SimpleNamespace(
            id=22,
            is_open=is_open,
            professor_user_id=7,
            updated_at=datetime.now(timezone.utc),
        )

    async def fake_get_member(_db, *, session_id, student_user_id):
        assert session_id == 22
        assert student_user_id == 101
        return SimpleNamespace(session_id=22, student_user_id=101, team_label="1조")

    async def fake_list_team_member_users(_db, *, session_id, team_label):
        assert session_id == 22
        assert team_label == "1조"
        return [
            SimpleNamespace(id=user_id, name=f"학생{user_id}", email=f"u{user_id}@example.com", picture=None)
            for user_id in team_user_ids
        ]

    monkeypatch.setattr(peer_reviews.crud, "get_user_by_email_basic", fake_get_user_by_email_basic)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_session_by_access_token", fake_get_session_by_access_token)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "get_member", fake_get_member)
    monkeypatch.setattr(peer_reviews.peer_review_crud, "list_team_member_users", fake_list_team_member_users)


def test_submit_peer_review_form_rejects_closed_session(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, is_open=False)

    payload = SimpleNamespace(entries=[_entry(101, 100, True)])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.submit_peer_review_form)(
                token="token",
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Session is closed"


def test_submit_peer_review_form_rejects_count_mismatch(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, team_user_ids=[101, 102])

    payload = SimpleNamespace(entries=[_entry(101, 100, True)])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.submit_peer_review_form)(
                token="token",
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "All team members must be evaluated exactly once"


def test_submit_peer_review_form_rejects_outside_team_evaluatee(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, team_user_ids=[101, 102])

    payload = SimpleNamespace(entries=[_entry(101, 50, True), _entry(999, 50, False)])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.submit_peer_review_form)(
                token="token",
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Evaluatee must be in same session team"


def test_submit_peer_review_form_rejects_duplicate_evaluatee(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, team_user_ids=[101, 102])

    payload = SimpleNamespace(entries=[_entry(101, 40, True), _entry(101, 60, False)])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.submit_peer_review_form)(
                token="token",
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Duplicate evaluatee in entries"


def test_submit_peer_review_form_rejects_invalid_total(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, team_user_ids=[101, 102])

    payload = SimpleNamespace(entries=[_entry(101, 60, True), _entry(102, 30, True)])

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(peer_reviews.submit_peer_review_form)(
                token="token",
                payload=payload,
                request=request,
                db=object(),
            )
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.detail == "Contribution percent sum must be exactly 100"


def test_submit_peer_review_form_success(monkeypatch):
    request = _make_request("/peer-reviews/forms/token/submit")
    _patch_form_context(monkeypatch, team_user_ids=[101, 102])

    captured: dict[str, object] = {}

    async def fake_upsert_submission_entries(_db, *, session_id, evaluator_user_id, entries):
        captured["session_id"] = session_id
        captured["evaluator_user_id"] = evaluator_user_id
        captured["entries"] = entries

    monkeypatch.setattr(peer_reviews.peer_review_crud, "upsert_submission_entries", fake_upsert_submission_entries)

    payload = SimpleNamespace(entries=[_entry(101, 70, True), _entry(102, 30, False)])

    result = asyncio.run(
        inspect.unwrap(peer_reviews.submit_peer_review_form)(
            token="token",
            payload=payload,
            request=request,
            db=object(),
        )
    )

    assert result["message"] == "Submitted"
    assert captured["session_id"] == 22
    assert captured["evaluator_user_id"] == 101
    assert captured["entries"] == [(101, 70, True), (102, 30, False)]
