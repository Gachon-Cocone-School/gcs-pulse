from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app import crud
from app import crud_tournaments as tournament_crud
from app.database import AsyncSessionLocal
from app.models import TournamentSession


PROF_EMAIL = "e2e-prof@example.com"
PROF_NAME = "E2E Professor"
SESSION_TITLE = "E2E Tournament 2v2 8강"


async def ensure_professor(db):
    await crud.create_or_update_user(
        db,
        {
            "email": PROF_EMAIL,
            "name": PROF_NAME,
            "picture": "",
            "email_verified": True,
        },
    )
    professor = await crud.get_user_by_email_basic(db, PROF_EMAIL)
    if professor is None:
        raise RuntimeError("Failed to create professor user")

    professor.roles = ["교수", "gcs"]
    await db.commit()
    await db.refresh(professor)
    return professor


async def ensure_students(db):
    students = []
    for i in range(1, 22):
        email = f"tour-student-{i:02d}@example.com"
        name = f"토너먼트학생{i:02d}"
        await crud.create_or_update_user(
            db,
            {
                "email": email,
                "name": name,
                "picture": "",
                "email_verified": True,
            },
        )
        user = await crud.get_user_by_email_basic(db, email)
        if user is None:
            raise RuntimeError(f"Failed to create student user: {email}")
        user.roles = ["gcs"]
        students.append(user)

    await db.commit()

    refreshed = []
    for i in range(1, 22):
        email = f"tour-student-{i:02d}@example.com"
        user = await crud.get_user_by_email_basic(db, email)
        if user is None:
            raise RuntimeError(f"Missing student user after commit: {email}")
        refreshed.append(user)

    return refreshed


async def ensure_session(db, professor):
    existing_result = await db.execute(
        select(TournamentSession)
        .filter(
            TournamentSession.professor_user_id == professor.id,
            TournamentSession.title == SESSION_TITLE,
        )
        .order_by(TournamentSession.id.desc())
    )
    target = existing_result.scalars().first()

    if target is None:
        target = await tournament_crud.create_session(
            db,
            title=SESSION_TITLE,
            professor_user_id=professor.id,
        )

    target = await tournament_crud.update_session(
        db,
        session=target,
        title=SESSION_TITLE,
    )
    target = await tournament_crud.update_session_format(
        db,
        session=target,
        format_text="2자대결 8강",
        format_json={
            "match_size": 2,
            "bracket_size": 8,
            "repechage": {"enabled": False, "style": None},
        },
    )
    target = await tournament_crud.update_session_is_open(db, session=target, is_open=True)
    return target


def build_team_payload(students):
    teams = []
    cursor = 0
    for team_idx in range(1, 8):
        members = []
        for _ in range(3):
            student = students[cursor]
            cursor += 1
            members.append((student.id, True))
        teams.append((f"{team_idx}팀", members))
    return teams


def build_matches_payload(team_ids):
    slots = team_ids + [None]

    payload = [
        {
            "bracket_type": "main",
            "round_no": 1,
            "match_no": 1,
            "status": "pending",
            "is_bye": False,
            "team1_id": slots[0],
            "team2_id": slots[1],
            "winner_team_id": None,
            "next_index": 4,
        },
        {
            "bracket_type": "main",
            "round_no": 1,
            "match_no": 2,
            "status": "pending",
            "is_bye": False,
            "team1_id": slots[2],
            "team2_id": slots[3],
            "winner_team_id": None,
            "next_index": 4,
        },
        {
            "bracket_type": "main",
            "round_no": 1,
            "match_no": 3,
            "status": "pending",
            "is_bye": False,
            "team1_id": slots[4],
            "team2_id": slots[5],
            "winner_team_id": None,
            "next_index": 5,
        },
        {
            "bracket_type": "main",
            "round_no": 1,
            "match_no": 4,
            "status": "closed" if slots[7] is None else "pending",
            "is_bye": slots[7] is None,
            "team1_id": slots[6],
            "team2_id": slots[7],
            "winner_team_id": slots[6] if slots[7] is None else None,
            "next_index": 5,
        },
        {
            "bracket_type": "main",
            "round_no": 2,
            "match_no": 1,
            "status": "pending",
            "is_bye": False,
            "team1_id": None,
            "team2_id": None,
            "winner_team_id": None,
            "next_index": 6,
        },
        {
            "bracket_type": "main",
            "round_no": 2,
            "match_no": 2,
            "status": "pending",
            "is_bye": False,
            "team1_id": None,
            "team2_id": None,
            "winner_team_id": None,
            "next_index": 6,
        },
        {
            "bracket_type": "main",
            "round_no": 3,
            "match_no": 1,
            "status": "pending",
            "is_bye": False,
            "team1_id": None,
            "team2_id": None,
            "winner_team_id": None,
            "next_index": None,
        },
    ]

    return payload


async def main():
    async with AsyncSessionLocal() as db:
        professor = await ensure_professor(db)
        students = await ensure_students(db)
        session = await ensure_session(db, professor)

        team_payload = build_team_payload(students)
        await tournament_crud.replace_session_teams(
            db,
            session_id=session.id,
            teams=team_payload,
        )

        team_rows = await tournament_crud.list_session_teams_without_members(db, session_id=session.id)
        matches_payload = build_matches_payload([team.id for team in team_rows])
        await tournament_crud.replace_session_matches(
            db,
            session_id=session.id,
            matches=matches_payload,
        )

        now = datetime.now(timezone.utc).isoformat()
        print(
            {
                "seeded_at": now,
                "professor_email": PROF_EMAIL,
                "session_id": session.id,
                "session_title": SESSION_TITLE,
                "student_count": len(students),
                "team_count": len(team_payload),
                "match_count": len(matches_payload),
            }
        )


if __name__ == "__main__":
    asyncio.run(main())
