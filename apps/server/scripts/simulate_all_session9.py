"""
Session 9 (16강 DE, 3명×16팀, allow_self_vote=True) 나머지 전 경기 대리 투표 스크립트.

처리 순서:
1. 두 팀 모두 확정된 pending 경기를 찾음
2. status → open
3. 모든 eligible 학생 대리 투표 (이미 투표한 경우 skip)
4. status → closed + winner 설정
5. advance_match_result 호출
6. 반복
"""
from __future__ import annotations

import asyncio
import datetime
import random

from sqlalchemy import func, select

from app import crud, crud_tournaments as tournament_crud
from app.database import AsyncSessionLocal
from app.models import TournamentMatch, TournamentTeam, TournamentTeamMember, TournamentVote

SESSION_ID = 9
SPECIAL_EMAIL = "buriburisuri@gmail.com"
random.seed(42)


async def main():
    async with AsyncSessionLocal() as db:
        # 모든 eligible 투표자 조회 (can_attend_vote=True)
        voters_result = await db.execute(
            select(TournamentTeamMember.student_user_id)
            .join(TournamentTeam, TournamentTeam.id == TournamentTeamMember.team_id)
            .filter(
                TournamentTeam.session_id == SESSION_ID,
                TournamentTeamMember.can_attend_vote == True,
            )
        )
        all_voter_ids = [row[0] for row in voters_result]
        print(f"총 투표 가능 학생: {len(all_voter_ids)}명")

        special = await crud.get_user_by_email_basic(db, SPECIAL_EMAIL)
        special_id = special.id if special else None
        print(f"buriburisuri user_id: {special_id}")

        processed = 0
        max_iterations = 200

        for iteration in range(max_iterations):
            # 두 팀 모두 확정된 pending 경기 조회
            result = await db.execute(
                select(TournamentMatch)
                .filter(
                    TournamentMatch.session_id == SESSION_ID,
                    TournamentMatch.status == "pending",
                    TournamentMatch.is_bye == False,
                    TournamentMatch.team1_id.isnot(None),
                    TournamentMatch.team2_id.isnot(None),
                )
                .order_by(
                    TournamentMatch.bracket_type,  # losers < winners 알파벳순이나 DB에 따라 다름
                    TournamentMatch.round_no,
                    TournamentMatch.match_no,
                )
            )
            ready = result.scalars().all()

            if not ready:
                print(f"\n처리할 경기 없음. 완료! (총 {processed}경기 처리)")
                break

            print(f"\n[iteration {iteration + 1}] {len(ready)}경기 처리 중...")

            for match in ready:
                label = f"[{match.bracket_type[:1].upper()}] R{match.round_no}.M{match.match_no} (id={match.id})"
                print(f"  {label}: t1={match.team1_id} vs t2={match.team2_id}", end="")

                # 1. Open
                match.status = "open"
                match.opened_at = datetime.datetime.now(tz=datetime.timezone.utc)
                await db.commit()

                # 2. 이미 투표한 user 조회
                existing_result = await db.execute(
                    select(TournamentVote.voter_user_id)
                    .filter(TournamentVote.match_id == match.id)
                )
                already_voted = {row[0] for row in existing_result}

                # 3. 대리 투표 (50/50 랜덤)
                now = datetime.datetime.now(tz=datetime.timezone.utc)
                t1_count_new = 0
                t2_count_new = 0
                for voter_id in all_voter_ids:
                    if voter_id in already_voted:
                        continue
                    team_id = match.team1_id if random.random() < 0.5 else match.team2_id
                    db.add(TournamentVote(
                        match_id=match.id,
                        voter_user_id=voter_id,
                        selected_team_id=team_id,
                        created_at=now,
                    ))
                    if team_id == match.team1_id:
                        t1_count_new += 1
                    else:
                        t2_count_new += 1
                await db.commit()

                # 전체 득표 집계
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
                print(f"  → t1={t1_total} t2={t2_total} winner={winner_id}")

                # 4. Close + set winner
                match.status = "closed"
                match.winner_team_id = winner_id
                await db.commit()
                await db.refresh(match)

                # 5. Advance
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
            print(f"  id={m.id} [{m.bracket_type:7s}] R{m.round_no}.M{m.match_no:2d} {m.status:7s} winner={m.winner_team_id}")


if __name__ == "__main__":
    asyncio.run(main())
