from __future__ import annotations

import json
import logging
import math
import re
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app import crud_tournaments as tournament_crud
from app.core.config import settings
from app.database import get_db
from app.dependencies import require_professor_or_admin_role, verify_csrf
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.lib.notification_runtime import registry as notification_registry
from app.models import TournamentMatch, User

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["tournaments"],
    dependencies=[Depends(verify_csrf)],
)

_TEST_COPILOT_TOKEN_MISSING = "No OAuth token available to request Copilot token"


async def _get_logged_in_user_or_401(request: Request, db: AsyncSession) -> User:
    email = (request.session.get("user") or {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = await crud.get_user_by_email_basic(db, str(email).strip().lower())
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def _get_professor_or_403(request: Request, db: AsyncSession) -> User:
    viewer = await _get_logged_in_user_or_401(request, db)
    require_professor_or_admin_role(viewer)
    return viewer


async def _get_professor_session_or_404(
    db: AsyncSession,
    *,
    session_id: int,
    professor_user_id: int,
):
    session = await tournament_crud.get_session_by_id_and_professor(
        db,
        session_id=session_id,
        professor_user_id=professor_user_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Tournament session not found")
    return session


def _normalize_name(name: str) -> str:
    return "".join(str(name or "").strip().lower().split())


def _build_tournament_match_status_event_payload(
    *,
    match_id: int,
    session_id: int,
    session_is_open: bool,
    match_status: str,
    updated_at: str,
) -> dict[str, Any]:
    return {
        "match_id": int(match_id),
        "session_id": int(session_id),
        "session_is_open": bool(session_is_open),
        "match_status": str(match_status),
        "updated_at": updated_at,
    }


async def _broadcast_tournament_match_status_event(
    *,
    user_ids: set[int],
    payload: dict[str, Any],
) -> None:
    for user_id in user_ids:
        await notification_registry.send_to_user(
            int(user_id),
            {
                "event": "tournament_match_status",
                "data": json.dumps(payload, ensure_ascii=False),
            },
        )


async def _list_session_voter_user_ids(db: AsyncSession, *, session_id: int) -> set[int]:
    rows = await tournament_crud.list_session_teams(db, session_id=session_id)
    return {
        int(member.student_user_id)
        for _, member, _ in rows
        if bool(member.can_attend_vote)
    }


async def _list_student_users(db: AsyncSession) -> list[User]:
    students: list[User] = []
    offset = 0
    limit = 500

    while True:
        rows, _ = await crud.list_students(db, limit=limit, offset=offset)
        batch = [user for user, _ in rows]
        if not batch:
            break
        students.extend(batch)
        offset += len(batch)

    return students


async def _parse_team_text_with_copilot(
    *,
    raw_text: str,
    copilot: CopilotClient,
) -> list[dict[str, Any]]:
    system_prompt = (
        "You are a parser for tournament team roster text. "
        "Return strict JSON only with this shape: "
        '{"teams":[{"team_name":"A팀","members":[{"name":"홍길동","email_hint":null,"can_attend_vote":true}]}]}. '
        "Do not include markdown or extra keys. "
        "If team name is missing, infer sequential names like team-1, team-2."
    )
    user_prompt = f"Input:\n{raw_text}"

    try:
        response = await copilot.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            request_meta={"event": "tournaments.parse_members"},
        )
        content = (
            (((response.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
        ).strip()

        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)
        teams = parsed.get("teams") if isinstance(parsed, dict) else None
        if not isinstance(teams, list):
            raise ValueError("Invalid teams payload")
        return teams
    except Exception as exc:
        if settings.ENVIRONMENT == "test" and _TEST_COPILOT_TOKEN_MISSING in str(exc):
            logger.warning("Using fallback parser in test environment due to missing Copilot token")
            return _parse_team_text_fallback(raw_text)
        logger.exception("Failed to parse tournament teams via Copilot")
        raise HTTPException(status_code=502, detail="Failed to parse tournament teams") from exc


async def _parse_format_text_with_copilot(
    *,
    format_text: str,
    copilot: CopilotClient,
) -> dict[str, Any]:
    system_prompt = (
        "You are a parser for tournament format text. "
        "Return strict JSON only with this shape: "
        '{"match_size":2,"bracket_size":32,"repechage":{"enabled":false,"style":null}}. '
        "Do not include markdown or extra keys. "
        "If text includes repechage(패자부활전, 유도), set repechage.enabled true and style olympic_judo."
    )
    user_prompt = f"Input:\n{format_text}"

    try:
        response = await copilot.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            request_meta={"event": "tournaments.parse_format"},
        )
        content = (
            (((response.get("choices") or [{}])[0]).get("message") or {}).get("content") or ""
        ).strip()

        if content.startswith("```"):
            content = re.sub(r"^```(?:json)?\s*", "", content)
            content = re.sub(r"\s*```$", "", content)

        parsed = json.loads(content)
        if not isinstance(parsed, dict):
            raise ValueError("Invalid format payload")
        return parsed
    except Exception as exc:
        if settings.ENVIRONMENT == "test" and _TEST_COPILOT_TOKEN_MISSING in str(exc):
            logger.warning("Using fallback format parser in test environment due to missing Copilot token")
            return _parse_format_text_fallback(format_text)
        logger.exception("Failed to parse tournament format via Copilot")
        raise HTTPException(status_code=502, detail="Failed to parse tournament format") from exc


def _parse_team_text_fallback(raw_text: str) -> list[dict[str, Any]]:
    segments = [segment.strip() for segment in re.split(r"\r?\n|;", raw_text) if segment.strip()]
    teams: list[dict[str, Any]] = []

    for idx, segment in enumerate(segments, start=1):
        if ":" in segment:
            label_part, members_part = segment.split(":", 1)
            team_name = label_part.strip() or f"team-{idx}"
            members_text = members_part
        else:
            team_name = f"team-{idx}"
            members_text = segment

        names = [name.strip() for name in re.split(r"[,\n]+", members_text) if name.strip()]
        teams.append(
            {
                "team_name": team_name,
                "members": [
                    {"name": name, "email_hint": None, "can_attend_vote": True}
                    for name in names
                ],
            }
        )

    return teams


def _parse_format_text_fallback(format_text: str) -> dict[str, Any]:
    match = re.search(r"(\d+)\s*자대결\s*(\d+)\s*강", format_text)
    if match is None:
        raise HTTPException(status_code=422, detail="Tournament format text is not recognized")

    match_size = int(match.group(1))
    bracket_size = int(match.group(2))
    lowered = format_text.lower()
    has_repechage = ("패자부활전" in format_text) or ("유도" in format_text) or ("repechage" in lowered)

    return {
        "match_size": match_size,
        "bracket_size": bracket_size,
        "repechage": {
            "enabled": has_repechage,
            "style": "olympic_judo" if has_repechage else None,
        },
    }


def _normalize_format_json(raw: dict[str, Any]) -> dict[str, Any]:
    match_size = int(raw.get("match_size") or 0)
    bracket_size = int(raw.get("bracket_size") or 0)

    if match_size <= 1:
        raise HTTPException(status_code=422, detail="match_size must be greater than 1")
    if bracket_size <= 1:
        raise HTTPException(status_code=422, detail="bracket_size must be greater than 1")
    if match_size != 2:
        raise HTTPException(status_code=422, detail="Only 2-player match format is currently supported")
    if bracket_size & (bracket_size - 1):
        raise HTTPException(status_code=422, detail="bracket_size must be a power of 2")

    repechage_raw = raw.get("repechage")
    repechage_enabled = False
    repechage_style: str | None = None
    if isinstance(repechage_raw, dict):
        repechage_enabled = bool(repechage_raw.get("enabled"))
        style_raw = repechage_raw.get("style")
        repechage_style = str(style_raw).strip() if style_raw else None
    elif isinstance(repechage_raw, bool):
        repechage_enabled = repechage_raw

    return {
        "match_size": match_size,
        "bracket_size": bracket_size,
        "repechage": {
            "enabled": repechage_enabled,
            "style": repechage_style,
        },
    }


def _map_parsed_teams_to_students(
    *,
    parsed_teams: list[dict[str, Any]],
    students: list[User],
) -> tuple[dict[str, list[schemas.TournamentParsePreviewMember]], list[schemas.TournamentParseUnresolvedItem]]:
    students_by_name: dict[str, list[User]] = defaultdict(list)
    normalized_students: list[tuple[str, User]] = []
    for student in students:
        key = _normalize_name(student.name or "")
        if key:
            students_by_name[key].append(student)
            normalized_students.append((key, student))

    def _to_candidate_item(student: User) -> schemas.TournamentParseCandidateItem:
        return schemas.TournamentParseCandidateItem(
            student_user_id=student.id,
            student_name=student.name or student.email,
            student_email=student.email,
        )

    teams_map: dict[str, list[schemas.TournamentParsePreviewMember]] = defaultdict(list)
    unresolved: list[schemas.TournamentParseUnresolvedItem] = []
    assigned_team_by_student: dict[int, str] = {}
    added_member_pairs: set[tuple[str, int]] = set()

    for index, team in enumerate(parsed_teams, start=1):
        team_name = str(team.get("team_name") or f"team-{index}").strip() or f"team-{index}"
        raw_members = team.get("members")
        members = raw_members if isinstance(raw_members, list) else []

        for member in members:
            if not isinstance(member, dict):
                continue

            raw_name = str(member.get("name") or "").strip()
            can_attend_vote = bool(member.get("can_attend_vote", True))

            if not raw_name:
                continue

            candidate: User | None = None
            normalized_name = _normalize_name(raw_name)
            exact_matched = students_by_name.get(normalized_name, []) if normalized_name else []

            if len(exact_matched) == 1:
                candidate = exact_matched[0]
            else:
                like_candidates: list[User] = []
                if normalized_name:
                    for student_name, student in normalized_students:
                        if normalized_name in student_name or student_name in normalized_name:
                            like_candidates.append(student)

                unique_like_candidates = list({student.id: student for student in like_candidates}.values())
                if len(unique_like_candidates) == 1:
                    candidate = unique_like_candidates[0]
                elif len(unique_like_candidates) >= 2:
                    unresolved.append(
                        schemas.TournamentParseUnresolvedItem(
                            team_name=team_name,
                            raw_name=raw_name,
                            reason="ambiguous_name",
                            candidates=[_to_candidate_item(student) for student in unique_like_candidates],
                        )
                    )
                    continue
                else:
                    unresolved.append(
                        schemas.TournamentParseUnresolvedItem(
                            team_name=team_name,
                            raw_name=raw_name,
                            reason="name_not_found",
                            candidates=[],
                        )
                    )
                    continue

            if candidate is None:
                unresolved.append(
                    schemas.TournamentParseUnresolvedItem(
                        team_name=team_name,
                        raw_name=raw_name,
                        reason="name_not_found",
                        candidates=[],
                    )
                )
                continue

            existing_team_name = assigned_team_by_student.get(candidate.id)
            if existing_team_name is not None and existing_team_name != team_name:
                unresolved.append(
                    schemas.TournamentParseUnresolvedItem(
                        team_name=team_name,
                        raw_name=raw_name,
                        reason="student_in_multiple_teams",
                        candidates=[_to_candidate_item(candidate)],
                    )
                )
                continue

            assigned_team_by_student[candidate.id] = team_name

            member_pair = (team_name, candidate.id)
            if member_pair in added_member_pairs:
                continue
            added_member_pairs.add(member_pair)

            teams_map[team_name].append(
                schemas.TournamentParsePreviewMember(
                    team_name=team_name,
                    raw_name=raw_name,
                    student_user_id=candidate.id,
                    student_name=candidate.name or candidate.email,
                    student_email=candidate.email,
                    can_attend_vote=can_attend_vote,
                )
            )

    return dict(teams_map), unresolved


def _serialize_teams(
    rows: list[tuple[Any, Any, User]],
) -> list[schemas.TournamentTeamItem]:
    grouped: dict[str, list[schemas.TournamentTeamMemberItem]] = defaultdict(list)
    for team, member, user in rows:
        grouped[team.name].append(
            schemas.TournamentTeamMemberItem(
                student_user_id=user.id,
                student_name=user.name or user.email,
                student_email=user.email,
                can_attend_vote=bool(member.can_attend_vote),
            )
        )

    return [
        schemas.TournamentTeamItem(team_name=team_name, members=members)
        for team_name, members in grouped.items()
    ]


def _serialize_match_row(
    row: tuple[Any, Any, Any, Any, int, int],
    *,
    session_is_open: bool | None = None,
) -> schemas.TournamentMatchItem:
    match, team1, team2, winner, vote_count_team1, vote_count_team2 = row
    is_open_match = str(match.status) == "open"
    return schemas.TournamentMatchItem(
        id=match.id,
        session_id=match.session_id,
        bracket_type=match.bracket_type,
        round_no=match.round_no,
        match_no=match.match_no,
        status=match.status,
        is_bye=match.is_bye,
        session_is_open=session_is_open,
        team1_id=match.team1_id,
        team1_name=team1.name if team1 else None,
        team2_id=match.team2_id,
        team2_name=team2.name if team2 else None,
        winner_team_id=match.winner_team_id,
        winner_team_name=winner.name if winner else None,
        next_match_id=match.next_match_id,
        loser_next_match_id=match.loser_next_match_id,
        vote_count_team1=None if is_open_match else int(vote_count_team1 or 0),
        vote_count_team2=None if is_open_match else int(vote_count_team2 or 0),
        created_at=match.created_at,
        updated_at=match.updated_at,
    )


def _build_single_elim_payload(team_ids: list[int], bracket_size: int) -> list[dict[str, Any]]:
    """싱글 엘리미네이션 대진 생성."""
    slots = team_ids + [None] * (bracket_size - len(team_ids))
    rounds = int(math.log2(bracket_size))
    payload: list[dict[str, Any]] = []
    indices_by_round: dict[int, list[int]] = defaultdict(list)

    for round_no in range(1, rounds + 1):
        match_count = bracket_size // (2**round_no)
        for match_no in range(1, match_count + 1):
            item: dict[str, Any] = {
                "bracket_type": "winners",
                "round_no": round_no,
                "match_no": match_no,
                "status": "pending",
                "is_bye": False,
                "team1_id": None,
                "team2_id": None,
                "winner_team_id": None,
                "next_index": None,
                "loser_next_index": None,
            }
            if round_no == 1:
                slot_index = (match_no - 1) * 2
                team1_id = slots[slot_index]
                team2_id = slots[slot_index + 1]
                item["team1_id"] = team1_id
                item["team2_id"] = team2_id
                is_bye = (team1_id is None) != (team2_id is None)
                item["is_bye"] = is_bye
                if is_bye:
                    item["status"] = "closed"
                    item["winner_team_id"] = team1_id or team2_id
            payload.append(item)
            indices_by_round[round_no].append(len(payload) - 1)

    for round_no in range(1, rounds):
        cur = indices_by_round[round_no]
        nxt = indices_by_round[round_no + 1]
        for i, ci in enumerate(cur):
            payload[ci]["next_index"] = nxt[i // 2]

    return payload


def _build_double_elim_payload(team_ids: list[int], bracket_size: int) -> list[dict[str, Any]]:
    """더블 엘리미네이션: 승자 조(WB) + 패자 조(LB) 대진 생성.

    WB: log2(bracket_size) 라운드
    LB 구조 (bracket_size별):
      8강  : LB R1(WB R1) + R2(WB R2)              → R2 승자=공동 3위
      16강 : LB R1(WB R1) + R2(WB R2) + R3(순수)   → R3 승자=공동 5위, WB 4강 패자=공동 3위
      32강 : R1+R2+R3(순수)+R4(WB R3)+R5(순수)     → R5 승자=공동 5위, WB 4강 패자=공동 3위

    일반 규칙:
      WB 주입 라운드 = max(2, wb_rounds - 2)  (8강은 WB 4강까지 주입, 16강 이상은 4강 제외)
      주입 사이사이에 순수 LB 라운드 삽입 (리매치 방지 크로스 배정)
      bracket_size >= 16이면 마지막에 패자 결승(순수 LB) 추가 → 승자 공동 5위
    bracket_size >= 8 이어야 한다.
    """
    wb_rounds = int(math.log2(bracket_size))
    # WB에서 LB로 패자를 주입하는 라운드 수 (R1~R(wb_inject_count))
    # 8강: 2(R1+R2 = 4강까지), 16강: 2(R1+R2), 32강: 3(R1+R2+R3)
    wb_inject_count = max(2, wb_rounds - 2)

    slots = team_ids + [None] * (bracket_size - len(team_ids))
    payload: list[dict[str, Any]] = []
    by_br: dict[tuple[str, int], list[int]] = defaultdict(list)

    def new_match(bt: str, rn: int, mn: int, t1: Any = None, t2: Any = None,
                  is_bye: bool = False, winner: Any = None) -> int:
        item: dict[str, Any] = {
            "bracket_type": bt,
            "round_no": rn,
            "match_no": mn,
            "status": "closed" if is_bye else "pending",
            "is_bye": is_bye,
            "team1_id": t1,
            "team2_id": t2,
            "winner_team_id": winner,
            "next_index": None,
            "loser_next_index": None,
        }
        idx = len(payload)
        payload.append(item)
        by_br[(bt, rn)].append(idx)
        return idx

    # ── WB 경기 생성 ──────────────────────────────────────────────────────────
    for mn in range(1, bracket_size // 2 + 1):
        si = (mn - 1) * 2
        t1, t2 = slots[si], slots[si + 1]
        is_bye = (t1 is None) != (t2 is None)
        new_match("winners", 1, mn, t1, t2, is_bye=is_bye, winner=(t1 or t2) if is_bye else None)

    for r in range(2, wb_rounds + 1):
        cnt = bracket_size // (2 ** r)
        for mn in range(1, cnt + 1):
            new_match("winners", r, mn)

    # ── LB 경기 생성 ──────────────────────────────────────────────────────────
    lb_r1_count = bracket_size // 4
    # LB R1 (WB R1 패자)
    for mn in range(1, lb_r1_count + 1):
        new_match("losers", 1, mn)
    # LB R2 (LB R1 승자 + WB R2 패자 주입)
    for mn in range(1, lb_r1_count + 1):
        new_match("losers", 2, mn)

    # LB R3 이후: 추가 WB 주입 라운드마다 [순수 LB → WB 주입 LB] 쌍 생성
    lb_round = 3
    current_lb_count = lb_r1_count
    for _ in range(wb_inject_count - 2):
        current_lb_count //= 2
        for mn in range(1, current_lb_count + 1):
            new_match("losers", lb_round, mn)       # 순수 LB 라운드
        lb_round += 1
        for mn in range(1, current_lb_count + 1):
            new_match("losers", lb_round, mn)       # WB 주입 LB 라운드
        lb_round += 1

    # 패자 결승 (순수 LB, bracket_size >= 16만): 승자 공동 5위
    lb_final_round: int | None = None
    if bracket_size >= 16:
        final_count = current_lb_count // 2
        for mn in range(1, final_count + 1):
            new_match("losers", lb_round, mn)
        lb_final_round = lb_round

    # ── WB 연결 ───────────────────────────────────────────────────────────────
    for r in range(1, wb_rounds):
        cur = by_br[("winners", r)]
        nxt = by_br[("winners", r + 1)]
        for i, ci in enumerate(cur):
            payload[ci]["next_index"] = nxt[i // 2]

    # ── LB 연결 ───────────────────────────────────────────────────────────────
    # WB R1 패자 → LB R1 (2경기당 1개)
    for i, ci in enumerate(by_br[("winners", 1)]):
        payload[ci]["loser_next_index"] = by_br[("losers", 1)][i // 2]

    # LB R1 승자 → LB R2 (n//2 크로스 오프셋, team2) — 리매치 방지
    lb_r1 = by_br[("losers", 1)]
    lb_r2 = by_br[("losers", 2)]
    n = len(lb_r1)
    for i, ci in enumerate(lb_r1):
        payload[ci]["next_index"] = lb_r2[(i + n // 2) % n]

    # WB R2 패자 → LB R2 (1:1, team1)
    for i, ci in enumerate(by_br[("winners", 2)]):
        payload[ci]["loser_next_index"] = by_br[("losers", 2)][i]

    # LB R2 이후 체인: 주입 라운드 → 순수 → 다음 주입 → ...
    cur_inj_round = 2   # 현재 처리 완료된 마지막 주입 LB 라운드
    lb_round_ptr = 3
    for wb_r in range(3, wb_inject_count + 1):
        pure_r = by_br[("losers", lb_round_ptr)]
        next_inj_r = by_br[("losers", lb_round_ptr + 1)]

        # 주입 라운드 승자 → 순수 라운드 (2경기당 1개)
        for i, ci in enumerate(by_br[("losers", cur_inj_round)]):
            payload[ci]["next_index"] = pure_r[i // 2]

        # 순수 라운드 승자 → 다음 주입 라운드 (크로스 오프셋, team2)
        n = len(pure_r)
        for i, ci in enumerate(pure_r):
            payload[ci]["next_index"] = next_inj_r[(i + n // 2) % n]

        # WB R(wb_r) 패자 → 다음 주입 라운드 (1:1, team1)
        for i, ci in enumerate(by_br[("winners", wb_r)]):
            payload[ci]["loser_next_index"] = next_inj_r[i]

        cur_inj_round = lb_round_ptr + 1
        lb_round_ptr += 2

    # 마지막 주입 라운드 → 패자 결승 (bracket_size >= 16)
    if lb_final_round is not None:
        for i, ci in enumerate(by_br[("losers", cur_inj_round)]):
            payload[ci]["next_index"] = by_br[("losers", lb_final_round)][i // 2]

    # WB 4강(R(wb_rounds-1)) 패자는 공동 3위 자동 확정 (LB 연결 없음)
    # 패자 결승 승자는 공동 5위 확정 (next_match 없음)

    return payload


def _build_matches_payload(team_ids: list[int], format_json: dict[str, Any]) -> list[dict[str, Any]]:
    bracket_size = int(format_json["bracket_size"])
    match_size = int(format_json["match_size"])
    if match_size != 2:
        raise HTTPException(status_code=422, detail="Only 2-player match format is currently supported")
    if len(team_ids) > bracket_size:
        raise HTTPException(status_code=422, detail="Team count exceeds bracket size")

    repechage = format_json.get("repechage") or {}
    if isinstance(repechage, dict) and bool(repechage.get("enabled")):
        if bracket_size < 8:
            raise HTTPException(status_code=422, detail="Double elimination requires bracket_size >= 8")
        return _build_double_elim_payload(team_ids, bracket_size)

    return _build_single_elim_payload(team_ids, bracket_size)


async def _build_session_response(
    db: AsyncSession,
    session: Any,
) -> schemas.TournamentSessionResponse:
    team_rows = await tournament_crud.list_session_teams(db, session_id=session.id)
    return schemas.TournamentSessionResponse(
        id=session.id,
        title=session.title,
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        allow_self_vote=bool(session.allow_self_vote),
        format_text=session.format_text,
        format_json=session.format_json,
        created_at=session.created_at,
        updated_at=session.updated_at,
        teams=_serialize_teams(team_rows),
    )


@router.post("/tournaments/sessions", response_model=schemas.TournamentSessionResponse)
async def create_tournament_session(
    payload: schemas.TournamentSessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await tournament_crud.create_session(
        db,
        title=payload.title,
        professor_user_id=professor.id,
        allow_self_vote=payload.allow_self_vote,
    )
    return schemas.TournamentSessionResponse(
        id=session.id,
        title=session.title,
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        allow_self_vote=bool(session.allow_self_vote),
        format_text=session.format_text,
        format_json=session.format_json,
        created_at=session.created_at,
        updated_at=session.updated_at,
        teams=[],
    )


@router.get("/tournaments/sessions", response_model=schemas.TournamentSessionListResponse)
async def list_tournament_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    rows = await tournament_crud.list_sessions_by_professor(
        db,
        professor_user_id=professor.id,
    )
    return schemas.TournamentSessionListResponse(
        items=[
            schemas.TournamentSessionListItem(
                id=session.id,
                title=session.title,
                is_open=session.is_open,
                created_at=session.created_at,
                updated_at=session.updated_at,
                team_count=team_count,
                match_count=match_count,
            )
            for session, team_count, match_count in rows
        ],
        total=len(rows),
    )


@router.get("/tournaments/sessions/{session_id}", response_model=schemas.TournamentSessionResponse)
async def get_tournament_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    return await _build_session_response(db, session)


@router.patch("/tournaments/sessions/{session_id}", response_model=schemas.TournamentSessionResponse)
async def update_tournament_session(
    session_id: int,
    payload: schemas.TournamentSessionUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    session = await tournament_crud.update_session(
        db,
        session=session,
        title=payload.title,
        allow_self_vote=payload.allow_self_vote,
    )
    return await _build_session_response(db, session)


@router.delete("/tournaments/sessions/{session_id}", response_model=schemas.MessageResponse)
async def delete_tournament_session(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    await tournament_crud.delete_session(db, session=session)
    return schemas.MessageResponse(message="Deleted")


@router.patch("/tournaments/sessions/{session_id}/status", response_model=schemas.TournamentSessionResponse)
async def update_tournament_session_status(
    session_id: int,
    payload: schemas.TournamentSessionStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )
    session = await tournament_crud.update_session_is_open(
        db,
        session=session,
        is_open=payload.is_open,
    )

    session_voter_user_ids = await _list_session_voter_user_ids(db, session_id=session.id)
    match_rows = await tournament_crud.list_matches_with_votes_by_session(db, session_id=session.id)
    for match_row in match_rows:
        match = match_row[0]
        event_payload = _build_tournament_match_status_event_payload(
            match_id=int(match.id),
            session_id=int(session.id),
            session_is_open=bool(session.is_open),
            match_status=str(match.status),
            updated_at=session.updated_at.isoformat(),
        )
        await _broadcast_tournament_match_status_event(
            user_ids=session_voter_user_ids,
            payload=event_payload,
        )

    return await _build_session_response(db, session)


@router.post("/tournaments/members:parse", response_model=schemas.TournamentTeamsParseResponse)
async def parse_tournament_members_draft(
    payload: schemas.TournamentTeamsParseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    await _get_professor_or_403(request, db)
    parsed_teams = await _parse_team_text_with_copilot(raw_text=payload.raw_text, copilot=copilot)
    students = await _list_student_users(db)
    teams, unresolved = _map_parsed_teams_to_students(parsed_teams=parsed_teams, students=students)
    return schemas.TournamentTeamsParseResponse(
        teams=teams,
        unresolved_members=unresolved,
    )


@router.post("/tournaments/sessions/{session_id}/members:parse", response_model=schemas.TournamentTeamsParseResponse)
async def parse_tournament_members(
    session_id: int,
    payload: schemas.TournamentTeamsParseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    professor = await _get_professor_or_403(request, db)
    await _get_professor_session_or_404(db, session_id=session_id, professor_user_id=professor.id)

    parsed_teams = await _parse_team_text_with_copilot(raw_text=payload.raw_text, copilot=copilot)
    students = await _list_student_users(db)
    teams, unresolved = _map_parsed_teams_to_students(parsed_teams=parsed_teams, students=students)
    return schemas.TournamentTeamsParseResponse(
        teams=teams,
        unresolved_members=unresolved,
    )


@router.post("/tournaments/sessions/{session_id}/members:confirm", response_model=schemas.TournamentTeamsConfirmResponse)
async def confirm_tournament_members(
    session_id: int,
    payload: schemas.TournamentTeamsConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    await _get_professor_session_or_404(db, session_id=session_id, professor_user_id=professor.id)

    if payload.unresolved_members:
        raise HTTPException(status_code=400, detail="Unresolved members must be resolved before confirmation")
    if not payload.members:
        raise HTTPException(status_code=400, detail="At least one member is required")

    dedupe_ids: set[int] = set()
    team_payload: dict[str, list[tuple[int, bool]]] = defaultdict(list)

    for member in payload.members:
        if member.student_user_id in dedupe_ids:
            raise HTTPException(status_code=400, detail="Duplicate student in members")
        dedupe_ids.add(member.student_user_id)

        team_name = member.team_name.strip()
        if not team_name:
            raise HTTPException(status_code=400, detail="Team name is required")
        team_payload[team_name].append((member.student_user_id, bool(member.can_attend_vote)))

    await tournament_crud.replace_session_teams(
        db,
        session_id=session_id,
        teams=list(team_payload.items()),
    )

    rows = await tournament_crud.list_session_teams(db, session_id=session_id)
    return schemas.TournamentTeamsConfirmResponse(
        session_id=session_id,
        teams=_serialize_teams(rows),
    )


@router.post("/tournaments/sessions/{session_id}/format:parse", response_model=schemas.TournamentFormatParseResponse)
async def parse_tournament_format(
    session_id: int,
    payload: schemas.TournamentFormatParseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(db, session_id=session_id, professor_user_id=professor.id)

    parsed = await _parse_format_text_with_copilot(format_text=payload.format_text, copilot=copilot)
    try:
        normalized = _normalize_format_json(parsed)
    except HTTPException:
        normalized = _normalize_format_json(_parse_format_text_fallback(payload.format_text))

    session = await tournament_crud.update_session_format(
        db,
        session=session,
        format_text=payload.format_text,
        format_json=normalized,
    )

    return schemas.TournamentFormatParseResponse(
        format_text=session.format_text or payload.format_text,
        format_json=session.format_json or normalized,
    )


@router.post("/tournaments/sessions/{session_id}/matches:generate", response_model=schemas.TournamentBracketResponse)
async def generate_tournament_matches(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(db, session_id=session_id, professor_user_id=professor.id)

    format_json = session.format_json or {}
    if not isinstance(format_json, dict):
        raise HTTPException(status_code=422, detail="Tournament format is not configured")
    normalized_format = _normalize_format_json(format_json)

    teams = await tournament_crud.list_session_teams_without_members(db, session_id=session_id)
    if not teams:
        raise HTTPException(status_code=400, detail="No teams confirmed")

    matches_payload = _build_matches_payload([team.id for team in teams], normalized_format)
    created = await tournament_crud.replace_session_matches(db, session_id=session_id, matches=matches_payload)

    # BYE 경기 winner 자동 진출
    for m in created:
        if m.is_bye and m.winner_team_id is not None:
            await tournament_crud.advance_match_result(db, match_id=int(m.id))

    rows = await tournament_crud.list_matches_with_votes_by_session(db, session_id=session_id)
    grouped = tournament_crud.build_rounds(rows)
    rounds = [
        schemas.TournamentBracketRound(
            bracket_type=bracket_type,
            round_no=round_no,
            matches=[_serialize_match_row(row) for row in grouped[(bracket_type, round_no)]],
        )
        for bracket_type, round_no in sorted(grouped.keys(), key=lambda item: (item[0], item[1]))
    ]

    return schemas.TournamentBracketResponse(
        session_id=session_id,
        title=session.title,
        rounds=rounds,
    )


@router.get("/tournaments/sessions/mine", response_model=schemas.TournamentStudentSessionListResponse)
async def list_my_tournament_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """학생이 팀원으로 등록된 토너먼트 세션 목록을 반환한다."""
    user = await _get_logged_in_user_or_401(request, db)
    rows = await tournament_crud.list_sessions_by_student(db, student_user_id=user.id)
    return schemas.TournamentStudentSessionListResponse(
        items=[
            schemas.TournamentStudentSessionItem(
                id=session.id,
                title=session.title,
                is_open=session.is_open,
                created_at=session.created_at,
                updated_at=session.updated_at,
            )
            for session in rows
        ],
        total=len(rows),
    )


@router.get("/tournaments/sessions/{session_id}/bracket", response_model=schemas.TournamentBracketResponse)
async def get_tournament_bracket(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _get_logged_in_user_or_401(request, db)
    session = await tournament_crud.get_session_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tournament session not found")

    rows = await tournament_crud.list_matches_with_votes_by_session(db, session_id=session_id)
    grouped = tournament_crud.build_rounds(rows)
    rounds = [
        schemas.TournamentBracketRound(
            bracket_type=bracket_type,
            round_no=round_no,
            matches=[_serialize_match_row(row) for row in grouped[(bracket_type, round_no)]],
        )
        for bracket_type, round_no in sorted(grouped.keys(), key=lambda item: (item[0], item[1]))
    ]

    return schemas.TournamentBracketResponse(
        session_id=session_id,
        title=session.title,
        rounds=rounds,
    )


@router.get("/tournaments/matches/{match_id}", response_model=schemas.TournamentMatchItem)
async def get_tournament_match(
    match_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await _get_logged_in_user_or_401(request, db)
    row = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    match = row[0]
    session = await tournament_crud.get_session_by_id(db, int(match.session_id))
    session_is_open = bool(session.is_open) if session is not None else None
    return _serialize_match_row(row, session_is_open=session_is_open)


@router.get("/tournaments/matches/{match_id}/progress", response_model=schemas.TournamentMatchProgressResponse)
async def get_tournament_match_progress(
    match_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)

    row = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    session = await _get_professor_session_or_404(
        db,
        session_id=int(row[0].session_id),
        professor_user_id=professor.id,
    )
    serialized_match = _serialize_match_row(row, session_is_open=bool(session.is_open))

    voter_rows = await tournament_crud.list_match_voter_statuses(
        db,
        match_id=match_id,
        exclude_competing_teams=not bool(session.allow_self_vote),
    )
    voter_statuses = [
        schemas.TournamentMatchVoterStatusItem(
            voter_user_id=voter_user_id,
            voter_name=voter_name,
            has_submitted=has_submitted,
        )
        for voter_user_id, voter_name, has_submitted in voter_rows
    ]
    submitted_count = sum(1 for item in voter_statuses if item.has_submitted)

    return schemas.TournamentMatchProgressResponse(
        match=serialized_match,
        vote_url=f"/tournaments/matches/{match_id}/vote",
        session_is_open=bool(session.is_open),
        allow_self_vote=bool(session.allow_self_vote),
        voter_statuses=voter_statuses,
        submitted_count=submitted_count,
        total_count=len(voter_statuses),
    )


@router.patch("/tournaments/matches/{match_id}/status", response_model=schemas.TournamentMatchItem)
async def update_tournament_match_status(
    match_id: int,
    payload: schemas.TournamentMatchStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)

    match_result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = match_result.scalars().first()
    if match is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    await _get_professor_session_or_404(
        db,
        session_id=match.session_id,
        professor_user_id=professor.id,
    )

    if match.is_bye and payload.status == "open":
        raise HTTPException(status_code=400, detail="Bye match cannot be opened")

    updated_match = await tournament_crud.update_match_status(db, match=match, status=payload.status)
    session = await tournament_crud.get_session_by_id(db, int(updated_match.session_id))
    if session is None:
        raise HTTPException(status_code=404, detail="Tournament session not found")

    row = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    event_payload = _build_tournament_match_status_event_payload(
        match_id=int(updated_match.id),
        session_id=int(updated_match.session_id),
        session_is_open=bool(session.is_open),
        match_status=str(updated_match.status),
        updated_at=updated_match.updated_at.isoformat(),
    )
    await _broadcast_tournament_match_status_event(
        user_ids=await _list_session_voter_user_ids(db, session_id=int(updated_match.session_id)),
        payload=event_payload,
    )

    return _serialize_match_row(row, session_is_open=bool(session.is_open))


@router.patch("/tournaments/matches/{match_id}/winner", response_model=schemas.TournamentMatchItem)
async def update_tournament_match_winner(
    match_id: int,
    payload: schemas.TournamentMatchWinnerUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)

    match_result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = match_result.scalars().first()
    if match is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    await _get_professor_session_or_404(
        db,
        session_id=match.session_id,
        professor_user_id=professor.id,
    )

    if payload.winner_team_id is not None and payload.winner_team_id not in {match.team1_id, match.team2_id}:
        raise HTTPException(status_code=400, detail="Winner must be one of match teams")

    await tournament_crud.update_match_winner(db, match=match, winner_team_id=payload.winner_team_id)

    # 승자/패자 다음 경기로 자동 진출
    if payload.winner_team_id is not None:
        await tournament_crud.advance_match_result(db, match_id=match_id)

    row = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    session = await tournament_crud.get_session_by_id(db, int(match.session_id))
    session_is_open = bool(session.is_open) if session is not None else None

    # 영향받은 경기들에 SSE 브로드캐스트
    voter_ids = await _list_session_voter_user_ids(db, session_id=int(match.session_id))
    for broadcast_match_id in [match_id] + (
        [match.next_match_id] if match.next_match_id else []
    ) + (
        [match.loser_next_match_id] if match.loser_next_match_id else []
    ):
        if broadcast_match_id is None:
            continue
        bm_result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == broadcast_match_id))
        bm = bm_result.scalars().first()
        if bm is None:
            continue
        event_payload = _build_tournament_match_status_event_payload(
            match_id=int(bm.id),
            session_id=int(bm.session_id),
            session_is_open=bool(session_is_open) if session_is_open is not None else False,
            match_status=str(bm.status),
            updated_at=bm.updated_at.isoformat(),
        )
        await _broadcast_tournament_match_status_event(user_ids=voter_ids, payload=event_payload)

    return _serialize_match_row(row, session_is_open=session_is_open)


@router.post("/tournaments/matches/{match_id}/vote", response_model=schemas.TournamentVoteResponse)
async def submit_tournament_vote(
    match_id: int,
    payload: schemas.TournamentVoteSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_logged_in_user_or_401(request, db)

    row = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    serialized_match = _serialize_match_row(row)
    session = await tournament_crud.get_session_by_id(db, serialized_match.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Tournament session not found")

    if not session.is_open:
        raise HTTPException(status_code=409, detail="Session is closed")
    if serialized_match.status != "open":
        raise HTTPException(status_code=409, detail="Match is not open")
    if serialized_match.is_bye:
        raise HTTPException(status_code=409, detail="Bye match does not accept votes")

    valid_team_ids = {serialized_match.team1_id, serialized_match.team2_id}
    if payload.selected_team_id not in valid_team_ids:
        raise HTTPException(status_code=400, detail="Selected team is not in this match")

    if not bool(session.allow_self_vote):
        voter_team = await tournament_crud.get_member_team_in_session(
            db,
            session_id=serialized_match.session_id,
            user_id=user.id,
        )
        if voter_team is not None and voter_team.id in valid_team_ids:
            raise HTTPException(status_code=409, detail="본인 팀 경기에는 투표할 수 없습니다")

    await tournament_crud.upsert_match_vote(
        db,
        match_id=match_id,
        voter_user_id=user.id,
        selected_team_id=payload.selected_team_id,
    )

    refreshed = await tournament_crud.get_match_with_votes(db, match_id=match_id)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Tournament match not found")

    return schemas.TournamentVoteResponse(
        message="Submitted",
        match=_serialize_match_row(refreshed, session_is_open=bool(session.is_open)),
    )
