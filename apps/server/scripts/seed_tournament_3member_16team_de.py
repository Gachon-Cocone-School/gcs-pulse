"""
3명 × 16팀, 16강 패자부활전(더블 엘리미네이션), allow_self_vote=True 토너먼트 시드 스크립트.

- buriburisuri@gmail.com 을 팀A 1번 멤버로 포함
- 나머지 47명은 tour-test-{n:03d}@example.com 계정으로 자동 생성
- 기존 동일 제목 세션이 있으면 덮어씁니다.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app import crud
from app import crud_tournaments as tournament_crud
from app.database import AsyncSessionLocal
from app.models import TournamentSession
from app.routers.tournaments import _build_matches_payload, _normalize_format_json


PROF_EMAIL = "namjookim@gachon.ac.kr"
SESSION_TITLE = "16강 패자부활전 테스트 (3인팀 × 16팀, 자기팀 투표 가능)"

FORMAT_JSON = {
    "bracket_size": 16,
    "repechage": {"enabled": True},
}

TEAM_NAMES = [f"팀{chr(0x40 + i)}" for i in range(1, 17)]  # 팀A ~ 팀P

SPECIAL_EMAIL = "buriburisuri@gmail.com"
SPECIAL_NAME = "테스트학생"

MEMBERS_PER_TEAM = 3
TOTAL_STUDENTS = len(TEAM_NAMES) * MEMBERS_PER_TEAM  # 48


async def ensure_professor(db):
    professor = await crud.get_user_by_email_basic(db, PROF_EMAIL)
    if professor is None:
        raise RuntimeError(f"Professor account not found: {PROF_EMAIL}")
    return professor


async def ensure_students(db):
    await crud.create_or_update_user(
        db,
        {"email": SPECIAL_EMAIL, "name": SPECIAL_NAME, "picture": "", "email_verified": True},
    )
    special = await crud.get_user_by_email_basic(db, SPECIAL_EMAIL)
    if special is None:
        raise RuntimeError(f"Failed to create special student: {SPECIAL_EMAIL}")
    special.roles = ["가천대학교", "gcs"]

    extras = []
    for i in range(1, TOTAL_STUDENTS):
        email = f"tour-test-{i:03d}@example.com"
        name = f"테스터{i:03d}"
        await crud.create_or_update_user(
            db,
            {"email": email, "name": name, "picture": "", "email_verified": True},
        )
        user = await crud.get_user_by_email_basic(db, email)
        if user is None:
            raise RuntimeError(f"Failed to create student: {email}")
        user.roles = ["가천대학교", "gcs"]
        extras.append(user)

    await db.commit()

    refreshed_special = await crud.get_user_by_email_basic(db, SPECIAL_EMAIL)
    refreshed_extras = []
    for i in range(1, TOTAL_STUDENTS):
        u = await crud.get_user_by_email_basic(db, f"tour-test-{i:03d}@example.com")
        refreshed_extras.append(u)

    return [refreshed_special] + refreshed_extras


async def ensure_session(db, professor):
    existing = await db.execute(
        select(TournamentSession)
        .filter(
            TournamentSession.professor_user_id == professor.id,
            TournamentSession.title == SESSION_TITLE,
        )
        .order_by(TournamentSession.id.desc())
    )
    target = existing.scalars().first()

    if target is None:
        target = await tournament_crud.create_session(
            db,
            title=SESSION_TITLE,
            professor_user_id=professor.id,
            allow_self_vote=True,
        )
    else:
        target = await tournament_crud.update_session(
            db,
            session=target,
            title=SESSION_TITLE,
            allow_self_vote=True,
        )

    target = await tournament_crud.update_session_format(
        db,
        session=target,
        format_text=None,
        format_json=FORMAT_JSON,
    )
    return target


def build_team_payload(students):
    teams = []
    cursor = 0
    for name in TEAM_NAMES:
        members = [(students[cursor + i].id, True) for i in range(MEMBERS_PER_TEAM)]
        cursor += MEMBERS_PER_TEAM
        teams.append((name, members))
    return teams


async def main():
    async with AsyncSessionLocal() as db:
        print("▶ 교수 계정 조회 중...")
        professor = await ensure_professor(db)

        print(f"▶ 학생 {TOTAL_STUDENTS}명 생성 중...")
        students = await ensure_students(db)

        print("▶ 세션 생성/갱신 중...")
        session = await ensure_session(db, professor)

        print("▶ 팀 구성 중...")
        team_payload = build_team_payload(students)
        await tournament_crud.replace_session_teams(db, session_id=session.id, teams=team_payload)

        print("▶ 대진표 생성 중...")
        team_rows = await tournament_crud.list_session_teams_without_members(db, session_id=session.id)
        normalized = _normalize_format_json(FORMAT_JSON)
        matches_payload = _build_matches_payload([t.id for t in team_rows], normalized)
        created = await tournament_crud.replace_session_matches(
            db, session_id=session.id, matches=matches_payload
        )

        bye_count = 0
        for m in created:
            if m.is_bye and m.winner_team_id is not None:
                await tournament_crud.advance_match_result(db, match_id=int(m.id))
                bye_count += 1

        now = datetime.now(timezone.utc).isoformat()
        print("\n✅ 완료!")
        print({
            "seeded_at": now,
            "professor_email": PROF_EMAIL,
            "session_id": session.id,
            "session_title": SESSION_TITLE,
            "allow_self_vote": True,
            "team_count": len(team_payload),
            "student_count": len(students),
            "match_count": len(matches_payload),
            "bye_matches": bye_count,
        })
        print(f"\n대진표 URL (학생): /tournaments/{session.id}/bracket")
        print(f"대진표 URL (교수): /professor/tournaments/{session.id}/bracket")
        print(f"\n※ {SPECIAL_EMAIL} 계정으로 투표 UI 직접 테스트 가능 (자기팀 투표 가능)")
        print(f"   나머지 47명은 대리 투표 스크립트로 처리 가능")
        print(f"\n   buriburisuri user_id: {students[0].id}")


if __name__ == "__main__":
    asyncio.run(main())
