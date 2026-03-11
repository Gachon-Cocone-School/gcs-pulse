from __future__ import annotations

import json
import logging
import re
import secrets
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app import crud_peer_evaluations as peer_eval_crud
from app.core.config import settings
from app.database import get_db
from app.dependencies import verify_csrf
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient
from app.lib.notification_runtime import registry as notification_registry
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["peer-evaluations"],
    dependencies=[Depends(verify_csrf)],
)

_TEST_COPILOT_TOKEN_MISSING = "No OAuth token available to request Copilot token"


def _normalize_name(name: str) -> str:
    return "".join(str(name or "").strip().lower().split())


def _is_professor_only(user: User) -> bool:
    roles = user.roles if isinstance(user.roles, list) else []
    return "교수" in {str(role).strip() for role in roles}


def _build_form_url(access_token: str) -> str:
    base = settings.AUTH_SUCCESS_URL.rstrip("/")
    return f"{base}/peer-reviews/forms/{access_token}"


def _build_raw_text_from_members(members: list[schemas.PeerEvaluationSessionMemberItem]) -> str:
    grouped: dict[str, list[str]] = defaultdict(list)
    for member in members:
        grouped[member.team_label].append(member.student_name)

    lines: list[str] = []
    for team_label in sorted(grouped.keys()):
        names = ", ".join(grouped[team_label])
        lines.append(f"{team_label}: {names}")

    return "\r\n".join(lines)


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
    if not _is_professor_only(viewer):
        raise HTTPException(status_code=403, detail="Professor only")
    return viewer


async def _get_professor_session_or_404(
    db: AsyncSession,
    *,
    session_id: int,
    professor_user_id: int,
):
    session = await peer_eval_crud.get_session_by_id_and_professor(
        db,
        session_id=session_id,
        professor_user_id=professor_user_id,
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Peer evaluation session not found")
    return session


def _parse_team_text_fallback(raw_text: str) -> list[dict[str, Any]]:
    segments = [segment.strip() for segment in re.split(r"\s*/\s*", raw_text) if segment.strip()]
    teams: list[dict[str, Any]] = []

    for idx, segment in enumerate(segments, start=1):
        if ":" in segment:
            label_part, members_part = segment.split(":", 1)
            team_label = label_part.strip() or f"team-{idx}"
            members_text = members_part
        else:
            team_label = f"team-{idx}"
            members_text = segment

        names = [name.strip() for name in re.split(r"[,\n]+", members_text) if name.strip()]
        teams.append(
            {
                "team_label": team_label,
                "members": [{"name": name, "email_hint": None} for name in names],
            }
        )

    return teams


async def _parse_team_text_with_copilot(
    *,
    raw_text: str,
    copilot: CopilotClient,
) -> list[dict[str, Any]]:
    system_prompt = (
        "You are a parser for team roster text. "
        "Return strict JSON only with this shape: "
        "{\"teams\":[{\"team_label\":\"1조\",\"members\":[{\"name\":\"홍길동\",\"email_hint\":null}]}]}. "
        "Do not include markdown or extra keys. "
        "If team label is missing, infer sequential labels like team-1, team-2."
    )
    user_prompt = f"Input:\n{raw_text}"

    try:
        response = await copilot.chat(
            [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            request_meta={"event": "peer_evaluations.parse_members"},
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
        logger.exception("Failed to parse team composition via Copilot")
        raise HTTPException(status_code=502, detail="Failed to parse team composition") from exc


async def _list_student_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User).order_by(User.id.asc()))
    return list(result.scalars().all())


def _map_parsed_teams_to_students(
    *,
    parsed_teams: list[dict[str, Any]],
    students: list[User],
) -> tuple[dict[str, list[schemas.PeerEvaluationParsePreviewMember]], list[schemas.PeerEvaluationParseUnresolvedItem]]:
    students_by_email = {
        str(student.email or "").strip().lower(): student
        for student in students
        if str(student.email or "").strip()
    }

    students_by_name: dict[str, list[User]] = defaultdict(list)
    normalized_students: list[tuple[str, User]] = []
    for student in students:
        key = _normalize_name(student.name or "")
        if key:
            students_by_name[key].append(student)
            normalized_students.append((key, student))

    def _to_candidate_item(student: User) -> schemas.PeerEvaluationParseCandidateItem:
        return schemas.PeerEvaluationParseCandidateItem(
            student_user_id=student.id,
            student_name=student.name or student.email,
            student_email=student.email,
        )

    teams_map: dict[str, list[schemas.PeerEvaluationParsePreviewMember]] = defaultdict(list)
    unresolved: list[schemas.PeerEvaluationParseUnresolvedItem] = []

    for index, team in enumerate(parsed_teams, start=1):
        team_label = str(team.get("team_label") or f"team-{index}").strip() or f"team-{index}"
        raw_members = team.get("members")
        members = raw_members if isinstance(raw_members, list) else []

        for member in members:
            if not isinstance(member, dict):
                continue

            raw_name = str(member.get("name") or "").strip()
            email_hint = str(member.get("email_hint") or "").strip().lower()

            if not raw_name and not email_hint:
                continue

            candidate: User | None = None
            if email_hint:
                candidate = students_by_email.get(email_hint)
                if candidate is None:
                    unresolved.append(
                        schemas.PeerEvaluationParseUnresolvedItem(
                            team_label=team_label,
                            raw_name=raw_name or email_hint,
                            reason="email_not_found",
                            candidates=[],
                        )
                    )
                    continue
            else:
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
                            schemas.PeerEvaluationParseUnresolvedItem(
                                team_label=team_label,
                                raw_name=raw_name,
                                reason="ambiguous_name",
                                candidates=[_to_candidate_item(student) for student in unique_like_candidates],
                            )
                        )
                        continue
                    else:
                        unresolved.append(
                            schemas.PeerEvaluationParseUnresolvedItem(
                                team_label=team_label,
                                raw_name=raw_name,
                                reason="name_not_found",
                                candidates=[],
                            )
                        )
                        continue

            teams_map[team_label].append(
                schemas.PeerEvaluationParsePreviewMember(
                    team_label=team_label,
                    raw_name=raw_name or (candidate.name or candidate.email),
                    student_user_id=candidate.id,
                    student_name=candidate.name or candidate.email,
                    student_email=candidate.email,
                )
            )

    return dict(teams_map), unresolved


@router.post("/peer-reviews/sessions", response_model=schemas.PeerEvaluationSessionResponse)
@router.post("/peer-evaluations/sessions", response_model=schemas.PeerEvaluationSessionResponse)
async def create_peer_evaluation_session(
    payload: schemas.PeerEvaluationSessionCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    access_token = secrets.token_urlsafe(24)

    session = await peer_eval_crud.create_session(
        db,
        title=payload.title,
        professor_user_id=professor.id,
        access_token=access_token,
    )

    return schemas.PeerEvaluationSessionResponse(
        id=session.id,
        title=session.title,
        raw_text=None,
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        access_token=session.access_token,
        form_url=_build_form_url(session.access_token),
        created_at=session.created_at,
        updated_at=session.updated_at,
        members=[],
    )


@router.get("/peer-reviews/sessions", response_model=schemas.PeerEvaluationSessionListResponse)
@router.get("/peer-evaluations/sessions", response_model=schemas.PeerEvaluationSessionListResponse)
async def list_peer_evaluation_sessions(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    rows = await peer_eval_crud.list_sessions_by_professor(
        db,
        professor_user_id=professor.id,
    )

    return schemas.PeerEvaluationSessionListResponse(
        items=[
            schemas.PeerEvaluationSessionListItem(
                id=session.id,
                title=session.title,
                is_open=session.is_open,
                created_at=session.created_at,
                updated_at=session.updated_at,
                member_count=member_count,
                submitted_evaluators=submitted_evaluators,
            )
            for session, member_count, submitted_evaluators in rows
        ],
        total=len(rows),
    )


@router.post(
    "/peer-reviews/sessions/{session_id}/members:parse",
    response_model=schemas.PeerEvaluationSessionMembersParseResponse,
)
@router.post(
    "/peer-evaluations/sessions/{session_id}/members:parse",
    response_model=schemas.PeerEvaluationSessionMembersParseResponse,
)
async def parse_peer_evaluation_members(
    session_id: int,
    payload: schemas.PeerEvaluationSessionMembersParseRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    copilot: CopilotClient = Depends(get_copilot_client),
):
    professor = await _get_professor_or_403(request, db)
    await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )

    parsed_teams = await _parse_team_text_with_copilot(raw_text=payload.raw_text, copilot=copilot)
    students = await _list_student_users(db)
    teams, unresolved = _map_parsed_teams_to_students(parsed_teams=parsed_teams, students=students)

    return schemas.PeerEvaluationSessionMembersParseResponse(
        teams=teams,
        unresolved_members=unresolved,
    )


@router.post(
    "/peer-reviews/sessions/{session_id}/members:confirm",
    response_model=schemas.PeerEvaluationSessionMembersConfirmResponse,
)
@router.post(
    "/peer-evaluations/sessions/{session_id}/members:confirm",
    response_model=schemas.PeerEvaluationSessionMembersConfirmResponse,
)
async def confirm_peer_evaluation_members(
    session_id: int,
    payload: schemas.PeerEvaluationSessionMembersConfirmRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )

    if payload.unresolved_members:
        raise HTTPException(
            status_code=400,
            detail="Unresolved members must be resolved before confirmation",
        )

    if not payload.members:
        raise HTTPException(status_code=400, detail="At least one member is required")

    dedupe_ids: set[int] = set()
    normalized_members: list[tuple[int, str]] = []
    for member in payload.members:
        if member.student_user_id in dedupe_ids:
            raise HTTPException(status_code=400, detail="Duplicate student in members")
        dedupe_ids.add(member.student_user_id)

        team_label = member.team_label.strip()
        if not team_label:
            raise HTTPException(status_code=400, detail="Team label is required")
        normalized_members.append((member.student_user_id, team_label))

    await peer_eval_crud.replace_session_members(
        db,
        session_id=session_id,
        members=normalized_members,
    )

    rows = await peer_eval_crud.list_session_members(db, session_id=session_id)
    response_members = [
        schemas.PeerEvaluationSessionMemberItem(
            student_user_id=user.id,
            student_name=user.name or user.email,
            student_email=user.email,
            team_label=member.team_label,
        )
        for member, user in rows
    ]

    return schemas.PeerEvaluationSessionMembersConfirmResponse(
        session_id=session_id,
        members=response_members,
    )


@router.get("/peer-reviews/sessions/{session_id}", response_model=schemas.PeerEvaluationSessionResponse)
@router.get("/peer-evaluations/sessions/{session_id}", response_model=schemas.PeerEvaluationSessionResponse)
async def get_peer_evaluation_session(
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

    rows = await peer_eval_crud.list_session_members(db, session_id=session.id)
    members = [
        schemas.PeerEvaluationSessionMemberItem(
            student_user_id=user.id,
            student_name=user.name or user.email,
            student_email=user.email,
            team_label=member.team_label,
        )
        for member, user in rows
    ]

    return schemas.PeerEvaluationSessionResponse(
        id=session.id,
        title=session.title,
        raw_text=_build_raw_text_from_members(members),
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        access_token=session.access_token,
        form_url=_build_form_url(session.access_token),
        created_at=session.created_at,
        updated_at=session.updated_at,
        members=members,
    )


@router.patch("/peer-reviews/sessions/{session_id}", response_model=schemas.PeerEvaluationSessionResponse)
@router.patch("/peer-evaluations/sessions/{session_id}", response_model=schemas.PeerEvaluationSessionResponse)
async def update_peer_evaluation_session(
    session_id: int,
    payload: schemas.PeerEvaluationSessionUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )

    session = await peer_eval_crud.update_session(
        db,
        session=session,
        title=payload.title,
    )

    rows = await peer_eval_crud.list_session_members(db, session_id=session.id)
    members = [
        schemas.PeerEvaluationSessionMemberItem(
            student_user_id=user.id,
            student_name=user.name or user.email,
            student_email=user.email,
            team_label=member.team_label,
        )
        for member, user in rows
    ]

    return schemas.PeerEvaluationSessionResponse(
        id=session.id,
        title=session.title,
        raw_text=_build_raw_text_from_members(members),
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        access_token=session.access_token,
        form_url=_build_form_url(session.access_token),
        created_at=session.created_at,
        updated_at=session.updated_at,
        members=members,
    )


@router.delete("/peer-reviews/sessions/{session_id}", response_model=schemas.MessageResponse)
@router.delete("/peer-evaluations/sessions/{session_id}", response_model=schemas.MessageResponse)
async def delete_peer_evaluation_session(
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

    await peer_eval_crud.delete_session(db, session=session)
    return schemas.MessageResponse(message="Deleted")


@router.patch("/peer-reviews/sessions/{session_id}/status", response_model=schemas.PeerEvaluationSessionResponse)
@router.patch("/peer-evaluations/sessions/{session_id}/status", response_model=schemas.PeerEvaluationSessionResponse)
async def update_peer_evaluation_session_status(
    session_id: int,
    payload: schemas.PeerEvaluationSessionStatusUpdateRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    session = await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )

    session = await peer_eval_crud.update_session_is_open(
        db,
        session=session,
        is_open=payload.is_open,
    )

    rows = await peer_eval_crud.list_session_members(db, session_id=session.id)
    members = [
        schemas.PeerEvaluationSessionMemberItem(
            student_user_id=user.id,
            student_name=user.name or user.email,
            student_email=user.email,
            team_label=member.team_label,
        )
        for member, user in rows
    ]

    event_payload = {
        "session_id": int(session.id),
        "is_open": bool(session.is_open),
        "updated_at": session.updated_at.isoformat(),
    }
    for member_user_id in {member.student_user_id for member, _ in rows}:
        await notification_registry.send_to_user(
            int(member_user_id),
            {
                "event": "peer_evaluation_session_status",
                "data": json.dumps(event_payload, ensure_ascii=False),
            },
        )

    return schemas.PeerEvaluationSessionResponse(
        id=session.id,
        title=session.title,
        raw_text=_build_raw_text_from_members(members),
        professor_user_id=session.professor_user_id,
        is_open=session.is_open,
        access_token=session.access_token,
        form_url=_build_form_url(session.access_token),
        created_at=session.created_at,
        updated_at=session.updated_at,
        members=members,
    )


@router.get(
    "/peer-reviews/sessions/{session_id}/progress",
    response_model=schemas.PeerEvaluationSessionProgressResponse,
)
@router.get(
    "/peer-evaluations/sessions/{session_id}/progress",
    response_model=schemas.PeerEvaluationSessionProgressResponse,
)
async def get_peer_evaluation_session_progress(
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

    rows = await peer_eval_crud.list_session_progress_rows(db, session_id=session.id)

    return schemas.PeerEvaluationSessionProgressResponse(
        session_id=session.id,
        is_open=session.is_open,
        evaluator_statuses=[
            schemas.PeerEvaluationSessionProgressItem(
                evaluator_user_id=user.id,
                evaluator_name=user.name or user.email,
                evaluator_email=user.email,
                team_label=member.team_label,
                has_submitted=has_submitted,
            )
            for member, user, has_submitted in rows
        ],
    )


@router.get(
    "/peer-reviews/sessions/{session_id}/results",
    response_model=schemas.PeerEvaluationSessionResultsResponse,
)
@router.get(
    "/peer-evaluations/sessions/{session_id}/results",
    response_model=schemas.PeerEvaluationSessionResultsResponse,
)
async def get_peer_evaluation_results(
    session_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    professor = await _get_professor_or_403(request, db)
    await _get_professor_session_or_404(
        db,
        session_id=session_id,
        professor_user_id=professor.id,
    )

    rows = await peer_eval_crud.list_submission_rows_for_session(db, session_id=session_id)
    serialized_rows = [
        schemas.PeerEvaluationSubmissionRow(
            evaluator_user_id=evaluator.id,
            evaluator_name=evaluator.name or evaluator.email,
            evaluatee_user_id=evaluatee.id,
            evaluatee_name=evaluatee.name or evaluatee.email,
            contribution_percent=submission.contribution_percent,
            fit_yes_no=submission.fit_yes_no,
            updated_at=submission.updated_at,
        )
        for submission, evaluator, evaluatee in rows
    ]

    submitted_count = await peer_eval_crud.count_submitted_evaluators(db, session_id=session_id)
    contribution_avg_by_evaluatee, fit_yes_ratio_by_evaluatee, fit_yes_ratio_by_evaluator = peer_eval_crud.build_session_result_stats(rows)

    return schemas.PeerEvaluationSessionResultsResponse(
        session_id=session_id,
        total_evaluators_submitted=submitted_count,
        total_rows=len(serialized_rows),
        rows=serialized_rows,
        contribution_avg_by_evaluatee=contribution_avg_by_evaluatee,
        fit_yes_ratio_by_evaluatee=fit_yes_ratio_by_evaluatee,
        fit_yes_ratio_by_evaluator=fit_yes_ratio_by_evaluator,
    )


async def _get_session_and_member_by_token(
    db: AsyncSession,
    *,
    token: str,
    user_id: int,
) -> tuple[Any, Any]:
    session = await peer_eval_crud.get_session_by_access_token(db, token)
    if session is None:
        raise HTTPException(status_code=404, detail="Peer evaluation form not found")

    member = await peer_eval_crud.get_member(
        db,
        session_id=session.id,
        student_user_id=user_id,
    )
    if member is None:
        raise HTTPException(status_code=403, detail="You are not assigned to this session")

    return session, member


@router.get("/peer-reviews/forms/{token}", response_model=schemas.PeerEvaluationFormResponse)
@router.get("/peer-evaluations/forms/{token}", response_model=schemas.PeerEvaluationFormResponse)
async def get_peer_evaluation_form(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_logged_in_user_or_401(request, db)
    session, member = await _get_session_and_member_by_token(db, token=token, user_id=user.id)

    team_users = await peer_eval_crud.list_team_member_users(
        db,
        session_id=session.id,
        team_label=member.team_label,
    )

    submitted_ids = await peer_eval_crud.list_submitted_evaluator_ids(
        db,
        session_id=session.id,
        evaluator_ids=[team_user.id for team_user in team_users],
    )

    evaluator_statuses = [
        schemas.PeerEvaluationEvaluatorStatusItem(
            evaluator_user_id=team_user.id,
            evaluator_name=team_user.name or team_user.email,
            has_submitted=team_user.id in submitted_ids,
        )
        for team_user in team_users
    ]

    return schemas.PeerEvaluationFormResponse(
        session=schemas.PeerEvaluationFormSessionInfo(
            session_id=session.id,
            title=session.title,
            is_open=session.is_open,
        ),
        me=schemas.TeamMemberSummary(
            id=user.id,
            name=user.name or user.email,
            email=user.email,
            picture=user.picture,
        ),
        team_members=[
            schemas.TeamMemberSummary(
                id=team_user.id,
                name=team_user.name or team_user.email,
                email=team_user.email,
                picture=team_user.picture,
            )
            for team_user in team_users
        ],
        evaluator_statuses=evaluator_statuses,
        has_submitted=user.id in submitted_ids,
    )


@router.post("/peer-reviews/forms/{token}/submit", response_model=schemas.MessageResponse)
@router.post("/peer-evaluations/forms/{token}/submit", response_model=schemas.MessageResponse)
async def submit_peer_evaluation_form(
    token: str,
    payload: schemas.PeerEvaluationFormSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_logged_in_user_or_401(request, db)
    session, member = await _get_session_and_member_by_token(db, token=token, user_id=user.id)

    if not session.is_open:
        raise HTTPException(status_code=409, detail="Session is closed")

    team_users = await peer_eval_crud.list_team_member_users(
        db,
        session_id=session.id,
        team_label=member.team_label,
    )
    team_user_ids = {team_user.id for team_user in team_users}

    if len(payload.entries) != len(team_user_ids):
        raise HTTPException(status_code=400, detail="All team members must be evaluated exactly once")

    seen_evaluatee_ids: set[int] = set()
    total = 0
    entries: list[tuple[int, int, bool]] = []
    for entry in payload.entries:
        if entry.evaluatee_user_id not in team_user_ids:
            raise HTTPException(status_code=400, detail="Evaluatee must be in same session team")
        if entry.evaluatee_user_id in seen_evaluatee_ids:
            raise HTTPException(status_code=400, detail="Duplicate evaluatee in entries")

        seen_evaluatee_ids.add(entry.evaluatee_user_id)
        total += int(entry.contribution_percent)
        entries.append((entry.evaluatee_user_id, int(entry.contribution_percent), bool(entry.fit_yes_no)))

    if total != 100:
        raise HTTPException(status_code=400, detail="Contribution percent sum must be exactly 100")

    await peer_eval_crud.upsert_submission_entries(
        db,
        session_id=session.id,
        evaluator_user_id=user.id,
        entries=entries,
    )

    await notification_registry.send_to_user(
        int(session.professor_user_id),
        {
            "event": "peer_evaluation_progress_updated",
            "data": json.dumps(
                {
                    "session_id": int(session.id),
                    "evaluator_user_id": int(user.id),
                    "updated_at": session.updated_at.isoformat(),
                },
                ensure_ascii=False,
            ),
        },
    )

    return {"message": "Submitted"}


@router.get("/peer-reviews/forms/{token}/my-summary", response_model=schemas.PeerEvaluationMySummaryResponse)
@router.get("/peer-evaluations/forms/{token}/my-summary", response_model=schemas.PeerEvaluationMySummaryResponse)
async def get_peer_evaluation_my_summary(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user = await _get_logged_in_user_or_401(request, db)
    session, _ = await _get_session_and_member_by_token(db, token=token, user_id=user.id)

    summary = await peer_eval_crud.build_summary_for_user(
        db,
        session_id=session.id,
        user_id=user.id,
    )

    return schemas.PeerEvaluationMySummaryResponse(
        session_id=session.id,
        my_received_contribution_avg=summary["my_received_contribution_avg"],
        my_given_contribution_avg=summary["my_given_contribution_avg"],
        my_fit_yes_ratio_received=summary["my_fit_yes_ratio_received"],
        my_fit_yes_ratio_given=summary["my_fit_yes_ratio_given"],
    )
