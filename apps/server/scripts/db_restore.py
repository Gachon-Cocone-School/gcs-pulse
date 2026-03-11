#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse, urlunparse

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
            "db_restore.py는 PostgreSQL URL에서만 동작합니다. "
            f"현재 scheme={parsed.scheme!r}"
        )


def redact_database_url(database_url: str) -> str:
    parsed = urlparse(database_url)
    if parsed.password is None:
        return database_url
    username = parsed.username or ""
    host = parsed.hostname or ""
    port = f":{parsed.port}" if parsed.port else ""
    userinfo = f"{username}:***"
    netloc = f"{userinfo}@{host}{port}"
    return urlunparse(
        (
            parsed.scheme,
            netloc,
            parsed.path,
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )


def compute_sha256(file_path: Path) -> str:
    digest = hashlib.sha256()
    with file_path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_backup_from_index(index_path: Path, backup_id: str) -> dict | None:
    if not index_path.exists():
        return None

    found = None
    with index_path.open("r", encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if item.get("backup_id") == backup_id:
                found = item
    return found


def load_meta(meta_path: Path) -> dict:
    return json.loads(meta_path.read_text(encoding="utf-8"))


def run_psql_restore(database_url: str, sql_path: Path) -> None:
    subprocess.run(
        [
            "psql",
            "--dbname",
            database_url,
            "--set",
            "ON_ERROR_STOP=1",
            "--single-transaction",
            "--file",
            str(sql_path),
        ],
        check=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="backup_id 기반 PostgreSQL SQL dump 복원"
    )
    parser.add_argument("--backup-id", required=True, help="복원할 backup_id")
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=DEFAULT_BACKUP_DIR,
        help=f"백업 저장 경로 (default: {DEFAULT_BACKUP_DIR})",
    )
    parser.add_argument(
        "--target-db-url",
        default="",
        help="복원 대상 DB URL (미지정 시 ENVIRONMENT 규칙 사용)",
    )
    parser.add_argument(
        "--verify-db-url",
        default="",
        help="선복원 검증용 임시 DB URL",
    )
    parser.add_argument("--dry-run", action="store_true", help="검증만 수행하고 종료")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="실제 대상 DB 복원 수행(미지정 시 대상 DB 복원 금지)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    backup_id = args.backup_id
    backup_dir = args.backup_dir.resolve()
    index_path = backup_dir / "index.jsonl"
    meta_path = backup_dir / f"{backup_id}.meta.json"

    index_row = load_backup_from_index(index_path, backup_id)
    if index_row is None:
        print(f"실패: index.jsonl에서 backup_id={backup_id}를 찾지 못했습니다: {index_path}")
        return 2

    if not meta_path.exists():
        print(f"실패: meta 파일이 없습니다: {meta_path}")
        return 2

    try:
        meta = load_meta(meta_path)
    except Exception as exc:
        print(f"실패: meta 파일 파싱 오류: {exc}")
        return 2

    if meta.get("backup_id") != backup_id:
        print(
            "실패: meta의 backup_id가 요청값과 다릅니다. "
            f"requested={backup_id}, meta={meta.get('backup_id')}"
        )
        return 2

    sql_file = meta.get("sql_file", "")
    sql_path = backup_dir / sql_file
    if not sql_file or not sql_path.exists():
        print(f"실패: SQL dump 파일을 찾을 수 없습니다: {sql_path}")
        return 2

    expected_sha256 = meta.get("sha256", "")
    if not expected_sha256:
        print("실패: meta에 sha256 필드가 없습니다.")
        return 2

    actual_sha256 = compute_sha256(sql_path)
    if actual_sha256 != expected_sha256:
        print("실패: checksum 불일치로 복원을 중단합니다.")
        print(f"expected={expected_sha256}")
        print(f"actual={actual_sha256}")
        return 2

    _, resolved_target_raw_url = resolve_environment_and_db_url()
    target_raw_url = args.target_db_url.strip() or resolved_target_raw_url

    try:
        target_cli_url = to_cli_database_url(target_raw_url)
        validate_postgres_url(target_cli_url)
        verify_cli_url = ""
        if args.verify_db_url.strip():
            verify_cli_url = to_cli_database_url(args.verify_db_url.strip())
            validate_postgres_url(verify_cli_url)
    except ValueError as exc:
        print(f"실패: {exc}")
        return 2

    print("복원 대상 백업 확인 완료")
    print(f"backup_id={backup_id}")
    print(f"sql={sql_path}")
    print(f"checksum={actual_sha256} (검증 통과)")
    print(f"target_db={redact_database_url(target_cli_url)}")
    if verify_cli_url:
        print(f"verify_db={redact_database_url(verify_cli_url)}")

    if args.dry_run:
        print("DRY RUN: 실제 복원은 수행하지 않았습니다.")
        print(
            "실행 예정 명령: "
            f"psql --dbname <target> --set ON_ERROR_STOP=1 --single-transaction --file {sql_path}"
        )
        return 0

    try:
        if verify_cli_url:
            print("검증 DB 선복원 시작...")
            run_psql_restore(verify_cli_url, sql_path)
            print("✅ 검증 DB 복원 성공")

        if args.execute:
            print("대상 DB 복원 시작...")
            run_psql_restore(target_cli_url, sql_path)
            print("✅ 대상 DB 복원 성공")
            return 0

        print("안전장치: --execute 미지정으로 대상 DB 복원을 건너뜁니다.")
        return 0
    except FileNotFoundError as exc:
        print(f"실패: 필수 도구를 찾을 수 없습니다: {exc}")
        return 2
    except subprocess.CalledProcessError as exc:
        print(f"실패: psql 복원 오류 (exit={exc.returncode})")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
