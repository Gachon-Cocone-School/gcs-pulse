"""
4강 / 8강 / 16강 / 32강 DE 토너먼트 일괄 생성 + 전 경기 시뮬레이션 스크립트.

각 세션:
  - 팀 구성: 3명 × n팀 (n = 4 / 8 / 16 / 32)
  - 팀 이름: "1팀", "2팀", …
  - 포맷: 더블 엘리미네이션 (패자부활전)
  - allow_self_vote=True (팀원도 투표 가능)
  - can_attend_vote=True (모든 팀원 투표 참여)

시뮬레이션:
  - 각 팀원이 매 경기마다 무작위 투표 (50/50)
  - 각 투표의 응답 시간은 0.5–60초 사이 랜덤 → 투표자 순위에 반영
  - 브래킷 재사용: 같은 학생이 여러 세션에 중복 참여 가능
"""
from __future__ import annotations

import asyncio
import datetime
import random

from sqlalchemy import func, select

from app import crud_tournaments as tournament_crud
from app.database import AsyncSessionLocal
from app.models import (
    TournamentMatch,
    TournamentSession,
    TournamentTeam,
    TournamentTeamMember,
    TournamentVote,
    User,
)
from app.routers.tournaments import _build_matches_payload

# ──────────────────────────────────────────────
# 설정
# ──────────────────────────────────────────────
MEMBERS_PER_TEAM = 3

# (팀 수, 포맷)  ※ DE는 8강 이상만 지원 → 4강은 단일 토너먼트
SESSIONS: list[tuple[int, dict]] = [
    (4,  {"bracket_size": 4,  "repechage": {"enabled": False}}),  # 4강 SE
    (8,  {"bracket_size": 8,  "repechage": {"enabled": True}}),   # 8강 DE
    (16, {"bracket_size": 16, "repechage": {"enabled": True}}),   # 16강 DE
    (32, {"bracket_size": 32, "repechage": {"enabled": True}}),   # 32강 DE
]
MAX_STUDENTS = max(n for n, _ in SESSIONS) * MEMBERS_PER_TEAM    # 96명

PROF_EMAIL = "namjookim@gachon.ac.kr"
SIM_EMAIL_FMT = "sim_s{i:03d}@gachon.ac.kr"
SIM_NAME_FMT = "시뮬{i:03d}"

RANDOM_SEED = 42


# ──────────────────────────────────────────────
# 헬퍼
# ──────────────────────────────────────────────
async def get_or_create_user(db, email: str, name: str, roles: list) -> User:
    result = await db.execute(select(User).filter(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        user = User(email=email, name=name, roles=roles)
        db.add(user)
        await db.flush()
    return user


async def simulate_match(
    db,
    match: TournamentMatch,
    voter_ids: list[int],
    opened_at: datetime.datetime,
    rng: random.Random,
) -> None:
    """단일 경기: open → 투표 → close → advance."""
    match.status = "open"
    match.opened_at = opened_at
    await db.commit()

    # 투표 (각 팀원이 응답 시간 랜덤하게 투표)
    for voter_id in voter_ids:
        team_id = match.team1_id if rng.random() < 0.5 else match.team2_id
        response_secs = rng.uniform(0.5, 60.0)
        voted_at = opened_at + datetime.timedelta(seconds=response_secs)
        db.add(TournamentVote(
            match_id=match.id,
            voter_user_id=voter_id,
            selected_team_id=team_id,
            created_at=voted_at,
        ))
    await db.commit()

    # 득표 집계
    t1_votes = (await db.execute(
        select(func.count(TournamentVote.id)).filter(
            TournamentVote.match_id == match.id,
            TournamentVote.selected_team_id == match.team1_id,
        )
    )).scalar() or 0
    t2_votes = (await db.execute(
        select(func.count(TournamentVote.id)).filter(
            TournamentVote.match_id == match.id,
            TournamentVote.selected_team_id == match.team2_id,
        )
    )).scalar() or 0

    winner_id = match.team1_id if t1_votes >= t2_votes else match.team2_id
    match.status = "closed"
    match.winner_team_id = winner_id
    await db.commit()
    await db.refresh(match)
    await tournament_crud.advance_match_result(db, match_id=int(match.id))


async def run_session(
    db,
    n_teams: int,
    format_json: dict,
    professor_id: int,
    student_ids: list[int],
    rng: random.Random,
) -> None:
    bracket_size = format_json["bracket_size"]
    is_de = format_json.get("repechage", {}).get("enabled", False)
    fmt_label = "DE" if is_de else "SE"
    n_members_total = n_teams * MEMBERS_PER_TEAM

    print(f"\n{'─' * 60}")
    print(f"[{bracket_size}강 {fmt_label}]  {n_teams}팀 × {MEMBERS_PER_TEAM}명 = {n_members_total}명 투표자")

    # ── 세션 생성 ──────────────────────────────
    title_suffix = "DE (패자부활전)" if is_de else "SE (단일)"
    session = TournamentSession(
        title=f"시뮬레이션 {bracket_size}강 {title_suffix}",
        professor_user_id=professor_id,
        allow_self_vote=True,
        format_json=format_json,
    )
    db.add(session)
    await db.flush()
    session_id = int(session.id)
    print(f"  세션 ID: {session_id}")

    # ── 팀 + 팀원 생성 ──────────────────────────
    team_ids: list[int] = []
    voter_ids: list[int] = []

    for t in range(n_teams):
        team = TournamentTeam(session_id=session_id, name=f"{t + 1}팀")
        db.add(team)
        await db.flush()
        team_ids.append(int(team.id))

        for m in range(MEMBERS_PER_TEAM):
            s_id = student_ids[t * MEMBERS_PER_TEAM + m]
            db.add(TournamentTeamMember(
                team_id=team.id,
                student_user_id=s_id,
                can_attend_vote=True,
            ))
            voter_ids.append(s_id)

    await db.commit()
    print(f"  팀 생성: {n_teams}팀  (팀 ID {team_ids[0]}–{team_ids[-1]})")

    # ── 브래킷 생성 ────────────────────────────
    payload = _build_matches_payload(team_ids, format_json)  # type: ignore[arg-type]
    created = await tournament_crud.replace_session_matches(
        db, session_id=session_id, matches=payload
    )
    print(f"  경기 생성: {len(created)}경기")

    # BYE 자동 진출
    bye_count = 0
    for m in created:
        if m.is_bye and m.winner_team_id is not None:
            await tournament_crud.advance_match_result(db, match_id=int(m.id))
            bye_count += 1
    if bye_count:
        print(f"  BYE 자동 진출: {bye_count}경기")

    # ── 전 경기 시뮬레이션 ──────────────────────
    base_time = datetime.datetime(2025, 3, 20, 10, 0, 0, tzinfo=datetime.timezone.utc)
    match_offset_minutes = 0
    processed = 0

    for iteration in range(300):
        result = await db.execute(
            select(TournamentMatch).filter(
                TournamentMatch.session_id == session_id,
                TournamentMatch.status == "pending",
                TournamentMatch.is_bye == False,
                TournamentMatch.team1_id.isnot(None),
                TournamentMatch.team2_id.isnot(None),
            ).order_by(
                TournamentMatch.bracket_type,
                TournamentMatch.round_no,
                TournamentMatch.match_no,
            )
        )
        ready = result.scalars().all()
        if not ready:
            break

        for match in ready:
            opened_at = base_time + datetime.timedelta(minutes=match_offset_minutes)
            match_offset_minutes += rng.randint(5, 15)  # 경기 간 시간 간격
            await simulate_match(db, match, voter_ids, opened_at, rng)
            processed += 1

    print(f"  시뮬레이션 완료: {processed}경기 처리")

    # ── 순위 출력 ──────────────────────────────
    results = await tournament_crud.get_session_results(db, session_id=session_id)
    rankings = results.get("team_rankings", [])
    print(f"\n  ┌─ 팀 순위 ({'─' * 25}")
    for r in rankings:
        print(f"  │  {r['rank']:2d}위  {r['team_name']}")
    print(f"  └{'─' * 30}")

    voter_rankings = results.get("voter_rankings", [])
    if voter_rankings:
        print(f"\n  ┌─ 투표자 순위 (상위 5명)")
        for v in voter_rankings[:5]:
            print(
                f"  │  {v['rank']:2d}위  {v['voter_name']}"
                f"  {v['score']}/{v['total_matches']}경기"
                f"  응답 {v['cumulative_response_seconds']:.1f}초"
            )
        print(f"  └{'─' * 30}")


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────
async def main() -> None:
    rng = random.Random(RANDOM_SEED)

    async with AsyncSessionLocal() as db:
        # ── 교수 유저 ──────────────────────────
        professor = await get_or_create_user(
            db, PROF_EMAIL, "남주구",
            roles=["gcs", "교수", "admin"],
        )
        await db.commit()
        print(f"교수: id={professor.id}  ({professor.email})")

        # ── 학생 유저 96명 ─────────────────────
        student_ids: list[int] = []
        for i in range(1, MAX_STUDENTS + 1):
            u = await get_or_create_user(
                db,
                SIM_EMAIL_FMT.format(i=i),
                SIM_NAME_FMT.format(i=i),
                roles=["gcs"],
            )
            student_ids.append(int(u.id))
        await db.commit()
        print(f"학생 유저 {len(student_ids)}명 준비 완료  (ID {student_ids[0]}–{student_ids[-1]})")

        # ── 각 세션 실행 ────────────────────────
        for n_teams, format_json in SESSIONS:
            n = n_teams * MEMBERS_PER_TEAM
            session_students = student_ids[:n]
            await run_session(db, n_teams, format_json, int(professor.id), session_students, rng)

    print(f"\n{'=' * 60}")
    print("전체 시뮬레이션 완료!")


if __name__ == "__main__":
    asyncio.run(main())
