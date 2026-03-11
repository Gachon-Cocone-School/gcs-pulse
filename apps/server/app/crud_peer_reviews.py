from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Sequence

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased, load_only

from app.models import (
    PeerReviewSession,
    PeerReviewSessionMember,
    PeerReviewSubmission,
    User,
)


async def create_session(
    db: AsyncSession,
    *,
    title: str,
    professor_user_id: int,
    access_token: str,
) -> PeerReviewSession:
    session = PeerReviewSession(
        title=title,
        professor_user_id=professor_user_id,
        access_token=access_token,
        is_open=True,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


async def get_session_by_id(db: AsyncSession, session_id: int) -> PeerReviewSession | None:
    result = await db.execute(
        select(PeerReviewSession)
        .options(load_only(
            PeerReviewSession.id,
            PeerReviewSession.title,
            PeerReviewSession.professor_user_id,
            PeerReviewSession.is_open,
            PeerReviewSession.access_token,
            PeerReviewSession.created_at,
            PeerReviewSession.updated_at,
        ))
        .filter(PeerReviewSession.id == session_id)
    )
    return result.scalars().first()


async def get_session_by_id_and_professor(
    db: AsyncSession,
    *,
    session_id: int,
    professor_user_id: int,
) -> PeerReviewSession | None:
    result = await db.execute(
        select(PeerReviewSession)
        .options(load_only(
            PeerReviewSession.id,
            PeerReviewSession.title,
            PeerReviewSession.professor_user_id,
            PeerReviewSession.is_open,
            PeerReviewSession.access_token,
            PeerReviewSession.created_at,
            PeerReviewSession.updated_at,
        ))
        .filter(
            PeerReviewSession.id == session_id,
            PeerReviewSession.professor_user_id == professor_user_id,
        )
    )
    return result.scalars().first()


async def get_session_by_access_token(
    db: AsyncSession,
    access_token: str,
) -> PeerReviewSession | None:
    result = await db.execute(
        select(PeerReviewSession)
        .options(load_only(
            PeerReviewSession.id,
            PeerReviewSession.title,
            PeerReviewSession.professor_user_id,
            PeerReviewSession.is_open,
            PeerReviewSession.access_token,
            PeerReviewSession.created_at,
            PeerReviewSession.updated_at,
        ))
        .filter(PeerReviewSession.access_token == access_token)
    )
    return result.scalars().first()


async def update_session_is_open(
    db: AsyncSession,
    *,
    session: PeerReviewSession,
    is_open: bool,
) -> PeerReviewSession:
    session.is_open = is_open
    await db.commit()
    await db.refresh(session)
    return session


async def update_session(
    db: AsyncSession,
    *,
    session: PeerReviewSession,
    title: str,
) -> PeerReviewSession:
    session.title = title
    await db.commit()
    await db.refresh(session)
    return session


async def delete_session(
    db: AsyncSession,
    *,
    session: PeerReviewSession,
) -> None:
    await db.delete(session)
    await db.commit()


async def list_session_members(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[tuple[PeerReviewSessionMember, User]]:
    result = await db.execute(
        select(PeerReviewSessionMember, User)
        .join(User, User.id == PeerReviewSessionMember.student_user_id)
        .filter(PeerReviewSessionMember.session_id == session_id)
        .order_by(PeerReviewSessionMember.team_label.asc(), User.id.asc())
    )
    return list(result.all())


async def list_sessions_by_professor(
    db: AsyncSession,
    *,
    professor_user_id: int,
) -> list[tuple[PeerReviewSession, int, int]]:
    submission_subquery = (
        select(
            PeerReviewSubmission.session_id.label("session_id"),
            func.count(func.distinct(PeerReviewSubmission.evaluator_user_id)).label("submitted_evaluators"),
        )
        .group_by(PeerReviewSubmission.session_id)
        .subquery()
    )

    result = await db.execute(
        select(
            PeerReviewSession,
            func.count(func.distinct(PeerReviewSessionMember.student_user_id)).label("member_count"),
            func.coalesce(submission_subquery.c.submitted_evaluators, 0).label("submitted_evaluators"),
        )
        .outerjoin(PeerReviewSessionMember, PeerReviewSessionMember.session_id == PeerReviewSession.id)
        .outerjoin(submission_subquery, submission_subquery.c.session_id == PeerReviewSession.id)
        .filter(PeerReviewSession.professor_user_id == professor_user_id)
        .group_by(
            PeerReviewSession.id,
            PeerReviewSession.title,
            PeerReviewSession.professor_user_id,
            PeerReviewSession.is_open,
            PeerReviewSession.access_token,
            PeerReviewSession.created_at,
            PeerReviewSession.updated_at,
            submission_subquery.c.submitted_evaluators,
        )
        .order_by(PeerReviewSession.updated_at.desc(), PeerReviewSession.id.desc())
    )

    return [
        (
            session,
            int(member_count or 0),
            int(submitted_evaluators or 0),
        )
        for session, member_count, submitted_evaluators in result.all()
    ]


async def replace_session_members(
    db: AsyncSession,
    *,
    session_id: int,
    members: Sequence[tuple[int, str]],
) -> None:
    await db.execute(
        delete(PeerReviewSessionMember).filter(PeerReviewSessionMember.session_id == session_id)
    )

    for student_user_id, team_label in members:
        db.add(
            PeerReviewSessionMember(
                session_id=session_id,
                student_user_id=student_user_id,
                team_label=team_label,
            )
        )

    await db.commit()


async def get_member(
    db: AsyncSession,
    *,
    session_id: int,
    student_user_id: int,
) -> PeerReviewSessionMember | None:
    result = await db.execute(
        select(PeerReviewSessionMember).filter(
            PeerReviewSessionMember.session_id == session_id,
            PeerReviewSessionMember.student_user_id == student_user_id,
        )
    )
    return result.scalars().first()


async def list_team_member_users(
    db: AsyncSession,
    *,
    session_id: int,
    team_label: str,
) -> list[User]:
    result = await db.execute(
        select(User)
        .join(PeerReviewSessionMember, PeerReviewSessionMember.student_user_id == User.id)
        .filter(
            PeerReviewSessionMember.session_id == session_id,
            PeerReviewSessionMember.team_label == team_label,
        )
        .order_by(User.id.asc())
    )
    return list(result.scalars().all())


async def has_submission_by_evaluator(
    db: AsyncSession,
    *,
    session_id: int,
    evaluator_user_id: int,
) -> bool:
    result = await db.execute(
        select(PeerReviewSubmission.id)
        .filter(
            PeerReviewSubmission.session_id == session_id,
            PeerReviewSubmission.evaluator_user_id == evaluator_user_id,
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None


async def list_submitted_evaluator_ids(
    db: AsyncSession,
    *,
    session_id: int,
    evaluator_ids: Iterable[int],
) -> set[int]:
    evaluator_ids = list(evaluator_ids)
    if not evaluator_ids:
        return set()

    result = await db.execute(
        select(PeerReviewSubmission.evaluator_user_id)
        .filter(
            PeerReviewSubmission.session_id == session_id,
            PeerReviewSubmission.evaluator_user_id.in_(evaluator_ids),
        )
        .group_by(PeerReviewSubmission.evaluator_user_id)
    )
    return {int(row[0]) for row in result.all()}


async def list_session_progress_rows(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[tuple[PeerReviewSessionMember, User, bool]]:
    members = await list_session_members(db, session_id=session_id)
    submitted_ids = await list_submitted_evaluator_ids(
        db,
        session_id=session_id,
        evaluator_ids=[user.id for _member, user in members],
    )

    return [
        (member, user, user.id in submitted_ids)
        for member, user in members
    ]


async def upsert_submission_entries(
    db: AsyncSession,
    *,
    session_id: int,
    evaluator_user_id: int,
    entries: Sequence[tuple[int, int, bool]],
) -> None:
    await db.execute(
        delete(PeerReviewSubmission).filter(
            PeerReviewSubmission.session_id == session_id,
            PeerReviewSubmission.evaluator_user_id == evaluator_user_id,
        )
    )

    for evaluatee_user_id, contribution_percent, fit_yes_no in entries:
        db.add(
            PeerReviewSubmission(
                session_id=session_id,
                evaluator_user_id=evaluator_user_id,
                evaluatee_user_id=evaluatee_user_id,
                contribution_percent=contribution_percent,
                fit_yes_no=fit_yes_no,
            )
        )

    await db.commit()


async def list_submission_rows_for_session(
    db: AsyncSession,
    *,
    session_id: int,
) -> list[tuple[PeerReviewSubmission, User, User]]:
    evaluator = aliased(User)
    evaluatee = aliased(User)

    result = await db.execute(
        select(PeerReviewSubmission, evaluator, evaluatee)
        .join(evaluator, evaluator.id == PeerReviewSubmission.evaluator_user_id)
        .join(evaluatee, evaluatee.id == PeerReviewSubmission.evaluatee_user_id)
        .filter(PeerReviewSubmission.session_id == session_id)
        .order_by(
            PeerReviewSubmission.updated_at.desc(),
            PeerReviewSubmission.evaluator_user_id.asc(),
            PeerReviewSubmission.evaluatee_user_id.asc(),
        )
    )
    return list(result.all())


async def count_submitted_evaluators(
    db: AsyncSession,
    *,
    session_id: int,
) -> int:
    result = await db.execute(
        select(func.count(func.distinct(PeerReviewSubmission.evaluator_user_id))).filter(
            PeerReviewSubmission.session_id == session_id
        )
    )
    return int(result.scalar_one() or 0)


async def build_summary_for_user(
    db: AsyncSession,
    *,
    session_id: int,
    user_id: int,
) -> dict[str, float]:
    rows = await db.execute(
        select(
            PeerReviewSubmission.evaluator_user_id,
            PeerReviewSubmission.evaluatee_user_id,
            PeerReviewSubmission.contribution_percent,
            PeerReviewSubmission.fit_yes_no,
        ).filter(PeerReviewSubmission.session_id == session_id)
    )

    received_contributions: list[float] = []
    received_fit_values: list[float] = []
    given_contributions: list[float] = []
    given_fit_values: list[float] = []

    for evaluator_user_id, evaluatee_user_id, contribution_percent, fit_yes_no in rows.all():
        contribution_value = float(contribution_percent)
        fit_value = 1.0 if bool(fit_yes_no) else 0.0

        if evaluatee_user_id == user_id:
            received_contributions.append(contribution_value)
            received_fit_values.append(fit_value)
        if evaluator_user_id == user_id:
            given_contributions.append(contribution_value)
            given_fit_values.append(fit_value)

    def _avg(values: list[float]) -> float:
        if not values:
            return 0.0
        return float(sum(values) / len(values))

    return {
        "my_received_contribution_avg": _avg(received_contributions),
        "my_given_contribution_avg": _avg(given_contributions),
        "my_fit_yes_ratio_received": _avg(received_fit_values) * 100.0,
        "my_fit_yes_ratio_given": _avg(given_fit_values) * 100.0,
    }


def build_session_result_stats(
    rows: Sequence[tuple[PeerReviewSubmission, User, User]],
) -> tuple[dict[str, float | None], dict[str, float | None], dict[str, float | None]]:
    contribution_bucket: dict[str, list[int]] = defaultdict(list)
    fit_by_evaluatee_bucket: dict[str, list[bool]] = defaultdict(list)
    fit_by_evaluator_bucket: dict[str, list[bool]] = defaultdict(list)
    evaluatee_names: set[str] = set()
    evaluator_names: set[str] = set()

    for submission, evaluator, evaluatee in rows:
        evaluatee_key = evaluatee.name or evaluatee.email
        evaluator_key = evaluator.name or evaluator.email
        evaluatee_names.add(evaluatee_key)
        evaluator_names.add(evaluator_key)
        if evaluator.id != evaluatee.id:
            contribution_bucket[evaluatee_key].append(int(submission.contribution_percent))
            fit_by_evaluatee_bucket[evaluatee_key].append(bool(submission.fit_yes_no))
            fit_by_evaluator_bucket[evaluator_key].append(bool(submission.fit_yes_no))

    contribution_avg_by_evaluatee = {
        evaluatee_name: (float(sum(values) / len(values)) if values else None)
        for evaluatee_name, values in contribution_bucket.items()
    }
    fit_yes_ratio_by_evaluatee = {
        evaluatee_name: (float((sum(1 for value in values if value) / len(values)) * 100.0) if values else None)
        for evaluatee_name, values in fit_by_evaluatee_bucket.items()
    }
    fit_yes_ratio_by_evaluator = {
        evaluator_name: (float((sum(1 for value in values if value) / len(values)) * 100.0) if values else None)
        for evaluator_name, values in fit_by_evaluator_bucket.items()
    }

    for evaluatee_name in evaluatee_names:
        contribution_avg_by_evaluatee.setdefault(evaluatee_name, None)
        fit_yes_ratio_by_evaluatee.setdefault(evaluatee_name, None)
    for evaluator_name in evaluator_names:
        fit_yes_ratio_by_evaluator.setdefault(evaluator_name, None)

    return contribution_avg_by_evaluatee, fit_yes_ratio_by_evaluatee, fit_yes_ratio_by_evaluator
