from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from datetime import datetime, timezone

from sqlalchemy import and_, case, delete, func, or_, select
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
    allow_self_vote: bool = True,
) -> TournamentSession:
    session = TournamentSession(
        title=title,
        professor_user_id=professor_user_id,
        is_open=False,
        allow_self_vote=allow_self_vote,
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
    allow_self_vote: bool | None = None,
) -> TournamentSession:
    session.title = title
    if allow_self_vote is not None:
        session.allow_self_vote = allow_self_vote
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
    format_text: str | None,
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
        loser_next_index = item.get("loser_next_index")
        if loser_next_index is not None and 0 <= loser_next_index < len(created_matches):
            created_matches[index].loser_next_match_id = created_matches[loser_next_index].id

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
    if status == "open" and match.opened_at is None:
        match.opened_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(match)
    return match


async def get_session_my_score(
    db: AsyncSession,
    *,
    session_id: int,
    voter_user_id: int,
) -> dict:
    # 총 경기 수 (BYE 제외)
    total_result = await db.execute(
        select(func.count(TournamentMatch.id)).filter(
            TournamentMatch.session_id == session_id,
            TournamentMatch.is_bye.is_(False),
        )
    )
    total_matches = int(total_result.scalar() or 0)

    # 모든 투표자의 점수 + 누적 응답 시간 CTE
    vote_stats_cte = (
        select(
            TournamentVote.voter_user_id.label("voter_user_id"),
            func.sum(
                case((TournamentVote.selected_team_id == TournamentMatch.winner_team_id, 1), else_=0)
            ).label("score"),
            func.coalesce(
                func.sum(
                    case(
                        (
                            TournamentMatch.opened_at.is_not(None),
                            func.extract("epoch", TournamentVote.created_at - TournamentMatch.opened_at),
                        ),
                        else_=0,
                    )
                ),
                0,
            ).label("cumulative_seconds"),
        )
        .join(TournamentMatch, TournamentMatch.id == TournamentVote.match_id)
        .filter(TournamentMatch.session_id == session_id)
        .group_by(TournamentVote.voter_user_id)
        .cte("vote_stats")
    )

    # 내 스탯
    my_row = (
        await db.execute(
            select(vote_stats_cte.c.score, vote_stats_cte.c.cumulative_seconds).filter(
                vote_stats_cte.c.voter_user_id == voter_user_id
            )
        )
    ).first()

    my_score = int(my_row.score) if my_row else 0
    my_cumulative = float(my_row.cumulative_seconds) if my_row else 0.0

    # 나보다 높은 사람 수 계산 → 내 등수
    rank_above = int(
        (
            await db.execute(
                select(func.count()).select_from(vote_stats_cte).filter(
                    or_(
                        vote_stats_cte.c.score > my_score,
                        and_(
                            vote_stats_cte.c.score == my_score,
                            vote_stats_cte.c.cumulative_seconds < my_cumulative,
                        ),
                    )
                )
            )
        ).scalar()
        or 0
    )

    total_voters = int(
        (await db.execute(select(func.count()).select_from(vote_stats_cte))).scalar() or 0
    )

    return {
        "session_id": session_id,
        "my_score": my_score,
        "total_matches": total_matches,
        "my_rank": rank_above + 1,
        "total_voters": total_voters,
        "cumulative_response_seconds": my_cumulative,
    }


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
    exclude_competing_teams: bool = False,
) -> list[tuple[int, str, bool]]:
    vote_subquery = (
        select(TournamentVote.voter_user_id.label("voter_user_id"))
        .filter(TournamentVote.match_id == match_id)
        .subquery()
    )

    is_competing = or_(
        TournamentTeam.id == TournamentMatch.team1_id,
        TournamentTeam.id == TournamentMatch.team2_id,
    )

    base_filters = [
        TournamentMatch.id == match_id,
        TournamentTeamMember.can_attend_vote.is_(True),
    ]
    if exclude_competing_teams:
        base_filters.append(~is_competing)

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
        .filter(*base_filters)
        .order_by(User.name.asc(), User.id.asc())
    )

    return [(int(voter_user_id), str(voter_name or "-"), bool(has_submitted)) for voter_user_id, voter_name, has_submitted in result.all()]


async def get_member_team_in_session(
    db: AsyncSession,
    *,
    session_id: int,
    user_id: int,
) -> TournamentTeam | None:
    """세션 내에서 해당 유저가 속한 팀을 반환한다. 팀원이 아니면 None."""
    result = await db.execute(
        select(TournamentTeam)
        .join(TournamentTeamMember, TournamentTeamMember.team_id == TournamentTeam.id)
        .filter(
            TournamentTeam.session_id == session_id,
            TournamentTeamMember.student_user_id == user_id,
        )
    )
    return result.scalars().first()


async def list_sessions_by_student(
    db: AsyncSession,
    *,
    student_user_id: int,
) -> list[TournamentSession]:
    """학생이 팀원으로 등록된 세션 목록을 반환한다."""
    result = await db.execute(
        select(TournamentSession)
        .join(TournamentTeam, TournamentTeam.session_id == TournamentSession.id)
        .join(TournamentTeamMember, TournamentTeamMember.team_id == TournamentTeam.id)
        .filter(TournamentTeamMember.student_user_id == student_user_id)
        .order_by(TournamentSession.updated_at.desc(), TournamentSession.id.desc())
        .distinct()
    )
    return list(result.scalars().all())


async def advance_match_result(
    db: AsyncSession,
    *,
    match_id: int,
) -> list[TournamentMatch]:
    """winner_team_id 확정 후 승자를 next_match로, 패자를 loser_next_match로 자동 배치한다.
    변경된 경기 목록을 반환한다."""
    result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = result.scalars().first()
    if match is None or match.winner_team_id is None:
        return []

    winner_id = int(match.winner_team_id)
    loser_id: int | None = None
    if match.team1_id is not None and match.team2_id is not None:
        loser_id = match.team2_id if match.team1_id == winner_id else match.team1_id

    modified: list[TournamentMatch] = []

    if match.next_match_id:
        nm_result = await db.execute(
            select(TournamentMatch).filter(TournamentMatch.id == match.next_match_id)
        )
        next_match = nm_result.scalars().first()
        if next_match:
            # LB 경기로 진출하는 LB 승자 → team1 고정 (위쪽 슬롯)
            if next_match.bracket_type == "losers" and match.bracket_type == "losers":
                if next_match.team1_id is None:
                    next_match.team1_id = winner_id
                elif next_match.team2_id is None:
                    next_match.team2_id = winner_id
            else:
                if next_match.team1_id is None:
                    next_match.team1_id = winner_id
                elif next_match.team2_id is None:
                    next_match.team2_id = winner_id
            modified.append(next_match)

    if match.loser_next_match_id and loser_id is not None:
        lm_result = await db.execute(
            select(TournamentMatch).filter(TournamentMatch.id == match.loser_next_match_id)
        )
        loser_match = lm_result.scalars().first()
        if loser_match:
            # LB 경기로 떨어지는 WB 패자 → team2 고정 (아래쪽 슬롯)
            if loser_match.bracket_type == "losers":
                if loser_match.team2_id is None:
                    loser_match.team2_id = loser_id
                elif loser_match.team1_id is None:
                    loser_match.team1_id = loser_id
            else:
                if loser_match.team1_id is None:
                    loser_match.team1_id = loser_id
                elif loser_match.team2_id is None:
                    loser_match.team2_id = loser_id
            modified.append(loser_match)

    if modified:
        await db.commit()
    return modified


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
