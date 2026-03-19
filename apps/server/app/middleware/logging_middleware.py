from __future__ import annotations

import time
import uuid
from typing import MutableMapping, Any

import structlog
from starlette.types import ASGIApp, Message, Receive, Scope, Send

logger = structlog.get_logger()

# 로깅을 건너뛸 경로
_SKIP_PATHS = frozenset(["/favicon.ico", "/health"])


class LoggingMiddleware:
    """순수 ASGI 로깅 미들웨어.

    BaseHTTPMiddleware 대신 raw ASGI를 사용해 SSE/스트리밍 응답 버퍼링 문제를 방지합니다.
    각 요청에 request_id를 부여하고 structlog contextvars로 전파합니다.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path: str = scope.get("path", "")
        if path in _SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        method: str = scope.get("method", "")
        client = scope.get("client")
        client_host = client[0] if client else None
        request_id = str(uuid.uuid4())

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=method,
            path=path,
            client=client_host,
        )

        status_code = 500
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            logger.exception("http_request_error", status_code=500)
            raise
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            log_fn = logger.info if status_code < 500 else logger.error
            log_fn("http_request", status_code=status_code, duration_ms=duration_ms)
            structlog.contextvars.clear_contextvars()
