import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.dependencies import ensure_csrf_token, verify_csrf


def _make_request(
    method: str,
    headers: dict[str, str] | None = None,
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
        "path": "/csrf-test",
        "headers": encoded_headers,
        "query_string": b"",
        "session": session or {},
    }
    return Request(scope, receive=receive)


def test_ensure_csrf_token_creates_token_when_missing():
    request = _make_request(method="GET", session={})

    token = ensure_csrf_token(request)

    assert token
    assert request.session["csrf_token"] == token


def test_ensure_csrf_token_reuses_existing_token():
    request = _make_request(method="GET", session={"csrf_token": "existing-token"})

    token = ensure_csrf_token(request)

    assert token == "existing-token"


def test_verify_csrf_rejects_missing_header_for_unsafe_session_request():
    request = _make_request(method="POST", session={"csrf_token": "expected-token"})

    with pytest.raises(HTTPException) as exc_info:
        verify_csrf(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "CSRF validation failed"


def test_verify_csrf_rejects_mismatched_token_for_unsafe_session_request():
    request = _make_request(
        method="PATCH",
        headers={"x-csrf-token": "wrong-token"},
        session={"csrf_token": "expected-token"},
    )

    with pytest.raises(HTTPException) as exc_info:
        verify_csrf(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "CSRF validation failed"


def test_verify_csrf_allows_matching_token_for_unsafe_session_request():
    request = _make_request(
        method="DELETE",
        headers={"x-csrf-token": "expected-token"},
        session={"csrf_token": "expected-token"},
    )

    verify_csrf(request)


def test_verify_csrf_allows_safe_method_without_token():
    request = _make_request(method="GET", session={})

    verify_csrf(request)


def test_verify_csrf_allows_bearer_request_without_csrf_header():
    request = _make_request(
        method="POST",
        headers={"authorization": "Bearer test-token"},
        session={},
    )

    verify_csrf(request)
