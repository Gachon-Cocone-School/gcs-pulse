"""
16팀 × 5명, 16강 패자부활전, allow_self_vote=True 토너먼트 세션 시드 스크립트.

기존 세션이 있으면 덮어씁니다.
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
PROF_NAME = "김남주/스타트업칼리지"
SESSION_TITLE = "16강 패자부활전 테스트 (팀원 투표 허용)"
NUM_TEAMS = 16
MEMBERS_PER_TEAM = 5

FORMAT_JSON = {
    "match_size": 2,
    "bracket_size": 16,
    "repechage": {"enabled": True, "style": None},
}

TEAM_NAMES = [
    "알파팀", "베타팀", "감마팀", "델타팀",
    "엡실론팀", "제타팀", "에타팀", "세타팀",
    "이오타팀", "카파팀", "람다팀", "뮤팀",
    "뉴팀", "크시팀", "오미크론팀", "파이팀",
]


async def ensure_professor(db):
    professor = await crud.get_user_by_email_basic(db, PROF_EMAIL)
    if professor is None:
        raise RuntimeError(f"Professor account not found: {PROF_EMAIL}")
    return professor


async def ensure_students(db):
    total = NUM_TEAMS * MEMBERS_PER_TEAM
    students = []
    for i in range(1, total + 1):
        email = f"tour16-student-{i:03d}@example.com"
        name = f"선수{i:03d}"
        await crud.create_or_update_user(
            db,
            {"email": email, "name": name, "picture": "", "email_verified": True},
        )
        user = await crud.get_user_by_email_basic(db, email)
        if user is None:
            raise RuntimeError(f"Failed to create student: {email}")
        user.roles = ["가천대학교", "gcs"]
        students.append(user)

    await db.commit()

    # 커밋 후 재조회 (id 확정)
    refreshed = []
    for i in range(1, total + 1):
        user = await crud.get_user_by_email_basic(db, f"tour16-student-{i:03d}@example.com")
        if user is None:
            raise RuntimeError(f"Missing student after commit: {i}")
        refreshed.append(user)
    return refreshed


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
        format_text="2자대결 16강 패자부활전",
        format_json=FORMAT_JSON,
    )
    return target


def build_team_payload(students):
    teams = []
    cursor = 0
    for i, name in enumerate(TEAM_NAMES):
        members = []
        for _ in range(MEMBERS_PER_TEAM):
            members.append((students[cursor].id, True))
            cursor += 1
        teams.append((name, members))
    return teams


async def main():
    async with AsyncSessionLocal() as db:
        print("▶ 교수 계정 생성 중...")
        professor = await ensure_professor(db)

        print(f"▶ 학생 {NUM_TEAMS * MEMBERS_PER_TEAM}명 생성 중...")
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

        # BYE 경기 자동 진출
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


if __name__ == "__main__":
    asyncio.run(main())
