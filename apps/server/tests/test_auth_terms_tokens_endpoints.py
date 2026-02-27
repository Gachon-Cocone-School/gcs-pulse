import asyncio
from datetime import datetime, timezone
import inspect
import json
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app import crud, schemas
from app.routers import auth, terms, tokens


def _make_request(
    path: str,
    method: str,
    headers: dict[str, str] | None = None,
    query_string: bytes = b"",
    session: dict | None = None,
) -> Request:
    encoded_headers = [
        (key.lower().encode("utf-8"), value.encode("utf-8"))
        for key, value in (headers or {}).items()
    ]

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": encoded_headers,
        "query_string": query_string,
        "session": session or {},
    }
    return Request(scope, receive=receive)


def test_auth_google_login_missing_client_returns_500(monkeypatch):
    request = _make_request(path="/auth/google/login", method="GET")

    monkeypatch.setattr(Request, "url_for", lambda self, name: "http://test/auth/google/callback")
    monkeypatch.setattr(auth.oauth, "create_client", lambda _name: None)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(inspect.unwrap(auth.login)(request=request))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "OAuth client not configured"


def test_auth_google_callback_test_bypass_sets_session_and_csrf(monkeypatch):
    request = _make_request(
        path="/auth/google/callback",
        method="GET",
        query_string=b"test_email=bypass%40example.com&test_name=Bypass+User",
        session={"csrf_token": "old-token"},
    )

    captured: dict[str, object] = {}

    async def fake_create_or_update_user(db, user_info):
        captured["user_info"] = user_info

    monkeypatch.setattr(auth.settings, "ENVIRONMENT", "test", raising=False)
    monkeypatch.setattr(auth.settings, "TEST_AUTH_BYPASS_ENABLED", True, raising=False)
    monkeypatch.setattr(auth.settings, "AUTH_SUCCESS_URL", "http://localhost:3000/success", raising=False)
    monkeypatch.setattr(crud, "create_or_update_user", fake_create_or_update_user)
    monkeypatch.setattr(auth, "ensure_csrf_token", lambda req: req.session.setdefault("csrf_token", "new-token"))

    response = asyncio.run(inspect.unwrap(auth.auth_callback)(request=request, db=object()))

    assert response.status_code in (302, 307)
    assert response.headers.get("location") == "http://localhost:3000/success"
    assert request.session["user"]["email"] == "bypass@example.com"
    assert request.session["user"]["name"] == "Bypass User"
    assert request.session["csrf_token"] == "new-token"
    assert captured["user_info"] == {
        "email": "bypass@example.com",
        "name": "Bypass User",
        "picture": "",
        "email_verified": True,
    }


def test_auth_csrf_returns_token(monkeypatch):
    request = _make_request(path="/auth/csrf", method="GET", session={})

    monkeypatch.setattr(auth, "ensure_csrf_token", lambda req: req.session.setdefault("csrf_token", "csrf-123"))

    result = asyncio.run(inspect.unwrap(auth.get_csrf_token)(request=request))

    assert result == {"csrf_token": "csrf-123"}


def test_auth_logout_clears_session():
    request = _make_request(
        path="/auth/logout",
        method="POST",
        session={
            "user": {"email": "user@example.com"},
            "csrf_token": "csrf-abc",
        },
    )

    response = asyncio.run(inspect.unwrap(auth.logout)(request=request))

    assert response.status_code == 200
    assert request.session == {}


def test_auth_me_unauthenticated_returns_401_json_response():
    request = _make_request(path="/auth/me", method="GET", session={})

    response = asyncio.run(inspect.unwrap(auth.me)(request=request, db=object()))

    assert response.status_code == 401
    assert json.loads(response.body.decode("utf-8")) == {
        "authenticated": False,
        "user": None,
    }


def test_auth_me_success_returns_authenticated_payload(monkeypatch):
    request = _make_request(
        path="/auth/me",
        method="GET",
        session={"user": {"email": "member@example.com"}},
    )

    db_user = SimpleNamespace(
        name="Member",
        email="member@example.com",
        picture="https://example.com/avatar.png",
        roles=["user"],
        league_type=schemas.LeagueType.SEMESTER,
        consents=[],
    )

    async def fake_get_user_by_email(db, email):
        assert email == "member@example.com"
        return db_user

    monkeypatch.setattr(crud, "get_user_by_email", fake_get_user_by_email)

    result = asyncio.run(inspect.unwrap(auth.me)(request=request, db=object()))

    assert result["authenticated"] is True
    assert result["user"]["email"] == "member@example.com"
    assert result["user"]["league_type"] == schemas.LeagueType.SEMESTER


def test_terms_get_terms_returns_active_terms(monkeypatch):
    active_terms = [SimpleNamespace(id=1, type="privacy", version="1.0", content="x", is_required=True, is_active=True)]

    async def fake_get_active_terms(db):
        return active_terms

    monkeypatch.setattr(crud, "get_active_terms", fake_get_active_terms)

    result = asyncio.run(inspect.unwrap(terms.get_terms)(request=_make_request("/terms", "GET"), db=object()))

    assert result == active_terms


def test_terms_create_consent_missing_user_email_returns_401():
    payload = schemas.ConsentCreate(term_id=1, agreed=True)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(terms.create_consent)(
                consent=payload,
                request=_make_request("/consents", "POST"),
                user={},
                db=object(),
            )
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Not authenticated"


def test_terms_create_consent_term_not_found_returns_404(monkeypatch):
    payload = schemas.ConsentCreate(term_id=99, agreed=True)

    async def fake_get_user_by_email(db, email):
        return SimpleNamespace(id=10, email=email)

    async def fake_get_term_by_id(db, term_id):
        return None

    monkeypatch.setattr(crud, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(crud, "get_term_by_id", fake_get_term_by_id)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(terms.create_consent)(
                consent=payload,
                request=_make_request("/consents", "POST"),
                user={"email": "member@example.com"},
                db=object(),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Term not found"


def test_terms_create_consent_existing_returns_already_recorded(monkeypatch):
    payload = schemas.ConsentCreate(term_id=7, agreed=True)

    async def fake_get_user_by_email(db, email):
        return SimpleNamespace(id=11, email=email)

    async def fake_get_term_by_id(db, term_id):
        return SimpleNamespace(id=term_id)

    async def fake_get_consent(db, user_id, term_id):
        return SimpleNamespace(user_id=user_id, term_id=term_id)

    monkeypatch.setattr(crud, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(crud, "get_term_by_id", fake_get_term_by_id)
    monkeypatch.setattr(crud, "get_consent", fake_get_consent)

    response = asyncio.run(
        inspect.unwrap(terms.create_consent)(
            consent=payload,
            request=_make_request("/consents", "POST"),
            user={"email": "member@example.com"},
            db=object(),
        )
    )

    assert response.status_code == 200
    assert json.loads(response.body.decode("utf-8")) == {"message": "Consent already recorded"}


def test_terms_create_consent_new_records_consent(monkeypatch):
    payload = schemas.ConsentCreate(term_id=8, agreed=True)
    captured: dict[str, int] = {}

    async def fake_get_user_by_email(db, email):
        return SimpleNamespace(id=12, email=email)

    async def fake_get_term_by_id(db, term_id):
        return SimpleNamespace(id=term_id)

    async def fake_get_consent(db, user_id, term_id):
        return None

    async def fake_create_consent(db, user_id, term_id):
        captured["user_id"] = user_id
        captured["term_id"] = term_id
        return SimpleNamespace(user_id=user_id, term_id=term_id)

    monkeypatch.setattr(crud, "get_user_by_email", fake_get_user_by_email)
    monkeypatch.setattr(crud, "get_term_by_id", fake_get_term_by_id)
    monkeypatch.setattr(crud, "get_consent", fake_get_consent)
    monkeypatch.setattr(crud, "create_consent", fake_create_consent)

    response = asyncio.run(
        inspect.unwrap(terms.create_consent)(
            consent=payload,
            request=_make_request("/consents", "POST"),
            user={"email": "member@example.com"},
            db=object(),
        )
    )

    assert response.status_code == 200
    assert captured == {"user_id": 12, "term_id": 8}
    assert json.loads(response.body.decode("utf-8")) == {"message": "Consent recorded"}


def test_tokens_list_returns_user_tokens(monkeypatch):
    user = SimpleNamespace(id=3)
    db_tokens = [
        SimpleNamespace(
            id=100,
            description="token A",
            created_at=datetime(2026, 2, 27, 9, 0, tzinfo=timezone.utc),
            last_used_at=None,
        )
    ]

    async def fake_list_api_tokens(db, user_id):
        assert user_id == 3
        return db_tokens

    monkeypatch.setattr(crud, "list_api_tokens", fake_list_api_tokens)

    result = asyncio.run(
        inspect.unwrap(tokens.list_tokens)(
            request=_make_request(path="/auth/tokens", method="GET"),
            db=object(),
            user=user,
        )
    )

    assert result == db_tokens


def test_tokens_create_sets_raw_token_and_forwards_idempotency(monkeypatch):
    user = SimpleNamespace(id=7)
    payload = schemas.ApiTokenCreate(description="integration token")
    captured: dict[str, object] = {}

    async def fake_create_api_token(db, user_id, description, idempotency_key):
        captured["user_id"] = user_id
        captured["description"] = description
        captured["idempotency_key"] = idempotency_key
        return (
            SimpleNamespace(
                id=501,
                description=description,
                created_at=datetime(2026, 2, 27, 10, 0, tzinfo=timezone.utc),
                last_used_at=None,
            ),
            "raw-token-value",
        )

    monkeypatch.setattr(crud, "create_api_token", fake_create_api_token)

    response = asyncio.run(
        inspect.unwrap(tokens.create_token)(
            payload=payload,
            request=_make_request(path="/auth/tokens", method="POST"),
            db=object(),
            user=user,
            idempotency_key="idem-1",
        )
    )

    assert captured == {
        "user_id": 7,
        "description": "integration token",
        "idempotency_key": "idem-1",
    }
    assert response.id == 501
    assert response.token == "raw-token-value"


def test_tokens_delete_missing_token_returns_404(monkeypatch):
    async def fake_delete_api_token(db, token_id, user_id):
        return False

    monkeypatch.setattr(crud, "delete_api_token", fake_delete_api_token)

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(
            inspect.unwrap(tokens.delete_token)(
                token_id=123,
                request=_make_request(path="/auth/tokens/123", method="DELETE"),
                db=object(),
                user=SimpleNamespace(id=9),
            )
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Token not found"


def test_tokens_delete_success_returns_message(monkeypatch):
    async def fake_delete_api_token(db, token_id, user_id):
        return True

    monkeypatch.setattr(crud, "delete_api_token", fake_delete_api_token)

    result = asyncio.run(
        inspect.unwrap(tokens.delete_token)(
            token_id=123,
            request=_make_request(path="/auth/tokens/123", method="DELETE"),
            db=object(),
            user=SimpleNamespace(id=9),
        )
    )

    assert result == {"message": "Token revoked"}
