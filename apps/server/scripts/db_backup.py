#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, unquote

# Add server project root to import path (same convention as existing scripts)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings


DEFAULT_BACKUP_DIR = Path(__file__).resolve().parents[1] / "backups" / "db"


def resolve_environment_and_db_url() -> tuple[str, str]:
    environment = settings.ENVIRONMENT
    if environment == "production":
        return environment, settings.DATABASE_URL
    if environment == "test" and settings.TEST_DATABASE_URL:
        return environment, settings.TEST_DATABASE_URL
    return environment, settings.DEV_DATABASE_URL


def to_cli_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + database_url[len("postgresql+asyncpg://") :]
    if database_url.startswith("postgres+asyncpg://"):
        return "postgres://" + database_url[len("postgres+asyncpg://") :]
    return database_url


def validate_postgres_url(database_url: str) -> None:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"postgres", "postgresql"}:
        raise ValueError(
            "db_backup.py는 PostgreSQL URL에서만 동작합니다. "
            f"현재 scheme={parsed.scheme!r}"
        )


def get_db_host_and_name(database_url: str) -> tuple[str, str]:
    parsed = urlparse(database_url)
    db_host = parsed.hostname or ""
    db_name = unquote(parsed.path.lstrip("/"))
    return db_host, db_name


def compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def get_pg_dump_version() -> str:
    proc = subprocess.run(
        ["pg_dump", "--version"],
        capture_output=True,
        text=True,
        check=True,
    )
    return proc.stdout.strip() or proc.stderr.strip()


def run_pg_dump(database_url: str, sql_path: Path) -> None:
    subprocess.run(
        [
            "pg_dump",
            "--dbname",
            database_url,
            "--format=plain",
            "--schema=public",
            "--no-owner",
            "--no-privileges",
            "--file",
            str(sql_path),
        ],
        check=True,
    )


def append_index(index_path: Path, row: dict) -> None:
    with index_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PostgreSQL SQL dump 백업 생성 및 메타데이터 기록"
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"백업 저장 경로 (default: {DEFAULT_BACKUP_DIR})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    backup_dir = args.backup_dir.resolve()
    backup_dir.mkdir(parents=True, exist_ok=True)

    environment, raw_db_url = resolve_environment_and_db_url()
    cli_db_url = to_cli_database_url(raw_db_url)
    validate_postgres_url(cli_db_url)

    now_utc = datetime.now(timezone.utc)
    backup_id = f"{now_utc.strftime('%Y%m%dT%H%M%SZ')}-{environment}"
    sql_filename = f"{backup_id}.sql"
    meta_filename = f"{backup_id}.meta.json"

    sql_path = backup_dir / sql_filename
    meta_path = backup_dir / meta_filename
    index_path = backup_dir / "index.jsonl"

    try:
        run_pg_dump(cli_db_url, sql_path)
        size_bytes = sql_path.stat().st_size
        sha256 = compute_sha256(sql_path)
        db_host, db_name = get_db_host_and_name(cli_db_url)
        pg_dump_version = get_pg_dump_version()
    except FileNotFoundError as exc:
        print(f"실패: 필수 도구를 찾을 수 없습니다: {exc}")
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"실패: pg_dump 실행 오류 (exit={exc.returncode})")
        return 2
    except Exception as exc:
        print(f"실패: 백업 생성 중 예외 발생: {exc}")
        return 2

    metadata = {
        "backup_id": backup_id,
        "created_at_utc": now_utc.isoformat().replace("+00:00", "Z"),
        "environment": environment,
        "sql_file": sql_filename,
        "size_bytes": size_bytes,
        "sha256": sha256,
        "db_host": db_host,
        "db_name": db_name,
        "pg_dump_version": pg_dump_version,
    }

    try:
        meta_path.write_text(
            json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        append_index(index_path, metadata)
    except Exception as exc:
        print(f"실패: 메타데이터 기록 중 예외 발생: {exc}")
        return 2

    print("✅ DB 백업 완료")
    print(f"backup_id={backup_id}")
    print(f"sql={sql_path}")
    print(f"meta={meta_path}")
    print(f"index={index_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
