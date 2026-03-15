from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import (
    TournamentMatch,
    TournamentSession,
    TournamentTeam,
    TournamentTeamMember,
    TournamentVote,
    User,
)


async def create_session(
    db: AsyncSession,
    *,
    title: str,
    professor_user_id: int,
) -> TournamentSession:
    session = TournamentSession(
        title=title,
        professor_user_id=professor_user_id,
        is_open=False,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_id(db: AsyncSession, session_id: int) -> TournamentSession | None:
    result = await db.execute(select(TournamentSession).filter(TournamentSession.id == session_id))
    return result.scalars().first()


async def get_session_by_id_and_professor(
    db: AsyncSession,
    *,
    session_id: int,
    professor_user_id: int,
) -> TournamentSession | None:
    result = await db.execute(
        select(TournamentSession).filter(
            TournamentSession.id == session_id,
            TournamentSession.professor_user_id == professor_user_id,
        )
    )
    return result.scalars().first()


async def list_sessions_by_professor(
    db: AsyncSession,
    *,
    professor_user_id: int,
) -> list[tuple[TournamentSession, int, int]]:
    team_count_subquery = (
        select(
            TournamentTeam.session_id.label("session_id"),
            func.count(TournamentTeam.id).label("team_count"),
        )
        .group_by(TournamentTeam.session_id)
        .subquery()
    )

    match_count_subquery = (
        select(
            TournamentMatch.session_id.label("session_id"),
            func.count(TournamentMatch.id).label("match_count"),
        )
        .group_by(TournamentMatch.session_id)
        .subquery()
    )

    result = await db.execute(
        select(
            TournamentSession,
            func.coalesce(team_count_subquery.c.team_count, 0).label("team_count"),
            func.coalesce(match_count_subquery.c.match_count, 0).label("match_count"),
        )
        .outerjoin(team_count_subquery, team_count_subquery.c.session_id == TournamentSession.id)
        .outerjoin(match_count_subquery, match_count_subquery.c.session_id == TournamentSession.id)
        .filter(TournamentSession.professor_user_id == professor_user_id)
        .order_by(TournamentSession.updated_at.desc(), TournamentSession.id.desc())
    )
    return [
        (session, int(team_count or 0), int(match_count or 0))
        for session, team_count, match_count in result.all()
    ]


async def update_session(
    db: AsyncSession,
    *,
    session: TournamentSession,
    title: str,
) -> TournamentSession:
    session.title = title
    await db.commit()
    await db.refresh(session)
    return session


async def update_session_is_open(
    db: AsyncSession,
    *,
    session: TournamentSession,
    is_open: bool,
) -> TournamentSession:
    session.is_open = is_open
    await db.commit()
    await db.refresh(session)
    return session


async def update_session_format(
    db: AsyncSession,
    *,
    session: TournamentSession,
    format_text: str,
    format_json: dict,
) -> TournamentSession:
    session.format_text = format_text
    session.format_json = format_json
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(
    db: AsyncSession,
    *,
    session: TournamentSession,
) -> None:
    await db.delete(session)
    await db.commit()


async def replace_session_teams(
    db: AsyncSession,
    *,
    session_id: int,
    teams: Sequence[tuple[str, Sequence[tuple[int, bool]]]],
) -> None:
    await db.execute(
        delete(TournamentVote).filter(
            TournamentVote.match_id.in_(
                select(TournamentMatch.id).filter(TournamentMatch.session_id == session_id)
            )
        )
    )
    await db.execute(delete(TournamentMatch).filter(TournamentMatch.session_id == session_id))

    existing_team_ids_result = await db.execute(
        select(TournamentTeam.id).filter(TournamentTeam.session_id == session_id)
    )
    existing_team_ids = [int(row[0]) for row in existing_team_ids_result.all()]
    if existing_team_ids:
        await db.execute(
            delete(TournamentTeamMember).filter(TournamentTeamMember.team_id.in_(existing_team_ids))
        )
    await db.execute(delete(TournamentTeam).filter(TournamentTeam.session_id == session_id))

    for team_name, members in teams:
        team = TournamentTeam(
            session_id=session_id,
            name=team_name,
        )
        db.add(team)
        await db.flush()

        for student_user_id, can_attend_vote in members:
            db.add(
                TournamentTeamMember(
                    team_id=team.id,
                    student_user_id=student_user_id,
                    can_attend_vote=can_attend_vote,
                )
            )

    await db.commit()


async def list_session_teams(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[tuple[TournamentTeam, TournamentTeamMember, User]]:
    result = await db.execute(
        select(TournamentTeam, TournamentTeamMember, User)
        .join(TournamentTeamMember, TournamentTeamMember.team_id == TournamentTeam.id)
        .join(User, User.id == TournamentTeamMember.student_user_id)
        .filter(TournamentTeam.session_id == session_id)
        .order_by(TournamentTeam.name.asc(), User.id.asc())
    )
    return list(result.all())


async def list_session_teams_without_members(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[TournamentTeam]:
    result = await db.execute(
        select(TournamentTeam)
        .filter(TournamentTeam.session_id == session_id)
        .order_by(TournamentTeam.id.asc())
    )
    return list(result.scalars().all())


async def replace_session_matches(
    db: AsyncSession,
    *,
    session_id: int,
    matches: Sequence[dict],
) -> list[TournamentMatch]:
    await db.execute(
        delete(TournamentVote).filter(
            TournamentVote.match_id.in_(
                select(TournamentMatch.id).filter(TournamentMatch.session_id == session_id)
            )
        )
    )
    await db.execute(delete(TournamentMatch).filter(TournamentMatch.session_id == session_id))

    created_matches: list[TournamentMatch] = []
    for item in matches:
        match = TournamentMatch(
            session_id=session_id,
            bracket_type=item["bracket_type"],
            round_no=item["round_no"],
            match_no=item["match_no"],
            status=item["status"],
            is_bye=item["is_bye"],
            team1_id=item.get("team1_id"),
            team2_id=item.get("team2_id"),
            winner_team_id=item.get("winner_team_id"),
        )
        db.add(match)
        created_matches.append(match)

    await db.flush()

    for index, item in enumerate(matches):
        next_index = item.get("next_index")
        if next_index is not None and 0 <= next_index < len(created_matches):
            created_matches[index].next_match_id = created_matches[next_index].id

    await db.commit()
    return created_matches


async def list_matches_with_votes_by_session(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[tuple[TournamentMatch, TournamentTeam | None, TournamentTeam | None, TournamentTeam | None, int, int]]:
    team1 = aliased(TournamentTeam)
    team2 = aliased(TournamentTeam)
    winner = aliased(TournamentTeam)

    vote_counts_subquery = (
        select(
            TournamentVote.match_id.label("match_id"),
            TournamentVote.selected_team_id.label("selected_team_id"),
            func.count(TournamentVote.id).label("vote_count"),
        )
        .group_by(TournamentVote.match_id, TournamentVote.selected_team_id)
        .subquery()
    )

    team1_vote = aliased(vote_counts_subquery)
    team2_vote = aliased(vote_counts_subquery)

    result = await db.execute(
        select(
            TournamentMatch,
            team1,
            team2,
            winner,
            func.coalesce(team1_vote.c.vote_count, 0).label("vote_count_team1"),
            func.coalesce(team2_vote.c.vote_count, 0).label("vote_count_team2"),
        )
        .outerjoin(team1, team1.id == TournamentMatch.team1_id)
        .outerjoin(team2, team2.id == TournamentMatch.team2_id)
        .outerjoin(winner, winner.id == TournamentMatch.winner_team_id)
        .outerjoin(
            team1_vote,
            (team1_vote.c.match_id == TournamentMatch.id)
            & (team1_vote.c.selected_team_id == TournamentMatch.team1_id),
        )
        .outerjoin(
            team2_vote,
            (team2_vote.c.match_id == TournamentMatch.id)
            & (team2_vote.c.selected_team_id == TournamentMatch.team2_id),
        )
        .filter(TournamentMatch.session_id == session_id)
        .order_by(TournamentMatch.bracket_type.asc(), TournamentMatch.round_no.asc(), TournamentMatch.match_no.asc())
    )
    return list(result.all())


async def get_match_with_votes(
    db: AsyncSession,
    *,
    match_id: int,
) -> tuple[TournamentMatch, TournamentTeam | None, TournamentTeam | None, TournamentTeam | None, int, int] | None:
    team1 = aliased(TournamentTeam)
    team2 = aliased(TournamentTeam)
    winner = aliased(TournamentTeam)

    vote_counts_subquery = (
        select(
            TournamentVote.match_id.label("match_id"),
            TournamentVote.selected_team_id.label("selected_team_id"),
            func.count(TournamentVote.id).label("vote_count"),
        )
        .group_by(TournamentVote.match_id, TournamentVote.selected_team_id)
        .subquery()
    )

    team1_vote = aliased(vote_counts_subquery)
    team2_vote = aliased(vote_counts_subquery)

    result = await db.execute(
        select(
            TournamentMatch,
            team1,
            team2,
            winner,
            func.coalesce(team1_vote.c.vote_count, 0).label("vote_count_team1"),
            func.coalesce(team2_vote.c.vote_count, 0).label("vote_count_team2"),
        )
        .outerjoin(team1, team1.id == TournamentMatch.team1_id)
        .outerjoin(team2, team2.id == TournamentMatch.team2_id)
        .outerjoin(winner, winner.id == TournamentMatch.winner_team_id)
        .outerjoin(
            team1_vote,
            (team1_vote.c.match_id == TournamentMatch.id)
            & (team1_vote.c.selected_team_id == TournamentMatch.team1_id),
        )
        .outerjoin(
            team2_vote,
            (team2_vote.c.match_id == TournamentMatch.id)
            & (team2_vote.c.selected_team_id == TournamentMatch.team2_id),
        )
        .filter(TournamentMatch.id == match_id)
    )
    return result.first()


async def update_match_status(
    db: AsyncSession,
    *,
    match: TournamentMatch,
    status: str,
) -> TournamentMatch:
    match.status = status
    await db.commit()
    await db.refresh(match)
    return match


async def update_match_winner(
    db: AsyncSession,
    *,
    match: TournamentMatch,
    winner_team_id: int | None,
) -> TournamentMatch:
    match.winner_team_id = winner_team_id
    await db.commit()
    await db.refresh(match)
    return match


async def upsert_match_vote(
    db: AsyncSession,
    *,
    match_id: int,
    voter_user_id: int,
    selected_team_id: int,
) -> None:
    result = await db.execute(
        select(TournamentVote).filter(
            TournamentVote.match_id == match_id,
            TournamentVote.voter_user_id == voter_user_id,
        )
    )
    existing = result.scalars().first()
    if existing:
        existing.selected_team_id = selected_team_id
    else:
        db.add(
            TournamentVote(
                match_id=match_id,
                voter_user_id=voter_user_id,
                selected_team_id=selected_team_id,
            )
        )
    await db.commit()


async def list_match_voter_statuses(
    db: AsyncSession,
    *,
    match_id: int,
) -> list[tuple[int, str, bool]]:
    vote_subquery = (
        select(TournamentVote.voter_user_id.label("voter_user_id"))
        .filter(TournamentVote.match_id == match_id)
        .subquery()
    )

    result = await db.execute(
        select(
            TournamentTeamMember.student_user_id.label("voter_user_id"),
            User.name.label("voter_name"),
            (vote_subquery.c.voter_user_id.is_not(None)).label("has_submitted"),
        )
        .join(TournamentTeam, TournamentTeam.id == TournamentTeamMember.team_id)
        .join(TournamentMatch, TournamentMatch.session_id == TournamentTeam.session_id)
        .join(User, User.id == TournamentTeamMember.student_user_id)
        .outerjoin(vote_subquery, vote_subquery.c.voter_user_id == TournamentTeamMember.student_user_id)
        .filter(
            TournamentMatch.id == match_id,
            TournamentTeamMember.can_attend_vote.is_(True),
            or_(
                TournamentTeam.id == TournamentMatch.team1_id,
                TournamentTeam.id == TournamentMatch.team2_id,
            ),
        )
        .order_by(User.name.asc(), User.id.asc())
    )

    return [(int(voter_user_id), str(voter_name or "-"), bool(has_submitted)) for voter_user_id, voter_name, has_submitted in result.all()]


def build_rounds(
    rows: Iterable[tuple[TournamentMatch, TournamentTeam | None, TournamentTeam | None, TournamentTeam | None, int, int]],
) -> dict[tuple[str, int], list[tuple[TournamentMatch, TournamentTeam | None, TournamentTeam | None, TournamentTeam | None, int, int]]]:
    grouped: dict[
        tuple[str, int],
        list[tuple[TournamentMatch, TournamentTeam | None, TournamentTeam | None, TournamentTeam | None, int, int]],
    ] = defaultdict(list)
    for row in rows:
        grouped[(row[0].bracket_type, int(row[0].round_no))].append(row)
    return grouped
