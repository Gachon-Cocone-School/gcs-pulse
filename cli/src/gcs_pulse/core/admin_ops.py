from __future__ import annotations

from typing import Any

from gcs_pulse.utils.gcs_pulse_backend import BackendClient


def migrate_seed(backend: BackendClient) -> dict[str, Any]:
    return backend.run_script("migrate_and_seed.py")


def grant_achievements(backend: BackendClient, target_date: str | None = None, dry_run: bool = False) -> dict[str, Any]:
    args: list[str] = []
    if target_date:
        args.extend(["--target-date", target_date])
    if dry_run:
        args.append("--dry-run")
    return backend.run_script("run_daily_achievement_grants.py", args)


def db_backup(backend: BackendClient, backup_dir: str | None = None) -> dict[str, Any]:
    args: list[str] = []
    if backup_dir:
        args.extend(["--backup-dir", backup_dir])
    return backend.run_script("db_backup.py", args)


def db_restore(
    backend: BackendClient,
    backup_id: str,
    *,
    backup_dir: str | None = None,
    target_db_url: str | None = None,
    verify_db_url: str | None = None,
    dry_run: bool = False,
    execute: bool = False,
    overwrite_public: bool = False,
    terminate_blocking_sessions: bool = False,
    timeout_seconds: int | None = None,
) -> dict[str, Any]:
    args: list[str] = ["--backup-id", backup_id]
    if backup_dir:
        args.extend(["--backup-dir", backup_dir])
    if target_db_url:
        args.extend(["--target-db-url", target_db_url])
    if verify_db_url:
        args.extend(["--verify-db-url", verify_db_url])
    if dry_run:
        args.append("--dry-run")
    if execute:
        args.append("--execute")
    if overwrite_public:
        args.append("--overwrite-public")
    if terminate_blocking_sessions:
        args.append("--terminate-blocking-sessions")
    if timeout_seconds is not None:
        args.extend(["--timeout-seconds", str(timeout_seconds)])

    return backend.run_script("db_restore.py", args)
