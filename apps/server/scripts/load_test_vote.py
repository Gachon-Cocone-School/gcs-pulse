"""
90명 동시 투표 부하 테스트
- 16강 시뮬레이션 세션의 WB R1 M1 (match_id=789, 1팀 vs 16팀) 을 open으로 리셋
- sim_s 유저 90명이 10초 안에 랜덤 시각에 투표
- p50/p95/p99 레이턴시 및 성공률 출력

실행:
    python scripts/load_test_vote.py [--url http://localhost:8000] [--match-id 789] [--voters 90] [--spread 10]
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import random
import statistics
import time
from dataclasses import dataclass, field

import httpx
import itsdangerous
import psycopg2

# ── 설정 ──────────────────────────────────────────────────────────────────────
DEV_DB = "postgresql://postgres.lhhyvrpznoizwhdkqdbp:0JHq59mtNLs39W66@aws-1-ap-northeast-2.pooler.supabase.com:5432/postgres"
SECRET_KEY = "1609ba2b6fbd9d3ab2758062b484c59754e428df9c0672b7e4b9113dc36bf3bf"
CSRF_TOKEN = "loadtest_csrf_token_fixed"
SESSION_ID = 16
# ──────────────────────────────────────────────────────────────────────────────


def make_session_cookie(email: str, name: str) -> str:
    """Starlette SessionMiddleware 형식의 서명된 세션 쿠키 생성"""
    signer = itsdangerous.TimestampSigner(SECRET_KEY)
    session_data = {
        "user": {
            "email": email,
            "name": name,
            "picture": "",
            "email_verified": True,
        },
        "csrf_token": CSRF_TOKEN,
    }
    data = base64.b64encode(json.dumps(session_data).encode("utf-8"))
    return signer.sign(data).decode("utf-8")


def reset_match(match_id: int) -> tuple[int, int]:
    """DB에서 경기를 open 상태로 리셋하고 (team1_id, team2_id) 반환"""
    conn = psycopg2.connect(DEV_DB)
    try:
        cur = conn.cursor()
        # 기존 투표 삭제
        cur.execute("DELETE FROM tournament_votes WHERE match_id = %s", (match_id,))
        # 경기 리셋
        cur.execute(
            """
            UPDATE tournament_matches
            SET status = 'open',
                winner_team_id = NULL,
                opened_at = NOW()
            WHERE id = %s
            RETURNING team1_id, team2_id, bracket_type, round_no, match_no
            """,
            (match_id,),
        )
        row = cur.fetchone()
        conn.commit()
        team1_id, team2_id, btype, rno, mno = row
        print(f"[reset] match {match_id} ({btype} R{rno}.M{mno}) → open  team1={team1_id} team2={team2_id}")
        return int(team1_id), int(team2_id)
    finally:
        conn.close()


def load_sim_users(limit: int) -> list[tuple[int, str, str]]:
    """sim_s 유저 목록 (user_id, email, name) 반환"""
    conn = psycopg2.connect(DEV_DB)
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, name FROM users WHERE email LIKE 'sim_s%%@gachon.ac.kr' ORDER BY id LIMIT %s",
            (limit,),
        )
        rows = cur.fetchall()
        return [(int(r[0]), str(r[1]), str(r[2])) for r in rows]
    finally:
        conn.close()


@dataclass
class VoteResult:
    user_id: int
    email: str
    status_code: int
    latency_ms: float
    error: str = ""


async def vote(
    client: httpx.AsyncClient,
    base_url: str,
    match_id: int,
    user_id: int,
    email: str,
    name: str,
    selected_team_id: int,
    delay: float,
) -> VoteResult:
    await asyncio.sleep(delay)
    cookie = make_session_cookie(email, name)
    t0 = time.perf_counter()
    try:
        resp = await client.post(
            f"{base_url}/tournaments/matches/{match_id}/vote",
            json={"selected_team_id": selected_team_id},
            headers={
                "x-csrf-token": CSRF_TOKEN,
                "Content-Type": "application/json",
            },
            cookies={"session": cookie},
            timeout=30.0,
        )
        latency_ms = (time.perf_counter() - t0) * 1000
        error = "" if resp.status_code == 200 else resp.text[:120]
        return VoteResult(user_id, email, resp.status_code, latency_ms, error)
    except Exception as e:
        latency_ms = (time.perf_counter() - t0) * 1000
        return VoteResult(user_id, email, 0, latency_ms, str(e)[:120])


def print_summary(results: list[VoteResult], spread_s: float) -> None:
    ok = [r for r in results if r.status_code == 200]
    fail = [r for r in results if r.status_code != 200]
    latencies = [r.latency_ms for r in results]
    latencies_sorted = sorted(latencies)

    def pct(p: float) -> float:
        idx = max(0, int(len(latencies_sorted) * p / 100) - 1)
        return latencies_sorted[idx]

    print("\n" + "=" * 52)
    print(f"  총 요청: {len(results)}  ✓ 성공: {len(ok)}  ✗ 실패: {len(fail)}")
    print(f"  투표 분산 범위: {spread_s}초")
    print("-" * 52)
    print(f"  평균 레이턴시  : {statistics.mean(latencies):.1f} ms")
    print(f"  p50            : {pct(50):.1f} ms")
    print(f"  p95            : {pct(95):.1f} ms")
    print(f"  p99            : {pct(99):.1f} ms")
    print(f"  최대           : {max(latencies):.1f} ms")
    print("-" * 52)

    if fail:
        print("  실패 목록 (최대 10건):")
        for r in fail[:10]:
            print(f"    [{r.status_code}] {r.email}  {r.error}")
    print("=" * 52)


async def run(base_url: str, match_id: int, n_voters: int, spread_s: float) -> None:
    team1_id, team2_id = reset_match(match_id)
    users = load_sim_users(n_voters)
    if len(users) < n_voters:
        print(f"[warn] sim 유저 {len(users)}명만 조회됨 (요청 {n_voters}명)")

    rng = random.Random(42)
    tasks = []
    async with httpx.AsyncClient(follow_redirects=False) as client:
        for i, (uid, email, name) in enumerate(users):
            # 팀은 번갈아 선택 (두 팀에 고르게 분산)
            selected = team1_id if i % 2 == 0 else team2_id
            delay = rng.uniform(0, spread_s)
            tasks.append(vote(client, base_url, match_id, uid, email, name, selected, delay))

        print(f"[start] {len(tasks)}명 투표 시작 ({spread_s}초 범위 내 랜덤 분산) → {base_url}")
        wall_t0 = time.perf_counter()
        results: list[VoteResult] = await asyncio.gather(*tasks)
        wall_elapsed = time.perf_counter() - wall_t0
        print(f"[done]  경과 {wall_elapsed:.2f}초")

    print_summary(results, spread_s)


def main() -> None:
    parser = argparse.ArgumentParser(description="토너먼트 투표 부하 테스트")
    parser.add_argument("--url", default="http://localhost:8000", help="API base URL")
    parser.add_argument("--match-id", type=int, default=789, help="대상 match_id")
    parser.add_argument("--voters", type=int, default=90, help="동시 투표자 수")
    parser.add_argument("--spread", type=float, default=10.0, help="투표 분산 시간(초)")
    args = parser.parse_args()
    asyncio.run(run(args.url, args.match_id, args.voters, args.spread))


if __name__ == "__main__":
    main()
