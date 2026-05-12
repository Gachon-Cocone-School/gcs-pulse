#!/usr/bin/env python3
"""
토너먼트 동시 투표 시뮬레이션 스크립트 (Dev 엔드포인트 활용)

/dev/tournaments/matches/{match_id}/simulate-votes 엔드포인트를
동시에 여러 번 호출하여 진정한 동시성 테스트 수행

사용법:
    python scripts/simultaneous_dev_votes.py <match_id> <num_concurrent_requests> <base_url>

예시:
    python scripts/simultaneous_dev_votes.py 123 10 http://localhost:8000
"""

import asyncio
import sys
import time
from typing import Any
import httpx


async def simulate_votes(
    client: httpx.AsyncClient,
    match_id: int,
    request_index: int,
) -> dict[str, Any]:
    """단일 시뮬레이션 요청"""
    start_time = time.time()

    try:
        response = await client.post(
            f"/dev/tournaments/matches/{match_id}/simulate-votes",
            timeout=60.0,
        )
        elapsed = time.time() - start_time

        return {
            "request_index": request_index,
            "status": response.status_code,
            "success": response.status_code == 200,
            "elapsed_time": elapsed,
            "response": response.json() if response.status_code == 200 else response.text,
        }
    except Exception as e:
        elapsed = time.time() - start_time
        return {
            "request_index": request_index,
            "status": "error",
            "success": False,
            "elapsed_time": elapsed,
            "response": str(e),
        }


async def main() -> None:
    if len(sys.argv) < 4:
        print("사용법: python scripts/simultaneous_dev_votes.py <match_id> <num_concurrent_requests> <base_url>")
        print("예시: python scripts/simultaneous_dev_votes.py 123 10 http://localhost:8000")
        sys.exit(1)

    match_id = int(sys.argv[1])
    num_requests = int(sys.argv[2])
    base_url = sys.argv[3].rstrip("/")

    print(f"토너먼트 동시 투표 시뮬레이션 (Dev 엔드포인트)")
    print(f"Match ID: {match_id}")
    print(f"동시 요청 수: {num_requests}")
    print(f"타겟 URL: {base_url}")
    print("-" * 60)

    async with httpx.AsyncClient(base_url=base_url) as client:
        # 먼저 경기 정보 가져오기
        match_response = await client.get(f"/tournaments/matches/{match_id}")
        if match_response.status_code != 200:
            print(f"경기 정보를 가져오는데 실패했습니다: {match_response.status_code}")
            sys.exit(1)

        match_data = match_response.json()
        print(f"경기 상태: {match_data.get('status')}")
        print(f"Team 1: {match_data.get('team1_name')} (ID: {match_data.get('team1_id')})")
        print(f"Team 2: {match_data.get('team2_name')} (ID: {match_data.get('team2_id')})")
        print(f"현재 득표 - Team 1: {match_data.get('vote_count_team1')}, Team 2: {match_data.get('vote_count_team2')}")
        print("-" * 60)

        # DB 커넥션 풀 경고
        print("⚠️  주의: 현재 DB 커넥션 풀 설정")
        print("   - pool_size: 2")
        print("   - max_overflow: 2")
        print("   - 총 최대 커넥션: 4개")
        print(f"   - 동시 요청 수: {num_requests}")
        if num_requests > 4:
            print("   ⚠️  커넥션 풀 병목이 발생할 수 있습니다!")
        print("-" * 60)

        # 동시 요청 시작
        print(f"{num_requests}개의 동시 요청을 시작합니다...")
        start_time = time.time()

        tasks = [
            simulate_votes(client, match_id, i + 1)
            for i in range(num_requests)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)
        total_elapsed = time.time() - start_time

        # 결과 분석
        successful = sum(1 for r in results if isinstance(r, dict) and r.get("success"))
        failed = num_requests - successful

        print("-" * 60)
        print(f"테스트 완료! 총 소요 시간: {total_elapsed:.2f}초")
        print(f"성공: {successful}/{num_requests}")
        print(f"실패: {failed}/{num_requests}")

        # 응답 시간 통계
        if successful > 0:
            elapsed_times = [
                r["elapsed_time"]
                for r in results
                if isinstance(r, dict) and r.get("success")
            ]
            avg_time = sum(elapsed_times) / len(elapsed_times)
            max_time = max(elapsed_times)
            min_time = min(elapsed_times)

            print(f"\n응답 시간 통계:")
            print(f"  평균: {avg_time:.2f}초")
            print(f"  최대: {max_time:.2f}초")
            print(f"  최소: {min_time:.2f}초")

            # 처리량 계산
            throughput = successful / total_elapsed
            print(f"  처리량: {throughput:.2f} requests/second")

        if failed > 0:
            print("\n실패한 요청들:")
            for r in results:
                if isinstance(r, dict) and not r.get("success"):
                    print(f"  Request {r.get('request_index')}: {r.get('response')}")

        # 최종 경기 상태 확인
        final_match = await client.get(f"/tournaments/matches/{match_id}")
        if final_match.status_code == 200:
            final_data = final_match.json()
            print(f"\n최종 경기 상태: {final_data.get('status')}")
            print(f"최종 투표 결과:")
            print(f"  Team 1 득표: {final_data.get('vote_count_team1')}")
            print(f"  Team 2 득표: {final_data.get('vote_count_team2')}")

            # 시뮬레이션된 총 투표 수 계산
            total_simulated = sum(
                r.get("response", {}).get("simulated_count", 0)
                for r in results
                if isinstance(r, dict) and r.get("success") and isinstance(r.get("response"), dict)
            )
            print(f"\n시뮬레이션된 총 투표 수: {total_simulated}")

        # DB 커넥션 풀 병목 진단
        if failed > 0 and num_requests > 4:
            print("\n🔍 DB 커넥션 풀 병목 진단:")
            print("   실패한 요청이 많다면 커넥션 풀 부족일 가능성이 높습니다.")
            print("   제안: 환경 변수로 조정")
            print("     export DB_POOL_SIZE=20")
            print("     export DB_MAX_OVERFLOW=30")


if __name__ == "__main__":
    asyncio.run(main())
