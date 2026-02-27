from __future__ import annotations

import json
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.models import DailySnippet, Team, User, WeeklySnippet


def _parse_total_score(feedback: Optional[str]) -> float:
    if not feedback:
        return 0.0
    try:
        parsed = json.loads(feedback)
    except (TypeError, ValueError, json.JSONDecodeError):
        return 0.0

    raw_score = parsed.get("total_score")
    if raw_score is None:
        return 0.0

    try:
        return float(raw_score)
    except (TypeError, ValueError):
        return 0.0


def apply_competition_ranks(items: list[dict]) -> list[dict]:
    ranked_items = sorted(items, key=lambda item: (-item["score"], item["participant_name"], item["participant_id"]))
    previous_score: Optional[float] = None
    previous_rank = 0
    for index, item in enumerate(ranked_items, start=1):
        if previous_score is not None and item["score"] == previous_score:
            item["rank"] = previous_rank
        else:
            item["rank"] = index
            previous_rank = index
            previous_score = item["score"]
    return ranked_items


async def build_individual_leaderboard(
    db: AsyncSession,
    league_type: str,
    period: str,
    target_key: date,
) -> list[dict]:
    result = await db.execute(
        select(User)
        .filter(User.team_id.is_(None), User.league_type == league_type)
        .order_by(User.id.asc())
    )
    users = list(result.scalars().all())

    if not users:
        return []

    user_ids = [user.id for user in users]

    snippet_map: dict[int, float] = {}
    if period == "daily":
        snippet_result = await db.execute(
            select(DailySnippet)
            .filter(DailySnippet.user_id.in_(user_ids), DailySnippet.date == target_key)
        )
        for snippet in snippet_result.scalars().all():
            snippet_map[snippet.user_id] = _parse_total_score(snippet.feedback)
    else:
        snippet_result = await db.execute(
            select(WeeklySnippet)
            .filter(WeeklySnippet.user_id.in_(user_ids), WeeklySnippet.week == target_key)
        )
        for snippet in snippet_result.scalars().all():
            snippet_map[snippet.user_id] = _parse_total_score(snippet.feedback)

    items: list[dict] = []
    for user in users:
        items.append(
            {
                "rank": 0,
                "score": float(snippet_map.get(user.id, 0.0)),
                "participant_type": "individual",
                "participant_id": user.id,
                "participant_name": user.name or user.email,
            }
        )

    return apply_competition_ranks(items)


async def build_team_leaderboard(
    db: AsyncSession,
    league_type: str,
    period: str,
    target_key: date,
) -> list[dict]:
    teams_result = await db.execute(
        select(Team)
        .options(selectinload(Team.members))
        .filter(Team.league_type == league_type)
        .order_by(Team.id.asc())
    )
    teams = list(teams_result.scalars().all())

    if not teams:
        return []

    all_member_ids: list[int] = []
    for team in teams:
        all_member_ids.extend(member.id for member in team.members)

    score_map: dict[int, float] = {}
    submitted_member_ids: set[int] = set()
    if all_member_ids:
        if period == "daily":
            snippet_result = await db.execute(
                select(DailySnippet)
                .filter(DailySnippet.user_id.in_(all_member_ids), DailySnippet.date == target_key)
            )
            snippets = list(snippet_result.scalars().all())
        else:
            snippet_result = await db.execute(
                select(WeeklySnippet)
                .filter(WeeklySnippet.user_id.in_(all_member_ids), WeeklySnippet.week == target_key)
            )
            snippets = list(snippet_result.scalars().all())

        for snippet in snippets:
            score_map[snippet.user_id] = _parse_total_score(snippet.feedback)
            submitted_member_ids.add(snippet.user_id)

    items: list[dict] = []
    for team in teams:
        members = list(team.members)
        member_count = len(members)
        if member_count == 0:
            average_score = 0.0
            submitted_count = 0
        else:
            total_score = 0.0
            submitted_count = 0
            for member in members:
                total_score += float(score_map.get(member.id, 0.0))
                if member.id in submitted_member_ids:
                    submitted_count += 1
            average_score = total_score / member_count

        items.append(
            {
                "rank": 0,
                "score": float(average_score),
                "participant_type": "team",
                "participant_id": team.id,
                "participant_name": team.name,
                "member_count": member_count,
                "submitted_count": submitted_count,
            }
        )

    return apply_competition_ranks(items)
