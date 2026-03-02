from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DailySnippet, StudentRiskSnapshot, User, WeeklySnippet
from app.risk_model_v2 import RiskEvaluationResult, evaluate_student_risk_v2


def is_student_user(user: User) -> bool:
    roles = user.roles if isinstance(user.roles, list) else []
    privileged = {"gcs", "교수", "admin"}
    return not bool(set(str(role).strip() for role in roles) & privileged)


def _snapshot_to_dict(snapshot: StudentRiskSnapshot) -> dict:
    return {
        "user_id": snapshot.user_id,
        "evaluated_at": snapshot.evaluated_at,
        "l1": float(snapshot.l1),
        "l2": float(snapshot.l2),
        "l3": float(snapshot.l3),
        "risk_score": float(snapshot.risk_score),
        "risk_band": snapshot.risk_band,
        "daily_subscores": snapshot.daily_subscores_json or {},
        "weekly_subscores": snapshot.weekly_subscores_json or {},
        "trend_subscores": snapshot.trend_subscores_json or {},
        "confidence": snapshot.confidence,
        "reasons": snapshot.reasons_json or [],
        "tone_policy": snapshot.tone_policy_json or {
            "primary": "질문",
            "secondary": ["제안"],
            "suppressed": ["훈계"],
            "trigger_patterns": [],
            "policy_confidence": 0.5,
        },
        "needs_professor_review": bool(snapshot.needs_professor_review),
    }


def _build_confidence_payload(raw: dict) -> dict:
    return {
        "score": float(raw.get("score", 0.0)),
        "data_coverage": float(raw.get("data_coverage", 0.0)),
        "signal_agreement": float(raw.get("signal_agreement", 0.0)),
        "history_depth": float(raw.get("history_depth", 0.0)),
    }


def _evaluation_to_snapshot_payload(user_id: int, evaluation: RiskEvaluationResult) -> dict:
    return {
        "user_id": user_id,
        "l1": evaluation.l1,
        "l2": evaluation.l2,
        "l3": evaluation.l3,
        "risk_score": evaluation.risk_score,
        "risk_band": evaluation.risk_band,
        "confidence": _build_confidence_payload(evaluation.confidence),
        "reasons_json": evaluation.reasons,
        "tone_policy_json": evaluation.tone_policy,
        "daily_subscores_json": evaluation.daily_subscores,
        "weekly_subscores_json": evaluation.weekly_subscores,
        "trend_subscores_json": evaluation.trend_subscores,
        "needs_professor_review": evaluation.needs_professor_review,
    }


async def list_student_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.id.asc()))
    users = list(result.scalars().all())
    return [user for user in users if is_student_user(user)]


async def get_latest_snapshot_by_user_id(db: AsyncSession, user_id: int) -> StudentRiskSnapshot | None:
    result = await db.execute(
        select(StudentRiskSnapshot)
        .filter(StudentRiskSnapshot.user_id == user_id)
        .order_by(StudentRiskSnapshot.evaluated_at.desc(), StudentRiskSnapshot.id.desc())
        .limit(1)
    )
    return result.scalars().first()


async def list_latest_snapshots_for_students(db: AsyncSession) -> list[tuple[User, StudentRiskSnapshot]]:
    students = await list_student_users(db)
    if not students:
        return []

    user_ids = [student.id for student in students]

    latest_subquery = (
        select(
            StudentRiskSnapshot.user_id.label("user_id"),
            func.max(StudentRiskSnapshot.evaluated_at).label("evaluated_at"),
        )
        .filter(StudentRiskSnapshot.user_id.in_(user_ids))
        .group_by(StudentRiskSnapshot.user_id)
        .subquery()
    )

    latest_rows = await db.execute(
        select(StudentRiskSnapshot)
        .join(
            latest_subquery,
            and_(
                StudentRiskSnapshot.user_id == latest_subquery.c.user_id,
                StudentRiskSnapshot.evaluated_at == latest_subquery.c.evaluated_at,
            ),
        )
        .order_by(StudentRiskSnapshot.risk_score.desc(), StudentRiskSnapshot.evaluated_at.desc())
    )
    snapshots = list(latest_rows.scalars().all())
    snapshot_by_user_id = {snapshot.user_id: snapshot for snapshot in snapshots}

    pairs: list[tuple[User, StudentRiskSnapshot]] = []
    for student in students:
        snapshot = snapshot_by_user_id.get(student.id)
        if snapshot is not None:
            pairs.append((student, snapshot))
    return pairs


async def list_risk_history_by_user_id(
    db: AsyncSession,
    user_id: int,
    limit: int = 12,
) -> list[StudentRiskSnapshot]:
    result = await db.execute(
        select(StudentRiskSnapshot)
        .filter(StudentRiskSnapshot.user_id == user_id)
        .order_by(StudentRiskSnapshot.evaluated_at.desc(), StudentRiskSnapshot.id.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def build_overview_counts(db: AsyncSession) -> dict:
    pairs = await list_latest_snapshots_for_students(db)

    counts = {
        "high_or_critical_count": 0,
        "high_count": 0,
        "critical_count": 0,
        "medium_count": 0,
        "low_count": 0,
    }

    for _student, snapshot in pairs:
        band = snapshot.risk_band
        if band == "Critical":
            counts["critical_count"] += 1
            counts["high_or_critical_count"] += 1
        elif band == "High":
            counts["high_count"] += 1
            counts["high_or_critical_count"] += 1
        elif band == "Medium":
            counts["medium_count"] += 1
        else:
            counts["low_count"] += 1

    return counts


async def build_risk_queue(db: AsyncSession, limit: int = 30) -> list[dict]:
    pairs = await list_latest_snapshots_for_students(db)
    items: list[dict] = []

    for student, snapshot in pairs:
        latest_daily_id_result = await db.execute(
            select(DailySnippet.id)
            .filter(DailySnippet.user_id == student.id)
            .order_by(DailySnippet.date.desc(), DailySnippet.id.desc())
            .limit(1)
        )
        latest_daily_id = latest_daily_id_result.scalar_one_or_none()

        latest_weekly_id_result = await db.execute(
            select(WeeklySnippet.id)
            .filter(WeeklySnippet.user_id == student.id)
            .order_by(WeeklySnippet.week.desc(), WeeklySnippet.id.desc())
            .limit(1)
        )
        latest_weekly_id = latest_weekly_id_result.scalar_one_or_none()

        item = {
            "user_id": student.id,
            "user_name": student.name or student.email,
            "user_email": student.email,
            "risk_score": float(snapshot.risk_score),
            "risk_band": snapshot.risk_band,
            "evaluated_at": snapshot.evaluated_at,
            "confidence": float((snapshot.confidence or {}).get("score", 0.0)),
            "reasons": snapshot.reasons_json or [],
            "tone_policy": snapshot.tone_policy_json,
            "latest_daily_snippet_id": int(latest_daily_id) if latest_daily_id is not None else None,
            "latest_weekly_snippet_id": int(latest_weekly_id) if latest_weekly_id is not None else None,
        }
        items.append(item)

    items.sort(key=lambda item: (item["risk_score"], item["evaluated_at"]), reverse=True)
    return items[:limit]


async def evaluate_student_and_create_snapshot(db: AsyncSession, user_id: int) -> dict:
    user = await db.get(User, user_id)
    if not user:
        raise ValueError("User not found")

    recent_daily_start = date.today() - timedelta(days=28)
    recent_weekly_start = date.today() - timedelta(days=56)

    daily_result = await db.execute(
        select(DailySnippet)
        .filter(DailySnippet.user_id == user_id, DailySnippet.date >= recent_daily_start)
        .order_by(DailySnippet.date.asc(), DailySnippet.id.asc())
    )
    daily_snippets = list(daily_result.scalars().all())

    weekly_result = await db.execute(
        select(WeeklySnippet)
        .filter(WeeklySnippet.user_id == user_id, WeeklySnippet.week >= recent_weekly_start)
        .order_by(WeeklySnippet.week.asc(), WeeklySnippet.id.asc())
    )
    weekly_snippets = list(weekly_result.scalars().all())

    l2_history_rows = await db.execute(
        select(StudentRiskSnapshot.l2)
        .filter(StudentRiskSnapshot.user_id == user_id)
        .order_by(StudentRiskSnapshot.evaluated_at.desc(), StudentRiskSnapshot.id.desc())
        .limit(4)
    )
    l2_history = [float(row[0]) for row in l2_history_rows.all()]
    l2_history.reverse()

    recent_history = await list_risk_history_by_user_id(db, user_id, limit=8)
    recovered_count = 0
    relapse_count = 0
    if recent_history:
        bands = [snapshot.risk_band for snapshot in reversed(recent_history)]
        previous = bands[0]
        for current in bands[1:]:
            if previous in {"High", "Critical"} and current in {"Low", "Medium"}:
                recovered_count += 1
            if previous in {"Low", "Medium"} and current in {"High", "Critical"}:
                relapse_count += 1
            previous = current

    evaluation = evaluate_student_risk_v2(
        daily_snippets=daily_snippets,
        weekly_snippets=weekly_snippets,
        recent_l2_history=l2_history,
        recovered_count_4w=recovered_count,
        relapse_count_4w=relapse_count,
    )

    payload = _evaluation_to_snapshot_payload(user_id, evaluation)
    snapshot = StudentRiskSnapshot(**payload)
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)

    return _snapshot_to_dict(snapshot)


async def ensure_latest_snapshot_for_user(db: AsyncSession, user_id: int) -> dict:
    latest = await get_latest_snapshot_by_user_id(db, user_id)
    if latest is None:
        return await evaluate_student_and_create_snapshot(db, user_id)
    return _snapshot_to_dict(latest)


async def ensure_latest_snapshots_for_all_students(db: AsyncSession) -> None:
    students = await list_student_users(db)
    for student in students:
        latest = await get_latest_snapshot_by_user_id(db, student.id)
        if latest is None:
            await evaluate_student_and_create_snapshot(db, student.id)


async def build_risk_history_payload(db: AsyncSession, user_id: int, limit: int = 12) -> list[dict]:
    history = await list_risk_history_by_user_id(db, user_id, limit=limit)
    return [_snapshot_to_dict(snapshot) for snapshot in history]
