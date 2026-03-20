from __future__ import annotations

from collections import defaultdict, deque
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


async def check_next_match_has_votes(
    db: AsyncSession,
    *,
    match_id: int,
) -> tuple[int | None, bool]:
    """next_match_id와 그 경기에 투표가 있는지 반환한다."""
    result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = result.scalars().first()
    if match is None or match.next_match_id is None:
        return None, False

    next_match_id = int(match.next_match_id)
    vote_count_result = await db.execute(
        select(func.count(TournamentVote.id)).filter(TournamentVote.match_id == next_match_id)
    )
    has_votes = int(vote_count_result.scalar() or 0) > 0
    return next_match_id, has_votes


async def reset_match_votes(
    db: AsyncSession,
    *,
    match_id: int,
) -> TournamentMatch:
    """해당 경기의 투표를 전부 삭제하고 승자·상태를 초기화한다.
    호출 전 상위 라운드 차단 여부는 라우터에서 확인한다."""
    result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = result.scalars().first()
    if match is None:
        raise ValueError(f"Match {match_id} not found")

    # 이전 승자를 다음 경기에서 회수
    if match.winner_team_id is not None:
        await db.execute(delete(TournamentVote).filter(TournamentVote.match_id == match_id))
        # retract 전 임시 커밋 없이 직접 처리 (match 객체 아직 alive)
        if match.next_match_id:
            nm_result = await db.execute(
                select(TournamentMatch).filter(TournamentMatch.id == match.next_match_id)
            )
            next_match = nm_result.scalars().first()
            if next_match:
                if next_match.team1_id == match.winner_team_id:
                    next_match.team1_id = None
                elif next_match.team2_id == match.winner_team_id:
                    next_match.team2_id = None

        old_winner_id = int(match.winner_team_id)
        loser_id: int | None = None
        if match.team1_id is not None and match.team2_id is not None:
            loser_id = match.team2_id if match.team1_id == old_winner_id else match.team1_id
        if match.loser_next_match_id and loser_id is not None:
            lm_result = await db.execute(
                select(TournamentMatch).filter(TournamentMatch.id == match.loser_next_match_id)
            )
            loser_match = lm_result.scalars().first()
            if loser_match:
                if loser_match.team1_id == loser_id:
                    loser_match.team1_id = None
                elif loser_match.team2_id == loser_id:
                    loser_match.team2_id = None
    else:
        await db.execute(delete(TournamentVote).filter(TournamentVote.match_id == match_id))

    match.winner_team_id = None
    match.status = "pending"
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


async def retract_match_result(
    db: AsyncSession,
    *,
    match_id: int,
) -> None:
    """advance_match_result로 다음 경기에 배치된 승자/패자를 다시 제거한다.
    winner_team_id 변경 전에 호출해야 한다."""
    result = await db.execute(select(TournamentMatch).filter(TournamentMatch.id == match_id))
    match = result.scalars().first()
    if match is None or match.winner_team_id is None:
        return

    old_winner_id = int(match.winner_team_id)
    old_loser_id: int | None = None
    if match.team1_id is not None and match.team2_id is not None:
        old_loser_id = match.team2_id if match.team1_id == old_winner_id else match.team1_id

    modified = False

    if match.next_match_id:
        nm_result = await db.execute(
            select(TournamentMatch).filter(TournamentMatch.id == match.next_match_id)
        )
        next_match = nm_result.scalars().first()
        if next_match:
            if next_match.team1_id == old_winner_id:
                next_match.team1_id = None
                modified = True
            elif next_match.team2_id == old_winner_id:
                next_match.team2_id = None
                modified = True

    if match.loser_next_match_id and old_loser_id is not None:
        lm_result = await db.execute(
            select(TournamentMatch).filter(TournamentMatch.id == match.loser_next_match_id)
        )
        loser_match = lm_result.scalars().first()
        if loser_match:
            if loser_match.team1_id == old_loser_id:
                loser_match.team1_id = None
                modified = True
            elif loser_match.team2_id == old_loser_id:
                loser_match.team2_id = None
                modified = True

    if modified:
        await db.commit()


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
            # 같은 next_match를 향하는 피더 경기를 round_no, match_no 순으로 정렬해
            # 첫 번째 피더 → team1, 두 번째 피더 → team2 로 고정 배정
            feeders_result = await db.execute(
                select(TournamentMatch)
                .filter(TournamentMatch.next_match_id == next_match.id)
                .order_by(TournamentMatch.round_no, TournamentMatch.match_no)
            )
            feeders = feeders_result.scalars().all()
            feeder_ids = [f.id for f in feeders]
            use_team1 = (len(feeder_ids) == 0 or feeder_ids[0] == match.id)
            if use_team1:
                next_match.team1_id = winner_id
            else:
                next_match.team2_id = winner_id
            modified.append(next_match)

    if match.loser_next_match_id and loser_id is not None:
        lm_result = await db.execute(
            select(TournamentMatch).filter(TournamentMatch.id == match.loser_next_match_id)
        )
        loser_match = lm_result.scalars().first()
        if loser_match:
            if loser_match.bracket_type == "losers":
                # WB 패자가 LB로 떨어지는 경우:
                # 같은 LB 경기에 WB 패자가 2팀 들어오면(LB R1) match_no 순으로 team1/team2 배정
                # WB 패자가 1팀만 들어오면(mixed LB) LB 승자가 team1을 쓰므로 team2 고정
                loser_feeders_result = await db.execute(
                    select(TournamentMatch)
                    .filter(TournamentMatch.loser_next_match_id == loser_match.id)
                    .order_by(TournamentMatch.round_no, TournamentMatch.match_no)
                )
                loser_feeders = loser_feeders_result.scalars().all()
                if len(loser_feeders) >= 2:
                    use_team1 = (loser_feeders[0].id == match.id)
                    if use_team1:
                        loser_match.team1_id = loser_id
                    else:
                        loser_match.team2_id = loser_id
                else:
                    # mixed LB: WB 패자 → team2 (LB 승자는 next_match_id 경로로 team1)
                    loser_match.team2_id = loser_id
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


async def get_session_results(
    db: AsyncSession,
    *,
    session_id: int,
) -> dict:
    """토너먼트 세션 결과 반환 (팀 순위 + 경기 결과 + 투표자 순위)."""
    # 모든 경기 조회 (투표 수 포함)
    rows = await list_matches_with_votes_by_session(db, session_id=session_id)

    # 팀명 맵 구성 및 match 구조 파악
    match_objs = [r[0] for r in rows]

    team_names: dict[int, str] = {}
    for m, t1, t2, w, vc1, vc2 in rows:
        if m.team1_id and t1:
            team_names[m.team1_id] = t1.name
        if m.team2_id and t2:
            team_names[m.team2_id] = t2.name
        if m.winner_team_id and w:
            team_names[m.winner_team_id] = w.name

    # Grand Final 찾기: outgoing 링크가 없는 terminal 경기 중 WB 우선, round_no 최대값
    # (next_match_id=None AND loser_next_match_id=None = 결과를 어디에도 전달하지 않는 최종 경기)
    terminal_matches = [
        m for m in match_objs
        if m.next_match_id is None and m.loser_next_match_id is None and not m.is_bye
    ]
    wb_terminals = [m for m in terminal_matches if m.bracket_type == "winners"]
    grand_final = (
        max(wb_terminals, key=lambda m: (m.round_no, m.match_no))
        if wb_terminals
        else (max(terminal_matches, key=lambda m: (m.round_no, m.match_no)) if terminal_matches else None)
    )
    # LB terminal 경기들 (Grand Final 제외): LB 챔피언을 배출하는 경기
    lb_terminal_matches = [
        m for m in terminal_matches
        if m.bracket_type == "losers" and m is not grand_final
    ]

    # BFS: Grand Final(distance=0)에서 역방향으로 거리 계산
    back_feeders: dict[int, list[int]] = defaultdict(list)
    for m in match_objs:
        if m.next_match_id:
            back_feeders[m.next_match_id].append(m.id)
        if m.loser_next_match_id:
            back_feeders[m.loser_next_match_id].append(m.id)

    distance: dict[int, int] = {}
    q: deque[int] = deque()
    if grand_final:
        distance[grand_final.id] = 0
        q.append(grand_final.id)
    # LB terminal 경기들도 BFS 기준점으로 추가 (distance 1로 설정)
    for lbt in lb_terminal_matches:
        if lbt.id not in distance:
            distance[lbt.id] = 1
            q.append(lbt.id)
    while q:
        mid = q.popleft()
        for fid in back_feeders[mid]:
            if fid not in distance:
                distance[fid] = distance[mid] + 1
                q.append(fid)

    # 팀 순위 계산
    # ① Grand Final 우승팀 = 1위
    # 순위 결정:
    # 1위: Grand Final 우승팀
    # 2위: Grand Final 패배팀 (WB 준우승)
    # 3위+: LB terminal 경기 우승팀 (LB 챔피언) — Grand Final 없이 LB를 제패한 팀
    # 그 다음: loser_next_match_id=None인 경기 패배팀을 distance 오름차순으로
    winner_id = grand_final.winner_team_id if grand_final and grand_final.status == "closed" else None

    # LB terminal 경기 우승팀 (Grand Final 없이 LB를 우승한 팀)
    lb_champion_ids = sorted(
        [
            lbt.winner_team_id
            for lbt in lb_terminal_matches
            if lbt.status == "closed" and lbt.winner_team_id and lbt.winner_team_id != winner_id
        ],
        key=lambda tid: team_names.get(tid, ""),
    )

    # distance 기반 패배팀 그룹화 (loser_next_match_id=None인 closed 경기의 패배팀)
    team_elim_distance: dict[int, int] = {}
    for m in match_objs:
        if m.status != "closed" or m.winner_team_id is None or m.loser_next_match_id is not None:
            continue
        loser_id = m.team1_id if m.winner_team_id == m.team2_id else m.team2_id
        if loser_id is None:
            continue
        d = distance.get(m.id, 9999)
        if loser_id not in team_elim_distance or d < team_elim_distance[loser_id]:
            team_elim_distance[loser_id] = d

    distance_groups: dict[int, list[int]] = defaultdict(list)
    for tid, d in team_elim_distance.items():
        distance_groups[d].append(tid)

    team_rankings = []
    current_rank = 1

    # 1위: Grand Final 우승팀
    if winner_id:
        team_rankings.append({"rank": 1, "team_id": winner_id, "team_name": team_names.get(winner_id, "?")})
        current_rank = 2

    def _append_group(teams: list[int]) -> None:
        nonlocal current_rank
        for tid in teams:
            team_rankings.append({"rank": current_rank, "team_id": tid, "team_name": team_names.get(tid, "?")})
        current_rank += len(teams)

    # distance=0: Grand Final 패배팀 (준우승)
    d0 = sorted([tid for tid in distance_groups.get(0, []) if tid != winner_id], key=lambda t: team_names.get(t, ""))
    _append_group(d0)

    # LB 챔피언 (Grand Final 없이 LB 우승, 공동 3위 수준)
    _append_group(lb_champion_ids)

    # distance >= 1 패배팀 (오름차순)
    for d in sorted(k for k in distance_groups if k >= 1):
        teams_at_d = sorted(
            [tid for tid in distance_groups[d] if tid != winner_id and tid not in lb_champion_ids],
            key=lambda tid: team_names.get(tid, ""),
        )
        _append_group(teams_at_d)

    # Global match number 계산 (WB 우선, bracket_type/round/match_no 순)
    sorted_matches = sorted(
        [m for m in match_objs if not m.is_bye],
        key=lambda m: (1 if m.bracket_type == "losers" else 0, m.round_no, m.match_no),
    )
    global_match_nos: dict[int, int] = {m.id: i + 1 for i, m in enumerate(sorted_matches)}

    # 경기 결과 목록 (부전승 제외)
    match_results = []
    for m, t1, t2, w, vc1, vc2 in rows:
        if m.is_bye:
            continue
        is_tie = (
            m.status == "closed"
            and m.winner_team_id is not None
            and vc1 == vc2
            and m.team1_id is not None
            and m.team2_id is not None
        )
        match_results.append({
            "id": m.id,
            "bracket_type": m.bracket_type,
            "round_no": m.round_no,
            "match_no": m.match_no,
            "global_match_no": global_match_nos.get(m.id),
            "team1_id": m.team1_id,
            "team1_name": t1.name if t1 else None,
            "team2_id": m.team2_id,
            "team2_name": t2.name if t2 else None,
            "winner_team_id": m.winner_team_id,
            "winner_team_name": w.name if w else None,
            "vote_count_team1": int(vc1),
            "vote_count_team2": int(vc2),
            "is_tie": is_tie,
            "is_bye": m.is_bye,
        })

    # 투표자 순위 (점수 내림차순, 누적 응답시간 오름차순)
    total_matches_result = await db.execute(
        select(func.count(TournamentMatch.id)).filter(
            TournamentMatch.session_id == session_id,
            TournamentMatch.is_bye.is_(False),
        )
    )
    total_matches = int(total_matches_result.scalar() or 0)

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

    voter_rows = (
        await db.execute(
            select(
                vote_stats_cte.c.voter_user_id,
                User.name.label("voter_name"),
                vote_stats_cte.c.score,
                vote_stats_cte.c.cumulative_seconds,
            )
            .join(User, User.id == vote_stats_cte.c.voter_user_id)
            .order_by(vote_stats_cte.c.score.desc(), vote_stats_cte.c.cumulative_seconds.asc())
        )
    ).all()

    voter_rankings = []
    current_voter_rank = 1
    prev_score: int | None = None
    prev_cumulative: float | None = None
    for i, row in enumerate(voter_rows):
        score = int(row.score)
        cumulative = float(row.cumulative_seconds)
        if prev_score is not None and (score != prev_score or cumulative != prev_cumulative):
            current_voter_rank = i + 1
        voter_rankings.append({
            "rank": current_voter_rank,
            "voter_user_id": row.voter_user_id,
            "voter_name": row.voter_name,
            "score": score,
            "total_matches": total_matches,
            "cumulative_response_seconds": cumulative,
        })
        prev_score = score
        prev_cumulative = cumulative

    session = await get_session_by_id(db, session_id)
    return {
        "session_id": session_id,
        "title": session.title if session else "",
        "team_rankings": team_rankings,
        "matches": match_results,
        "voter_rankings": voter_rankings,
    }
