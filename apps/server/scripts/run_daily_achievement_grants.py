#!/usr/bin/env python3

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime

# Add server project root to import path (same convention as existing scripts)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.achievement_granting import grant_daily_achievements, resolve_default_target_date
from app.database import AsyncSessionLocal


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run daily achievement granting job")
    parser.add_argument(
        "--target-date",
        type=str,
        default="",
        help="Target business date in YYYY-MM-DD (default: current_business_date(now)-1day)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate only without DB write",
    )
    return parser.parse_args()


async def run_job(target_date_raw: str, dry_run: bool) -> int:
    target_date = None
    if target_date_raw:
        try:
            target_date = datetime.strptime(target_date_raw, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid --target-date format: {target_date_raw} (expected YYYY-MM-DD)")
            return 2

    resolved_target_date = target_date or resolve_default_target_date()

    async with AsyncSessionLocal() as db:
        summary = await grant_daily_achievements(
            db,
            target_date=resolved_target_date,
            dry_run=dry_run,
        )

    print("✅ Daily achievement granting completed")
    print(json.dumps(summary, ensure_ascii=False, default=str, indent=2))
    return 0


def main() -> int:
    args = parse_args()
    return asyncio.run(run_job(args.target_date, args.dry_run))


if __name__ == "__main__":
    raise SystemExit(main())
