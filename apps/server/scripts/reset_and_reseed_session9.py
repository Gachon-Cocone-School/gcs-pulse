"""
Session 9 (16강 DE) 브래킷 재생성 + 전 경기 시뮬레이션 스크립트.

수정된 _build_double_elim_payload (WB R3 패자 → LB, WB R4 = Grand Final)를
적용해 브래킷을 재생성하고 모든 경기를 대리 투표로 시뮬레이션한다.
"""
from __future__ import annotations

import asyncio
import datetime
import random

from sqlalchemy import func, select

from app import crud, crud_tournaments as tournament_crud
from app.database import AsyncSessionLocal
from app.models import TournamentMatch, TournamentTeam, TournamentTeamMember, TournamentVote
from app.routers.tournaments import _build_matches_payload

SESSION_ID = 9
FORMAT_JSON = {"bracket_size": 16, "repechage": {"enabled": True}}
random.seed(42)


async def main():
    async with AsyncSessionLocal() as db:
        # 팀 목록 조회
        teams = await tournament_crud.list_session_teams_without_members(db, session_id=SESSION_ID)
        if not teams:
            print("세션 9 팀 없음. 종료.")
            return
        print(f"팀 수: {len(teams)}")
        for t in teams:
            print(f"  id={t.id} name={t.name}")

        # 브래킷 재생성 (기존 matches + votes 모두 삭제 후 재생성)
        print("\n브래킷 재생성 중...")
        matches_payload = _build_matches_payload([t.id for t in teams], FORMAT_JSON)
        created = await tournament_crud.replace_session_matches(
            db, session_id=SESSION_ID, matches=matches_payload
        )
        print(f"  생성된 경기 수: {len(created)}")

        # BYE 경기 자동 진출
        bye_count = 0
        for m in created:
            if m.is_bye and m.winner_team_id is not None:
                await tournament_crud.advance_match_result(db, match_id=int(m.id))
                bye_count += 1
        if bye_count:
            print(f"  BYE 경기 자동 진출: {bye_count}개")

        # 브래킷 구조 출력
        print("\n=== 생성된 브래킷 ===")
        bracket_result = await db.execute(
            select(TournamentMatch)
            .filter(TournamentMatch.session_id == SESSION_ID)
            .order_by(TournamentMatch.bracket_type, TournamentMatch.round_no, TournamentMatch.match_no)
        )
        for m in bracket_result.scalars().all():
            next_str = f"→next={m.next_match_id}" if m.next_match_id else ""
            loser_str = f"→loser={m.loser_next_match_id}" if m.loser_next_match_id else ""
            print(f"  id={m.id} [{m.bracket_type:7s}] R{m.round_no}.M{m.match_no:2d} {m.status:7s} {next_str} {loser_str}")

        # 투표 가능 학생 조회
        voters_result = await db.execute(
            select(TournamentTeamMember.student_user_id)
            .join(TournamentTeam, TournamentTeam.id == TournamentTeamMember.team_id)
            .filter(
                TournamentTeam.session_id == SESSION_ID,
                TournamentTeamMember.can_attend_vote == True,
            )
        )
        all_voter_ids = [row[0] for row in voters_result]
        print(f"\n총 투표 가능 학생: {len(all_voter_ids)}명")

        # 전 경기 시뮬레이션
        print("\n=== 시뮬레이션 시작 ===")
        processed = 0

        for iteration in range(200):
            result = await db.execute(
                select(TournamentMatch)
                .filter(
                    TournamentMatch.session_id == SESSION_ID,
                    TournamentMatch.status == "pending",
                    TournamentMatch.is_bye == False,
                    TournamentMatch.team1_id.isnot(None),
                    TournamentMatch.team2_id.isnot(None),
                )
                .order_by(TournamentMatch.bracket_type, TournamentMatch.round_no, TournamentMatch.match_no)
            )
            ready = result.scalars().all()

            if not ready:
                print(f"\n처리할 경기 없음. 완료! (총 {processed}경기 처리)")
                break

            print(f"\n[iteration {iteration + 1}] {len(ready)}경기 처리 중...")

            for match in ready:
                label = f"[{match.bracket_type[:1].upper()}] R{match.round_no}.M{match.match_no} (id={match.id})"

                # Open
                match.status = "open"
                match.opened_at = datetime.datetime.now(tz=datetime.timezone.utc)
                await db.commit()

                # 대리 투표
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                for voter_id in all_voter_ids:
                    team_id = match.team1_id if random.random() < 0.5 else match.team2_id
                    db.add(TournamentVote(
                        match_id=match.id,
                        voter_user_id=voter_id,
                        selected_team_id=team_id,
                        created_at=now,
                    ))
                await db.commit()

                # 득표 집계
                t1_total = (await db.execute(
                    select(func.count(TournamentVote.id)).filter(
                        TournamentVote.match_id == match.id,
                        TournamentVote.selected_team_id == match.team1_id,
                    )
                )).scalar() or 0
                t2_total = (await db.execute(
                    select(func.count(TournamentVote.id)).filter(
                        TournamentVote.match_id == match.id,
                        TournamentVote.selected_team_id == match.team2_id,
                    )
                )).scalar() or 0

                winner_id = match.team1_id if t1_total >= t2_total else match.team2_id
                print(f"  {label}: t1={t1_total} t2={t2_total} winner={winner_id}")

                # Close + winner
                match.status = "closed"
                match.winner_team_id = winner_id
                await db.commit()
                await db.refresh(match)

                await tournament_crud.advance_match_result(db, match_id=int(match.id))
                processed += 1

        # 최종 현황
        print("\n=== 최종 경기 현황 ===")
        final_result = await db.execute(
            select(TournamentMatch)
            .filter(TournamentMatch.session_id == SESSION_ID)
            .order_by(TournamentMatch.bracket_type, TournamentMatch.round_no, TournamentMatch.match_no)
        )
        for m in final_result.scalars().all():
            print(
                f"  id={m.id} [{m.bracket_type:7s}] R{m.round_no}.M{m.match_no:2d}"
                f" {m.status:7s} winner={m.winner_team_id}"
            )


if __name__ == "__main__":
    asyncio.run(main())
