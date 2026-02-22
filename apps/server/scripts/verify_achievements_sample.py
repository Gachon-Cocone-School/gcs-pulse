#!/usr/bin/env python3
"""업적 샘플 데이터 시드 + 응답 검증 스크립트.

기본 동작:
- 격리된 SQLite 테스트 DB 생성
- 필수 약관/유저/업적 정의/업적 지급 이벤트 시드
- GET /achievements/me, GET /achievements/recent 호출
- 요구사항 기반 검증 수행 후 결과 출력

사용 예시:
  source venv/bin/activate
  python scripts/verify_achievements_sample.py
  python scripts/verify_achievements_sample.py --keep-db
  python scripts/verify_achievements_sample.py --db-path ./tmp_verify.db
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


# Add server project root to import path (same convention as existing scripts)
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

KST = timezone(timedelta(hours=9))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed and verify achievements APIs")
    parser.add_argument(
        "--db-path",
        type=str,
        default="",
        help="테스트 DB 파일 경로(기본: scripts 실행 시점 기준 자동 생성)",
    )
    parser.add_argument(
        "--keep-db",
        action="store_true",
        help="검증 후 DB 파일을 삭제하지 않고 유지",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="/achievements/recent 조회 limit (기본 10)",
    )
    return parser.parse_args()


def configure_env(db_path: Path) -> None:
    os.environ["ENVIRONMENT"] = "test"
    os.environ["TEST_AUTH_BYPASS_ENABLED"] = "true"
    os.environ["AUTH_SUCCESS_URL"] = "http://localhost:3000"
    os.environ["ALLOWED_HOSTS"] = '["localhost","127.0.0.1","testserver"]'
    os.environ["TEST_DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"


@dataclass
class SeedContext:
    now: datetime
    run_id: str
    public_code: str
    private_code: str


async def setup_schema_and_required_term(
    engine: Any,
    Base: Any,
    AsyncSessionLocal: Any,
    Term: Any,
    run_id: str,
) -> None:
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        db.add(
            Term(
                type="privacy",
                version=f"verify-{run_id}",
                content="verification required term",
                is_required=True,
                is_active=True,
            )
        )
        await db.commit()


async def grant_required_terms_to_all_users(
    AsyncSessionLocal: Any,
    User: Any,
    Term: Any,
    Consent: Any,
) -> None:
    from sqlalchemy import select

    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User))).scalars().all()
        terms = (
            await db.execute(select(Term).filter(Term.is_active == True, Term.is_required == True))
        ).scalars().all()
        existing_pairs = {
            (c.user_id, c.term_id)
            for c in (await db.execute(select(Consent))).scalars().all()
        }

        for user in users:
            for term in terms:
                if (user.id, term.id) not in existing_pairs:
                    db.add(Consent(user_id=user.id, term_id=term.id))

        await db.commit()


async def seed_achievement_data(
    AsyncSessionLocal: Any,
    crud: Any,
    AchievementDefinition: Any,
    AchievementGrant: Any,
    current_user_sub: str,
    ctx: SeedContext,
) -> dict[str, Any]:
    async with AsyncSessionLocal() as db:
        current_user = await crud.get_user_by_sub(db, current_user_sub)
        if not current_user:
            raise RuntimeError("Current user not found after auth callback")

        another_user = await crud.create_or_update_user(
            db,
            {
                "sub": f"verify-another-{ctx.run_id}",
                "email": f"verify-another-{ctx.run_id}@example.com",
                "name": "샘플 다른유저",
                "picture": "",
                "email_verified": True,
            },
        )

        public_def = AchievementDefinition(
            code=ctx.public_code,
            name="연속 기록 달성",
            description="연속 학습 기록을 달성했습니다.",
            badge_image_url="https://example.com/badges/streak.png",
            is_public_announceable=True,
        )
        private_def = AchievementDefinition(
            code=ctx.private_code,
            name="개인 숨김 업적",
            description="개인 확인 전용 업적입니다.",
            badge_image_url="https://example.com/badges/private.png",
            is_public_announceable=False,
        )
        db.add_all([public_def, private_def])
        await db.flush()

        now = ctx.now
        db.add_all(
            [
                # 포함: 공개 업적(현재 사용자)
                AchievementGrant(
                    user_id=current_user.id,
                    achievement_definition_id=public_def.id,
                    granted_at=now - timedelta(hours=2),
                    publish_start_at=now - timedelta(days=1),
                    publish_end_at=now + timedelta(days=7),
                    external_grant_id=f"verify-g1-{ctx.run_id}",
                ),
                # 포함: 동일 공개 업적 중복 지급(현재 사용자)
                AchievementGrant(
                    user_id=current_user.id,
                    achievement_definition_id=public_def.id,
                    granted_at=now - timedelta(hours=1),
                    publish_start_at=now - timedelta(days=1),
                    publish_end_at=now + timedelta(days=7),
                    external_grant_id=f"verify-g2-{ctx.run_id}",
                ),
                # recent 제외: 비공개 업적
                AchievementGrant(
                    user_id=current_user.id,
                    achievement_definition_id=private_def.id,
                    granted_at=now - timedelta(minutes=50),
                    publish_start_at=now - timedelta(days=1),
                    publish_end_at=now + timedelta(days=7),
                    external_grant_id=f"verify-g3-{ctx.run_id}",
                ),
                # 포함: 공개 업적(타 사용자)
                AchievementGrant(
                    user_id=another_user.id,
                    achievement_definition_id=public_def.id,
                    granted_at=now - timedelta(minutes=30),
                    publish_start_at=now - timedelta(days=1),
                    publish_end_at=now + timedelta(days=7),
                    external_grant_id=f"verify-g4-{ctx.run_id}",
                ),
                # recent 제외: 게시 기간 만료
                AchievementGrant(
                    user_id=another_user.id,
                    achievement_definition_id=public_def.id,
                    granted_at=now - timedelta(hours=3),
                    publish_start_at=now - timedelta(days=2),
                    publish_end_at=now - timedelta(minutes=10),
                    external_grant_id=f"verify-g5-{ctx.run_id}",
                ),
                # recent 제외: 게시 시작 전
                AchievementGrant(
                    user_id=another_user.id,
                    achievement_definition_id=public_def.id,
                    granted_at=now - timedelta(minutes=10),
                    publish_start_at=now + timedelta(hours=1),
                    publish_end_at=now + timedelta(days=1),
                    external_grant_id=f"verify-g6-{ctx.run_id}",
                ),
            ]
        )
        await db.commit()

        return {
            "test_now": now.isoformat(),
            "current_user_id": current_user.id,
            "another_user_id": another_user.id,
            "public_definition_id": public_def.id,
            "private_definition_id": private_def.id,
        }


def verify_me_response(payload: dict[str, Any], public_code: str, private_code: str) -> None:
    items = payload.get("items", [])
    by_code = {item.get("code"): item for item in items}

    assert payload.get("total") == 2, f"/achievements/me total expected 2, got {payload.get('total')}"
    assert public_code in by_code, f"public achievement missing in /achievements/me: {public_code}"
    assert private_code in by_code, f"private achievement missing in /achievements/me: {private_code}"

    assert by_code[public_code].get("grant_count") == 2, (
        f"public grant_count expected 2, got {by_code[public_code].get('grant_count')}"
    )
    assert by_code[private_code].get("grant_count") == 1, (
        f"private grant_count expected 1, got {by_code[private_code].get('grant_count')}"
    )


def verify_recent_response(payload: dict[str, Any], public_code: str, private_code: str) -> None:
    items = payload.get("items", [])

    # 기대값: 공개 + 게시윈도우 유효 이벤트 3개
    assert payload.get("total") == 3, f"/achievements/recent total expected 3, got {payload.get('total')}"
    assert len(items) == 3, f"/achievements/recent items length expected 3, got {len(items)}"

    codes = [item.get("achievement_code") for item in items]
    assert all(code == public_code for code in codes), f"recent contains non-public code(s): {codes}"
    assert private_code not in codes, "private achievement leaked into /achievements/recent"

    # 최신순 정렬(granted_at DESC, id DESC) 확인
    def dt(v: str) -> datetime:
        return datetime.fromisoformat(v)

    for prev, curr in zip(items, items[1:]):
        prev_dt = dt(prev["granted_at"])
        curr_dt = dt(curr["granted_at"])
        assert prev_dt >= curr_dt, "recent grants are not sorted by granted_at desc"


def cleanup_sqlite_files(db_path: Path) -> None:
    for suffix in ("", "-wal", "-shm"):
        target = Path(str(db_path) + suffix)
        if target.exists():
            target.unlink()


def main() -> int:
    args = parse_args()

    run_id = datetime.now(KST).strftime("%Y%m%d%H%M%S")
    db_path = Path(args.db_path).resolve() if args.db_path else Path(f"./achievement_verify_{run_id}.db").resolve()

    configure_env(db_path)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.database import engine, AsyncSessionLocal, Base
    from app import crud
    from app.models import Term, User, Consent, AchievementDefinition, AchievementGrant

    now = datetime.now(KST).replace(microsecond=0)
    ctx = SeedContext(
        now=now,
        run_id=run_id,
        public_code=f"verify-public-{run_id}",
        private_code=f"verify-private-{run_id}",
    )

    try:
        asyncio.run(setup_schema_and_required_term(engine, Base, AsyncSessionLocal, Term, run_id))

        with TestClient(app, base_url="http://localhost") as client:
            auth_resp = client.get("/auth/google/callback", follow_redirects=False)
            if auth_resp.status_code not in (302, 307):
                raise RuntimeError(f"Auth callback failed: {auth_resp.status_code} {auth_resp.text}")

            me_resp = client.get("/auth/me")
            me_json = me_resp.json()
            if not me_json.get("authenticated"):
                raise RuntimeError(f"Auth/me not authenticated: {me_resp.status_code} {me_resp.text}")

            seed_info = asyncio.run(
                seed_achievement_data(
                    AsyncSessionLocal,
                    crud,
                    AchievementDefinition,
                    AchievementGrant,
                    me_json["user"]["sub"],
                    ctx,
                )
            )

            asyncio.run(grant_required_terms_to_all_users(AsyncSessionLocal, User, Term, Consent))

            headers = {"x-test-now": seed_info["test_now"]}
            my_ach_resp = client.get("/achievements/me", headers=headers)
            recent_resp = client.get(f"/achievements/recent?limit={args.limit}", headers=headers)

            assert my_ach_resp.status_code == 200, (
                f"/achievements/me expected 200, got {my_ach_resp.status_code}: {my_ach_resp.text}"
            )
            assert recent_resp.status_code == 200, (
                f"/achievements/recent expected 200, got {recent_resp.status_code}: {recent_resp.text}"
            )

            my_payload = my_ach_resp.json()
            recent_payload = recent_resp.json()

            verify_me_response(my_payload, ctx.public_code, ctx.private_code)
            verify_recent_response(recent_payload, ctx.public_code, ctx.private_code)

            print("✅ Achievement API verification passed")
            print(
                json.dumps(
                    {
                        "db_file": str(db_path),
                        "seed_info": seed_info,
                        "responses": {
                            "/achievements/me": my_payload,
                            "/achievements/recent": recent_payload,
                        },
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )

        asyncio.run(engine.dispose())
        return 0

    except Exception as exc:
        print(f"❌ Achievement API verification failed: {exc}")
        return 1

    finally:
        if not args.keep_db:
            cleanup_sqlite_files(db_path)


if __name__ == "__main__":
    raise SystemExit(main())
