from __future__ import annotations

import logging
import sys
from queue import Queue
from typing import Optional

import structlog


def configure_logging(
    environment: str,
    loki_url: Optional[str] = None,
    loki_username: Optional[str] = None,
    loki_password: Optional[str] = None,
) -> None:
    """structlog + stdlib logging 초기화. loki_url 제공 시 Loki 핸들러도 등록."""

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if environment == "development"
        else structlog.processors.JSONRenderer()
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(stdout_handler)
    root_logger.setLevel(logging.INFO)

    # 우리 미들웨어가 요청 로깅을 담당하므로 uvicorn access log 비활성화
    logging.getLogger("uvicorn.access").propagate = False
    # 불필요한 노이즈 줄이기
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    if loki_url:
        _add_loki_handler(root_logger, loki_url, loki_username, loki_password, environment)


def _add_loki_handler(
    root_logger: logging.Logger,
    url: str,
    username: Optional[str],
    password: Optional[str],
    environment: str,
) -> None:
    try:
        import logging_loki  # type: ignore[import]
    except ImportError:
        logging.getLogger(__name__).warning(
            "python-logging-loki 미설치 — Loki 핸들러를 건너뜁니다"
        )
        return

    auth = (username, password) if username and password else None

    handler = logging_loki.LokiQueueHandler(
        Queue(-1),
        url=url,
        tags={"app": "gcs-pulse", "service": "server", "environment": environment},
        auth=auth,
        version="1",
    )
    root_logger.addHandler(handler)
    logging.getLogger(__name__).info("Loki 핸들러 등록 완료", extra={"url": url})
