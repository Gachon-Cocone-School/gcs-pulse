#!/usr/bin/env python3
"""
토너먼트 동시 투표 시뮬레이션 스크립트 (DB 직접 접근)

데이터베이스에 직접 접속하여 동시에 투표를 생성합니다.
HTTP 레벨의 인증/CSRF 문제를 우회합니다.

사용법:
    python scripts/db_concurrent_votes.py <match_id> <num_concurrent_requests>

예시:
    python scripts/db_concurrent_votes.py 789 200
"""

import asyncio
import sys
import time
import random
from pathlib import Path

# app 모듈 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "server"))

from app.database import AsyncSessionLocal
from app.models import TournamentMatch, TournamentVote
from sqlalchemy import select


async def simulate_votes_for_user(
    match_id: int,
    voter_user_id: int,
    team1_id: int,
    team2_id: int,
    user_index: int,
) -> dict:
    """단일 사용자의 투표 시뮬레이션"""
    start_time = time.time()

    try:
        async with AsyncSessionLocal() as session:
            # 이미 투표한 사용자인지 확인
            existing_vote = await session.execute(
                select(TournamentVote).where(
                    TournamentVote.match_id == match_id,
                    TournamentVote.voter_user_id == voter_user_id,
                )
            )
            if existing_vote.scalars().first():
                return {
                    "user_index": user_index,
                    "voter_user_id": voter_user_id,
                    "status": "skipped",
                    "success": True,
                    "elapsed_time": time.time() - start_time,
                    "reason": "already_voted",
                }

            # 랜덤 팀 선택
            selected_team_id = random.choice([team1_id, team2_id])

            # 투표 생성
            vote = TournamentVote(
                match_id=match_id,
                voter_user_id=voter_user_id,
                selected_team_id=selected_team_id,
            )
            session.add(vote)
            await session.commit()

            return {
                "user_index": user_index,
                "voter_user_id": voter_user_id,
                "status": "voted",
                "success": True,
                "elapsed_time": time.time() - start_time,
                "selected_team_id": selected_team_id,
            }
    except Exception as e:
        return {
            "user_index": user_index,
            "voter_user_id": voter_user_id,
            "status": "error",
            "success": False,
            "elapsed_time": time.time() - start_time,
            "error": str(e),
        }


async def main() -> None:
    if len(sys.argv) < 3:
        print("사용법: python scripts/db_concurrent_votes.py <match_id> <num_concurrent_requests>")
        print("예시: python scripts/db_concurrent_votes.py 789 200")
        sys.exit(1)

    match_id = int(sys.argv[1])
    num_users = int(sys.argv[2])

    print(f"토너먼트 동시 투표 시뮬레이션 (DB 직접 접근)")
    print(f"Match ID: {match_id}")
    print(f"동시 사용자 수: {num_users}")
    print("-" * 60)

    # 경기 정보 가져오기
    async with AsyncSessionLocal() as session:
        match_result = await session.execute(
            select(TournamentMatch).where(TournamentMatch.id == match_id)
        )
        match = match_result.scalars().first()

        if not match:
            print(f"경기를 찾을 수 없습니다: Match ID {match_id}")
            sys.exit(1)

        print(f"경기 상태: {match.status}")
        print(f"Team 1 ID: {match.team1_id}")
        print(f"Team 2 ID: {match.team2_id}")
        print("-" * 60)

        if match.team1_id is None or match.team2_id is None:
            print("경기에 두 팀이 모두 할당되지 않았습니다.")
            sys.exit(1)

    # DB 커넥션 풀 설정
    print("📊 DB 커넥션 풀 설정")
    print("   - pool_size: 20")
    print("   - max_overflow: 25")
    print("   - 총 최대 커넥션: 45개")
    print(f"   - 동시 사용자 수: {num_users}")
    if num_users > 45:
        print("   ⚠️  커넥션 풀 병목이 발생할 수 있습니다!")
    print("-" * 60)

    # 동시 투표 시작
    print(f"{num_users}명의 사용자가 동시에 투표를 시작합니다...")
    start_time = time.time()

    tasks = [
        simulate_votes_for_user(
            match_id=match_id,
            voter_user_id=i + 1,
            team1_id=match.team1_id,
            team2_id=match.team2_id,
            user_index=i + 1,
        )
        for i in range(num_users)
    ]

    results = await asyncio.gather(*tasks, return_exceptions=True)
    total_elapsed = time.time() - start_time

    # 결과 분석
    successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
    failed = sum(1 for r in results if isinstance(r, dict) and not r.get("success"))
    errors = sum(1 for r in results if isinstance(r, Exception))

    print("-" * 60)
    print(f"테스트 완료! 총 소요 시간: {total_elapsed:.2f}초")
    print(f"성공: {successful}/{num_users}")
    print(f"실패: {failed}/{num_users}")
    if errors > 0:
        print(f"예외: {errors}/{num_users}")

    # 응답 시간 통계
    if successful > 0:
        elapsed_times = [
            r["elapsed_time"]
            for r in results
            if isinstance(r, dict) and r.get("success") and r.get("elapsed_time", 0) > 0
        ]
        if elapsed_times:
            avg_time = sum(elapsed_times) / len(elapsed_times)
            max_time = max(elapsed_times)
            min_time = min(elapsed_times)

            print(f"\n응답 시간 통계:")
            print(f"  평균: {avg_time:.2f}초")
            print(f"  최대: {max_time:.2f}초")
            print(f"  최소: {min_time:.2f}초")

            # 처리량 계산
            throughput = successful / total_elapsed
            print(f"  처리량: {throughput:.2f} votes/second")

            # 이전 결과와 비교
            print(f"\n📈 성능 비교:")
            print(f"  이전 (pool=4):  3.76초, 53.19 votes/sec")
            print(f"  현재 (pool=45): {total_elapsed:.2f}초, {throughput:.2f} votes/sec")
            improvement = ((3.76 - total_elapsed) / 3.76) * 100
            print(f"  개선율: {improvement:.1f}% 더 빠름")

    if failed > 0:
        print("\n실패한 요청들:")
        for r in results:
            if isinstance(r, dict) and not r.get("success"):
                print(f"  User {r.get('user_index')}: {r.get('error', r.get('reason', 'Unknown'))}")

    # 최종 경기 상태 확인
    async with AsyncSessionLocal() as session:
        final_match = await session.execute(
            select(TournamentMatch).where(TournamentMatch.id == match_id)
        )
        match_data = final_match.scalars().first()

        if match_data:
            print(f"\n최종 경기 상태: {match_data.status}")

            # 투표 수 집계
            vote_result = await session.execute(
                select(TournamentVote).where(TournamentVote.match_id == match_id)
            )
            votes = vote_result.scalars().all()

            team1_votes = sum(1 for v in votes if v.selected_team_id == match_data.team1_id)
            team2_votes = sum(1 for v in votes if v.selected_team_id == match_data.team2_id)

            print(f"최종 투표 결과:")
            print(f"  Team 1 득표: {team1_votes}")
            print(f"  Team 2 득표: {team2_votes}")
            print(f"  총 투표 수: {len(votes)}")


if __name__ == "__main__":
    asyncio.run(main())
