from __future__ import annotations

import logging
import logging.handlers
import sys
from pathlib import Path
from typing import Optional

import structlog


def configure_logging(
    environment: str,
    log_file: Optional[str] = None,
) -> None:
    """structlog + stdlib logging 초기화."""

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

    console_renderer = (
        structlog.dev.ConsoleRenderer(colors=True)
        if environment == "development"
        else structlog.processors.JSONRenderer()
    )
    json_renderer = structlog.processors.JSONRenderer()

    def _make_formatter(renderer) -> structlog.stdlib.ProcessorFormatter:
        return structlog.stdlib.ProcessorFormatter(
            processors=[
                structlog.stdlib.ProcessorFormatter.remove_processors_meta,
                renderer,
            ],
            foreign_pre_chain=shared_processors,
        )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)

    # stdout 핸들러 (개발: 컬러, 프로덕션: JSON)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(_make_formatter(console_renderer))
    root_logger.addHandler(stdout_handler)

    # 파일 핸들러
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_path,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(_make_formatter(json_renderer))
        root_logger.addHandler(file_handler)

    # 우리 미들웨어가 요청 로깅을 담당하므로 uvicorn access log 비활성화
    logging.getLogger("uvicorn.access").propagate = False
    # 불필요한 노이즈 줄이기
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
