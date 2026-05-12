#!/usr/bin/env python3
"""
토너먼트 동시 투표 시뮬레이션 스크립트

사용법:
    python scripts/simultaneous_tournament_votes.py <match_id> <num_users> <base_url>

예시:
    python scripts/simultaneous_tournament_votes.py 123 30 http://localhost:8000
"""

import asyncio
import sys
import random
from typing import Any
import httpx


async def submit_vote(
    client: httpx.AsyncClient,
    match_id: int,
    user_token: str,
    team_id: int,
    user_index: int,
) -> dict[str, Any]:
    """단일 사용자의 투표 제출"""
    try:
        response = await client.post(
            f"/tournaments/matches/{match_id}/vote",
            json={"selected_team_id": team_id},
            headers={"Cookie": f"session={user_token}"},
            timeout=30.0,
        )
        return {
            "user_index": user_index,
            "status": response.status_code,
            "success": response.status_code == 200,
            "response": response.json() if response.status_code == 200 else response.text,
        }
    except Exception as e:
        return {
            "user_index": user_index,
            "status": "error",
            "success": False,
            "response": str(e),
        }


async def main() -> None:
    if len(sys.argv) < 4:
        print("사용법: python scripts/simultaneous_tournament_votes.py <match_id> <num_users> <base_url>")
        print("예시: python scripts/simultaneous_tournament_votes.py 123 30 http://localhost:8000")
        sys.exit(1)

    match_id = int(sys.argv[1])
    num_users = int(sys.argv[2])
    base_url = sys.argv[3].rstrip("/")

    print(f"토너먼트 동시 투표 시뮬레이션 시작")
    print(f"Match ID: {match_id}")
    print(f"동시 사용자 수: {num_users}")
    print(f"타겟 URL: {base_url}")
    print("-" * 50)

    async with httpx.AsyncClient(base_url=base_url) as client:
        # 먼저 경기 정보 가져오기
        match_response = await client.get(f"/tournaments/matches/{match_id}")
        if match_response.status_code != 200:
            print(f"경기 정보를 가져오는데 실패했습니다: {match_response.status_code}")
            sys.exit(1)

        match_data = match_response.json()
        team1_id = match_data.get("team1_id")
        team2_id = match_data.get("team2_id")

        if not team1_id or not team2_id:
            print("경기에 두 팀이 모두 할당되지 않았습니다.")
            sys.exit(1)

        print(f"Team 1 ID: {team1_id}, Team 2 ID: {team2_id}")
        print(f"경기 상태: {match_data.get('status')}")
        print("-" * 50)

        # 동시 투표 제출
        print(f"{num_users}명의 사용자가 동시에 투표를 시작합니다...")
        print("-" * 50)

        # 각 사용자에 대한 세션 토큰 생성 (실제로는 인증된 사용자의 토큰이 필요함)
        # 여기서는 예시로 user_1, user_2, ... 형태 사용
        # 실제 사용 시에는 인증된 세션 토큰을 전달해야 함

        tasks = []
        for i in range(num_users):
            user_token = f"user_{i+1}_session_token"  # 실제 인증 토큰으로 교체 필요
            selected_team = random.choice([team1_id, team2_id])

            task = submit_vote(
                client=client,
                match_id=match_id,
                user_token=user_token,
                team_id=selected_team,
                user_index=i + 1,
            )
            tasks.append(task)

        # 모든 투표 동시 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 결과 분석
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = num_users - successful

        print("-" * 50)
        print(f"테스트 완료!")
        print(f"성공: {successful}/{num_users}")
        print(f"실패: {failed}/{num_users}")

        if failed > 0:
            print("\n실패한 요청들:")
            for r in results:
                if isinstance(r, dict) and not r.get("success"):
                    print(f"  User {r.get('user_index')}: {r.get('response')}")

        # 최종 경기 상태 확인
        final_match = await client.get(f"/tournaments/matches/{match_id}")
        if final_match.status_code == 200:
            final_data = final_match.json()
            print(f"\n최종 투표 결과:")
            print(f"  Team 1 득표: {final_data.get('vote_count_team1')}")
            print(f"  Team 2 득표: {final_data.get('vote_count_team2')}")


if __name__ == "__main__":
    asyncio.run(main())
