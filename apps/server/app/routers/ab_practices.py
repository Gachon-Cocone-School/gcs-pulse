from __future__ import annotations

import random
import secrets
import uuid
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import schemas
from app.core.config import settings
from app.database import AsyncSessionLocal
from app.dependencies import load_session_user_or_401, require_professor_role, verify_csrf
from app.models import (
    ABPracticeAnonymousExposure,
    ABPracticeAnonymousParticipant,
    ABPracticeExposure,
    ABPracticePair,
    ABPracticeSession,
    User,
)

router = APIRouter(tags=["ab-practice"], dependencies=[Depends(verify_csrf)])

MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_SESSION_WARM_BYTES = 64 * 1024 * 1024
WARM_READ_CHUNK_BYTES = 1024 * 1024
ALLOWED_IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
UPLOAD_DIR = Path(
    settings.AB_PRACTICE_UPLOAD_DIR
    or Path(__file__).resolve().parents[2] / "data" / "ab-practice"
).expanduser()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _upload_url(token: str) -> str:
    return f"{settings.AUTH_SUCCESS_URL.rstrip('/')}/ab-practice/upload/{token}"


def _test_url(token: str) -> str:
    return f"{settings.AUTH_SUCCESS_URL.rstrip('/')}/ab-practice/test/{token}"


def _asset_url(token: str, pair_id: int, slot: str, updated_at: datetime) -> str:
    version = updated_at.strftime("%Y%m%dT%H%M%S%f")
    return f"/ab-practices/assets/{token}/{pair_id}/{slot}?v={version}"


def _warm_image_files(paths: list[str]) -> None:
    """Touch a bounded amount of session image data to warm the OS file cache."""
    remaining = MAX_SESSION_WARM_BYTES
    for image_path in paths:
        if remaining <= 0:
            break
        try:
            with Path(image_path).open("rb") as image_file:
                while remaining > 0:
                    chunk = image_file.read(min(WARM_READ_CHUNK_BYTES, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
        except OSError:
            continue


def _mime_from_bytes(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if len(data) >= 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


async def _read_image(upload: UploadFile) -> tuple[bytes, str]:
    data = await upload.read(MAX_IMAGE_BYTES + 1)
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise HTTPException(status_code=413, detail="이미지는 8MB 이하로 올려 주세요.")
    mime_type = _mime_from_bytes(data)
    if mime_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="JPG, PNG, WebP 이미지만 올릴 수 있습니다.")
    return data, ALLOWED_IMAGE_TYPES[mime_type]


async def _get_user(request: Request, db: AsyncSession) -> User:
    return await load_session_user_or_401(request, db, basic=True)


def _is_session_professor(user: User, session: ABPracticeSession) -> bool:
    return "교수" in (user.roles or []) and session.professor_user_id == user.id


async def _pair_for_management(
    db: AsyncSession,
    session: ABPracticeSession,
    pair_id: int,
    user: User,
) -> ABPracticePair:
    pair = await db.scalar(select(ABPracticePair).where(
        ABPracticePair.id == pair_id,
        ABPracticePair.session_id == session.id,
    ))
    if pair is None:
        raise HTTPException(status_code=404, detail="A/B 테스트 항목을 찾을 수 없습니다.")
    if not _is_session_professor(user, session) and pair.created_by_user_id != user.id:
        raise HTTPException(status_code=403, detail="본인이 등록한 A/B 테스트 항목만 수정하거나 삭제할 수 있습니다.")
    if not _registration_is_open(session):
        raise HTTPException(status_code=409, detail="등록 기간이 아닙니다.")
    return pair


async def _create_pair(
    db: AsyncSession,
    session: ABPracticeSession,
    user: User,
    title: str,
    image_a_bytes: bytes,
    image_a_ext: str,
    image_b_bytes: bytes,
    image_b_ext: str,
) -> ABPracticePair:
    if not _registration_is_open(session):
        raise HTTPException(status_code=409, detail="등록 기간이 아닙니다.")
    title = title.strip()
    if not title or len(title) > 200:
        raise HTTPException(status_code=422, detail="항목 제목은 1자 이상 200자 이하여야 합니다.")
    next_slot = await db.scalar(select(func.max(ABPracticePair.slot_number)).where(
        ABPracticePair.session_id == session.id,
        ABPracticePair.team_label == "전체",
    ))
    pair = ABPracticePair(
        session_id=session.id,
        title=title,
        team_label="전체",
        slot_number=(next_slot or 0) + 1,
        image_a_path="pending",
        image_b_path="pending",
        created_by_user_id=user.id,
    )
    db.add(pair)
    await db.flush()
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    image_a_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{image_a_ext}"
    image_b_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{image_b_ext}"
    image_a_path.write_bytes(image_a_bytes)
    image_b_path.write_bytes(image_b_bytes)
    pair.image_a_path = str(image_a_path)
    pair.image_b_path = str(image_b_path)
    session.updated_at = _now()
    await db.commit()
    await db.refresh(pair)
    return pair


async def _get_professor(request: Request, db: AsyncSession) -> User:
    user = await _get_user(request, db)
    require_professor_role(user)
    return user


async def _get_session_by_token(db: AsyncSession, token: str) -> ABPracticeSession:
    session = await db.scalar(select(ABPracticeSession).where(ABPracticeSession.access_token == token))
    if session is None:
        raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
    return session


def _participant_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _get_anonymous_participant(
    request: Request, db: AsyncSession, session: ABPracticeSession,
) -> ABPracticeAnonymousParticipant:
    raw_token = request.headers.get("x-ab-participant-token", "")
    if len(raw_token) < 32 or len(raw_token) > 128:
        raise HTTPException(status_code=401, detail="참여자 정보를 확인할 수 없습니다.")
    participant = await db.scalar(select(ABPracticeAnonymousParticipant).where(
        ABPracticeAnonymousParticipant.session_id == session.id,
        ABPracticeAnonymousParticipant.token_hash == _participant_token_hash(raw_token),
    ))
    if participant is None:
        raise HTTPException(status_code=401, detail="참여자 정보를 확인할 수 없습니다.")
    return participant


async def _get_professor_session(db: AsyncSession, session_id: int, professor_id: int) -> ABPracticeSession:
    session = await db.scalar(select(ABPracticeSession).where(
        ABPracticeSession.id == session_id,
        ABPracticeSession.professor_user_id == professor_id,
    ))
    if session is None:
        raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
    return session


def _pair_response(
    pair: ABPracticePair,
    token: str,
    submitter_name: str,
    *,
    can_manage: bool = False,
) -> schemas.ABPracticePairResponse:
    return schemas.ABPracticePairResponse(
        id=pair.id,
        title=pair.title,
        submitter_name=submitter_name,
        image_a_url=_asset_url(token, pair.id, "a", pair.updated_at) if pair.image_a_path else None,
        image_b_url=_asset_url(token, pair.id, "b", pair.updated_at) if pair.image_b_path else None,
        complete=bool(pair.image_a_path and pair.image_b_path),
        can_manage=can_manage,
        created_at=pair.created_at,
    )


def _session_status(session: ABPracticeSession) -> str:
    # Older local databases may still contain the former terminal state.
    # Expose it as the reusable pre-test state so registration can be reopened.
    if session.status in {"registration_voting", "registration_ended"}:
        return "registration_open"
    return "setup" if session.status == "registration_closed" else session.status


def _registration_is_open(session: ABPracticeSession) -> bool:
    return session.status in {"registration_open", "registration_voting", "registration_ended"}


def _session_response(session: ABPracticeSession) -> schemas.ABPracticeSessionResponse:
    return schemas.ABPracticeSessionResponse(
        id=session.id,
        title=session.title,
        question=session.question,
        exposure_seconds=session.exposure_seconds,
        status=_session_status(session),
        access_token=session.access_token,
        upload_url=_upload_url(session.access_token),
        test_url=_test_url(session.access_token),
    )


@router.post("/ab-practices/sessions", response_model=schemas.ABPracticeSessionResponse)
async def create_session(payload: schemas.ABPracticeCreateRequest, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = ABPracticeSession(
            title=payload.title,
            professor_user_id=professor.id,
            access_token=secrets.token_urlsafe(24),
            question=payload.question,
            exposure_seconds=payload.exposure_seconds,
            status="setup",
        )
        db.add(session)
        await db.flush()
        await db.commit()
        await db.refresh(session)
        return _session_response(session)


@router.get("/ab-practices/sessions")
async def list_sessions(request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        rows = await db.execute(
            select(ABPracticeSession, func.count(ABPracticePair.id))
            .outerjoin(ABPracticePair, ABPracticePair.session_id == ABPracticeSession.id)
            .where(ABPracticeSession.professor_user_id == professor.id)
            .group_by(ABPracticeSession.id)
            .order_by(ABPracticeSession.updated_at.desc(), ABPracticeSession.id.desc())
        )
        completed_participants = (
            select(
                ABPracticeExposure.session_id.label("session_id"),
                ABPracticeExposure.student_user_id.label("student_user_id"),
            )
            .group_by(ABPracticeExposure.session_id, ABPracticeExposure.student_user_id)
            .having(func.count(ABPracticeExposure.id) == func.count(ABPracticeExposure.choice))
            .subquery()
        )
        submitted_rows = await db.execute(
            select(completed_participants.c.session_id, func.count())
            .group_by(completed_participants.c.session_id)
        )
        submission_counts = {session_id: count for session_id, count in submitted_rows.all()}
        completed_anonymous_participants = (
            select(
                ABPracticeAnonymousExposure.session_id.label("session_id"),
                ABPracticeAnonymousExposure.participant_id.label("participant_id"),
            )
            .group_by(ABPracticeAnonymousExposure.session_id, ABPracticeAnonymousExposure.participant_id)
            .having(func.count(ABPracticeAnonymousExposure.id) == func.count(ABPracticeAnonymousExposure.choice))
            .subquery()
        )
        anonymous_submitted_rows = await db.execute(
            select(completed_anonymous_participants.c.session_id, func.count())
            .group_by(completed_anonymous_participants.c.session_id)
        )
        for session_id, count in anonymous_submitted_rows.all():
            submission_counts[session_id] = submission_counts.get(session_id, 0) + count
        return {"items": [{
            "id": session.id,
            "title": session.title,
            "status": _session_status(session),
            "pair_count": int(member_count),
            "submission_count": int(submission_counts.get(session.id, 0)),
            "created_at": session.created_at,
            "updated_at": session.updated_at,
        } for session, member_count in rows.all()]}


@router.get("/ab-practices/sessions/{session_id}", response_model=schemas.ABPracticeSessionResponse)
async def get_session(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        return _session_response(session)


@router.patch("/ab-practices/sessions/{session_id}", response_model=schemas.ABPracticeSessionResponse)
async def update_session(session_id: int, payload: schemas.ABPracticeCreateRequest, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        session.title = payload.title
        session.question = payload.question
        session.exposure_seconds = payload.exposure_seconds
        session.updated_at = _now()
        await db.commit()
        await db.refresh(session)
        return _session_response(session)


@router.delete("/ab-practices/sessions/{session_id}", response_model=schemas.MessageResponse)
async def delete_session(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        image_paths = list((await db.execute(
            select(ABPracticePair.image_a_path, ABPracticePair.image_b_path)
            .where(ABPracticePair.session_id == session.id)
        )).all())
        await db.delete(session)
        await db.commit()
    for image_a_path, image_b_path in image_paths:
        for image_path in (image_a_path, image_b_path):
            if image_path:
                Path(image_path).unlink(missing_ok=True)
    return schemas.MessageResponse(message="Deleted")


@router.post("/ab-practices/sessions/{session_id}/registration:start", response_model=schemas.ABPracticeSessionResponse)
async def start_registration(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        if not _registration_is_open(session):
            return_to = "voting_open" if session.status == "voting_open" else "ended" if session.status == "ended" else "setup"
            session.status = f"registration_{return_to.split('_')[0]}" if return_to != "setup" else "registration_open"
        session.updated_at = _now()
        await db.commit()
        await db.refresh(session)
        return _session_response(session)


@router.post("/ab-practices/sessions/{session_id}/registration:end", response_model=schemas.ABPracticeSessionResponse)
async def end_registration(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        if not _registration_is_open(session):
            raise HTTPException(status_code=409, detail="종료할 수 있는 이미지 등록이 없습니다.")
        if session.status == "registration_voting":
            session.status = "voting_open"
        elif session.status == "registration_ended":
            session.status = "ended"
        else:
            session.status = "setup"
        session.updated_at = _now()
        await db.commit()
        await db.refresh(session)
        return _session_response(session)


@router.get("/ab-practices/upload/{token}", response_model=schemas.ABPracticeUploadResponse)
async def get_upload(token: str, request: Request):
    async with AsyncSessionLocal() as db:
        user = await _get_user(request, db)
        session = await _get_session_by_token(db, token)
        rows = await db.execute(
            select(ABPracticePair, User).join(User, User.id == ABPracticePair.created_by_user_id)
            .where(ABPracticePair.session_id == session.id)
            .order_by(ABPracticePair.slot_number, ABPracticePair.id)
        )
        return schemas.ABPracticeUploadResponse(
            session_id=session.id,
            title=session.title,
            status=_session_status(session),
            pairs=[_pair_response(
                pair, token, submitter.name or submitter.email,
                can_manage=_is_session_professor(user, session) or pair.created_by_user_id == user.id,
            ) for pair, submitter in rows.all()],
        )


async def _create_pair_from_upload(
    session: ABPracticeSession,
    user: User,
    db: AsyncSession,
    token: str,
    title: str,
    image_a: UploadFile,
    image_b: UploadFile,
) -> schemas.ABPracticePairResponse:
    image_a_bytes, image_a_ext = await _read_image(image_a)
    image_b_bytes, image_b_ext = await _read_image(image_b)
    pair = await _create_pair(
        db, session, user, title, image_a_bytes, image_a_ext, image_b_bytes, image_b_ext,
    )
    return _pair_response(pair, token, user.name or user.email, can_manage=True)


@router.post("/ab-practices/upload/{token}/pairs", response_model=schemas.ABPracticePairResponse)
async def create_pair(
    token: str,
    request: Request,
    title: str = Form(...),
    image_a: UploadFile = File(...),
    image_b: UploadFile = File(...),
):
    async with AsyncSessionLocal() as db:
        user = await _get_user(request, db)
        session = await db.scalar(select(ABPracticeSession).where(
            ABPracticeSession.access_token == token,
        ).with_for_update())
        if session is None:
            raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
        return await _create_pair_from_upload(session, user, db, token, title, image_a, image_b)


@router.post("/ab-practices/sessions/{session_id}/pairs", response_model=schemas.ABPracticePairResponse)
async def professor_create_pair(
    session_id: int,
    request: Request,
    title: str = Form(...),
    image_a: UploadFile = File(...),
    image_b: UploadFile = File(...),
):
    async with AsyncSessionLocal() as db:
        user = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, user.id)
        session = await db.scalar(select(ABPracticeSession).where(
            ABPracticeSession.id == session.id,
        ).with_for_update())
        if session is None:
            raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
        return await _create_pair_from_upload(session, user, db, session.access_token, title, image_a, image_b)


async def _replace_pair_image(
    session: ABPracticeSession, pair_id: int, slot: str, user: User,
    db: AsyncSession, image: UploadFile,
) -> schemas.ABPracticePairResponse:
    if slot not in {"a", "b"}:
        raise HTTPException(status_code=422, detail="이미지 구분이 올바르지 않습니다.")
    pair = await _pair_for_management(db, session, pair_id, user)
    previous_exposures = list((await db.scalars(select(ABPracticeExposure).where(
        ABPracticeExposure.pair_id == pair.id,
    ))).all())
    for exposure in previous_exposures:
        await db.delete(exposure)
    previous_anonymous_exposures = list((await db.scalars(select(ABPracticeAnonymousExposure).where(
        ABPracticeAnonymousExposure.pair_id == pair.id,
    ))).all())
    for exposure in previous_anonymous_exposures:
        await db.delete(exposure)
    image_bytes, extension = await _read_image(image)
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    new_path = UPLOAD_DIR / f"{uuid.uuid4().hex}{extension}"
    new_path.write_bytes(image_bytes)
    old_path_value = pair.image_a_path if slot == "a" else pair.image_b_path
    if slot == "a":
        pair.image_a_path = str(new_path)
    else:
        pair.image_b_path = str(new_path)
    pair.updated_at = _now()
    session.updated_at = _now()
    await db.commit()
    await db.refresh(pair)
    if old_path_value:
        Path(old_path_value).unlink(missing_ok=True)
    submitter = await db.get(User, pair.created_by_user_id)
    return _pair_response(
        pair, session.access_token, submitter.name or submitter.email if submitter else "알 수 없음",
        can_manage=True,
    )


@router.put("/ab-practices/upload/{token}/pairs/{pair_id}/{slot}", response_model=schemas.ABPracticePairResponse)
async def replace_pair_image(
    token: str, pair_id: int, slot: str, request: Request, image: UploadFile = File(...),
):
    async with AsyncSessionLocal() as db:
        user = await _get_user(request, db)
        session = await _get_session_by_token(db, token)
        return await _replace_pair_image(session, pair_id, slot, user, db, image)


@router.put("/ab-practices/sessions/{session_id}/pairs/{pair_id}/{slot}", response_model=schemas.ABPracticePairResponse)
async def professor_replace_pair_image(
    session_id: int, pair_id: int, slot: str, request: Request, image: UploadFile = File(...),
):
    async with AsyncSessionLocal() as db:
        user = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, user.id)
        return await _replace_pair_image(session, pair_id, slot, user, db, image)


async def _delete_pair(
    session: ABPracticeSession, pair_id: int, user: User, db: AsyncSession,
) -> dict[str, str]:
    pair = await _pair_for_management(db, session, pair_id, user)
    paths = [pair.image_a_path, pair.image_b_path]
    await db.delete(pair)
    session.updated_at = _now()
    await db.commit()
    for path in paths:
        if path:
            Path(path).unlink(missing_ok=True)
    return {"message": "Deleted"}


@router.delete("/ab-practices/upload/{token}/pairs/{pair_id}")
async def delete_pair(token: str, pair_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        user = await _get_user(request, db)
        session = await _get_session_by_token(db, token)
        return await _delete_pair(session, pair_id, user, db)


@router.delete("/ab-practices/sessions/{session_id}/pairs/{pair_id}")
async def professor_delete_pair(session_id: int, pair_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        user = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, user.id)
        return await _delete_pair(session, pair_id, user, db)


async def _delete_pair_image(
    session: ABPracticeSession, pair_id: int, slot: str, user: User, db: AsyncSession,
) -> dict[str, str]:
    if slot not in {"a", "b"}:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    pair = await _pair_for_management(db, session, pair_id, user)
    previous_exposures = list((await db.scalars(select(ABPracticeExposure).where(
        ABPracticeExposure.pair_id == pair.id,
    ))).all())
    for exposure in previous_exposures:
        await db.delete(exposure)
    previous_anonymous_exposures = list((await db.scalars(select(ABPracticeAnonymousExposure).where(
        ABPracticeAnonymousExposure.pair_id == pair.id,
    ))).all())
    for exposure in previous_anonymous_exposures:
        await db.delete(exposure)
    old_path = pair.image_a_path if slot == "a" else pair.image_b_path
    if slot == "a":
        pair.image_a_path = None
    else:
        pair.image_b_path = None
    pair.updated_at = _now()
    session.updated_at = _now()
    await db.commit()
    if old_path:
        Path(old_path).unlink(missing_ok=True)
    return {"message": "Deleted"}


@router.delete("/ab-practices/upload/{token}/pairs/{pair_id}/{slot}")
async def delete_pair_image(token: str, pair_id: int, slot: str, request: Request):
    async with AsyncSessionLocal() as db:
        user = await _get_user(request, db)
        session = await _get_session_by_token(db, token)
        return await _delete_pair_image(session, pair_id, slot, user, db)


@router.delete("/ab-practices/sessions/{session_id}/pairs/{pair_id}/{slot}")
async def professor_delete_pair_image(session_id: int, pair_id: int, slot: str, request: Request):
    async with AsyncSessionLocal() as db:
        user = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, user.id)
        return await _delete_pair_image(session, pair_id, slot, user, db)


@router.post("/ab-practices/sessions/{session_id}/test:start", response_model=schemas.ABPracticeTestStartResponse)
async def start_test(session_id: int, request: Request, background_tasks: BackgroundTasks):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        if session.status == "voting_open" or _registration_is_open(session):
            raise HTTPException(status_code=409, detail="테스트가 이미 진행 중입니다.")
        pair_rows = list((await db.scalars(select(ABPracticePair).where(
            ABPracticePair.session_id == session.id,
            ABPracticePair.image_a_path.is_not(None),
            ABPracticePair.image_b_path.is_not(None),
        ))).all())
        if not pair_rows:
            raise HTTPException(status_code=409, detail="테스트를 시작하려면 완성된 A/B 테스트 항목을 하나 이상 등록해 주세요.")
        image_paths = [
            path
            for pair in pair_rows
            for path in (pair.image_a_path, pair.image_b_path)
            if path
        ]
        session.status = "voting_open"
        session.updated_at = _now()
        await db.commit()
        background_tasks.add_task(_warm_image_files, image_paths)
        return schemas.ABPracticeTestStartResponse(session_id=session.id, status=session.status, test_url=_test_url(session.access_token))


@router.post("/ab-practices/sessions/{session_id}/vote:end")
async def end_vote(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        if session.status != "voting_open":
            raise HTTPException(status_code=409, detail="진행 중인 투표가 없습니다.")
        session.status = "ended"
        session.updated_at = _now()
        await db.commit()
        return {"session_id": session.id, "status": session.status}


@router.get("/ab-practices/sessions/{session_id}/progress", response_model=schemas.ABPracticeProgressResponse)
async def get_progress(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        pair_rows = list((await db.execute(
            select(ABPracticePair, User).join(User, User.id == ABPracticePair.created_by_user_id)
            .where(ABPracticePair.session_id == session.id)
            .order_by(ABPracticePair.slot_number, ABPracticePair.id)
        )).all())
        pairs = [pair for pair, _ in pair_rows if pair.image_a_path and pair.image_b_path]
        pair_items = [schemas.ABPracticeProgressPairItem(
            id=pair.id,
            title=pair.title,
            submitter_name=user.name or user.email,
            image_a_url=_asset_url(session.access_token, pair.id, "a", pair.updated_at) if pair.image_a_path else None,
            image_b_url=_asset_url(session.access_token, pair.id, "b", pair.updated_at) if pair.image_b_path else None,
            complete=bool(pair.image_a_path and pair.image_b_path),
            can_manage=True,
            created_at=pair.created_at,
        ) for pair, user in pair_rows]
        participating_user_ids = select(ABPracticeExposure.student_user_id).where(
            ABPracticeExposure.session_id == session.id,
        ).distinct()
        participating_users = list((await db.scalars(
            select(User)
            .where(User.id.in_(participating_user_ids))
            .order_by(User.name, User.id)
        )).all())
        participants = list((await db.scalars(select(ABPracticeAnonymousParticipant).where(
            ABPracticeAnonymousParticipant.session_id == session.id,
        ).order_by(ABPracticeAnonymousParticipant.serial_number))).all())
        students = []
        total = len(pairs) if _session_status(session) not in {"setup", "registration_open"} else 0
        for participant in participants:
            exposures = list((await db.scalars(select(ABPracticeAnonymousExposure).where(
                ABPracticeAnonymousExposure.session_id == session.id,
                ABPracticeAnonymousExposure.participant_id == participant.id,
            ))).all())
            answered = sum(1 for exposure in exposures if exposure.choice in {"a", "b"})
            completed_count = sum(1 for exposure in exposures if exposure.choice in {"a", "b", "skip"})
            students.append(schemas.ABPracticeStudentProgressItem(
                participant_id=participant.id,
                serial_number=participant.serial_number,
                student_name=participant.name,
                completed=total > 0 and completed_count == total,
                answered_count=answered,
                total_pairs=total,
            ))
        for user in participating_users:
            exposures = list((await db.scalars(select(ABPracticeExposure).where(
                ABPracticeExposure.session_id == session.id,
                ABPracticeExposure.student_user_id == user.id,
            ))).all())
            answered = sum(1 for exposure in exposures if exposure.choice in {"a", "b"})
            completed_count = sum(1 for exposure in exposures if exposure.choice in {"a", "b", "skip"})
            students.append(schemas.ABPracticeStudentProgressItem(
                student_user_id=user.id,
                student_name=user.name or user.email,
                student_email=user.email,
                completed=total > 0 and completed_count == total,
                answered_count=answered,
                total_pairs=total,
            ))
        completed_students = sum(1 for student in students if student.completed)
        return schemas.ABPracticeProgressResponse(
            session_id=session.id,
            status=_session_status(session),
            students=students,
            completed_students=completed_students,
            total_students=len(students),
            pairs=pair_items,
        )


@router.delete("/ab-practices/sessions/{session_id}/participants/{participant_id}/responses", response_model=schemas.MessageResponse)
async def reset_anonymous_participant_responses(session_id: int, participant_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        participant = await db.scalar(select(ABPracticeAnonymousParticipant).where(
            ABPracticeAnonymousParticipant.id == participant_id,
            ABPracticeAnonymousParticipant.session_id == session.id,
        ))
        if participant is None:
            raise HTTPException(status_code=404, detail="참여자를 찾을 수 없습니다.")
        # Remove the participant row as well as its exposures. The progress
        # endpoint lists anonymous participant rows, so clearing only votes
        # leaves a stale participant card on the dashboard.
        await db.delete(participant)
        if session.status == "ended":
            session.status = "voting_open"
        session.updated_at = _now()
        await db.commit()
        return schemas.MessageResponse(message="Participant responses reset")


@router.delete("/ab-practices/sessions/{session_id}/students/{student_user_id}/responses", response_model=schemas.MessageResponse)
async def reset_student_responses(session_id: int, student_user_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        exposures = list((await db.scalars(select(ABPracticeExposure).where(
            ABPracticeExposure.session_id == session.id,
            ABPracticeExposure.student_user_id == student_user_id,
        ).with_for_update())).all())
        for exposure in exposures:
            await db.delete(exposure)
        if session.status == "ended":
            # Resetting a student's responses after closure also reopens the
            # test so that student can immediately take it again. Other
            # students retain their completed exposures.
            session.status = "voting_open"
        session.updated_at = _now()
        await db.commit()
        return schemas.MessageResponse(message="Student responses reset")


@router.get("/ab-practice/upload/{token}", response_model=schemas.ABPracticeUploadResponse)
async def upload_form_alias(token: str, request: Request):
    return await get_upload(token, request)


@router.post("/ab-practice/test/{token}/participants")
async def register_anonymous_participant(
    token: str, payload: schemas.ABPracticeAnonymousParticipantRequest,
):
    async with AsyncSessionLocal() as db:
        session = await db.scalar(select(ABPracticeSession).where(
            ABPracticeSession.access_token == token,
        ).with_for_update())
        if session is None:
            raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
        if session.status == "ended":
            raise HTTPException(status_code=409, detail="테스트가 종료되었습니다.")
        token_hash = _participant_token_hash(payload.participant_token)
        participant = await db.scalar(select(ABPracticeAnonymousParticipant).where(
            ABPracticeAnonymousParticipant.session_id == session.id,
            ABPracticeAnonymousParticipant.token_hash == token_hash,
        ))
        if participant is None:
            for attempt in range(3):
                last_serial = await db.scalar(select(func.max(ABPracticeAnonymousParticipant.serial_number)).where(
                    ABPracticeAnonymousParticipant.session_id == session.id,
                ))
                participant = ABPracticeAnonymousParticipant(
                    session_id=session.id,
                    serial_number=(last_serial or 0) + 1,
                    name=payload.name,
                    token_hash=token_hash,
                )
                db.add(participant)
                try:
                    await db.commit()
                    break
                except IntegrityError:
                    await db.rollback()
                    participant = await db.scalar(select(ABPracticeAnonymousParticipant).where(
                        ABPracticeAnonymousParticipant.session_id == session.id,
                        ABPracticeAnonymousParticipant.token_hash == token_hash,
                    ))
                    if participant is not None:
                        break
                    if attempt == 2:
                        raise HTTPException(status_code=409, detail="참여 등록에 실패했습니다. 다시 시도해 주세요.")
        return {"participant_id": participant.id, "serial_number": participant.serial_number, "name": participant.name}


@router.get("/ab-practice/test/{token}", response_model=schemas.ABPracticeCurrentExposureResponse)
async def get_current_exposure(token: str, request: Request):
    async with AsyncSessionLocal() as db:
        session = await db.scalar(select(ABPracticeSession).where(
            ABPracticeSession.access_token == token,
        ).with_for_update())
        if session is None:
            raise HTTPException(status_code=404, detail="실습을 찾을 수 없습니다.")
        if session.status == "ended":
            return schemas.ABPracticeCurrentExposureResponse(
                session_id=session.id, title=session.title,
                exposure_seconds=session.exposure_seconds, question="", status="ended", total_pairs=0, completed_pairs=0,
            )
        raw_participant_token = request.headers.get("x-ab-participant-token", "")
        participant = None
        if 32 <= len(raw_participant_token) <= 128:
            participant = await db.scalar(select(ABPracticeAnonymousParticipant).where(
                ABPracticeAnonymousParticipant.session_id == session.id,
                ABPracticeAnonymousParticipant.token_hash == _participant_token_hash(raw_participant_token),
            ))
        if participant is None:
            return schemas.ABPracticeCurrentExposureResponse(
                session_id=session.id, title=session.title,
                exposure_seconds=session.exposure_seconds, question="", status="needs_name", total_pairs=0, completed_pairs=0,
            )
        if session.status in {"setup", "registration_closed"} or _registration_is_open(session):
            return schemas.ABPracticeCurrentExposureResponse(
                session_id=session.id, title=session.title,
                exposure_seconds=session.exposure_seconds, question="", status="waiting", total_pairs=0, completed_pairs=0,
            )
        if session.status != "voting_open":
            raise HTTPException(status_code=409, detail="투표가 아직 시작되지 않았습니다.")
        existing_exposures = list((await db.scalars(select(ABPracticeAnonymousExposure).where(
            ABPracticeAnonymousExposure.session_id == session.id,
            ABPracticeAnonymousExposure.participant_id == participant.id,
        ))).all())
        existing_pair_ids = {exposure.pair_id for exposure in existing_exposures}
        pair_rows = list((await db.scalars(select(ABPracticePair).where(
            ABPracticePair.session_id == session.id,
            ABPracticePair.image_a_path.is_not(None),
            ABPracticePair.image_b_path.is_not(None),
            ABPracticePair.id.not_in(existing_pair_ids) if existing_pair_ids else True,
        ))).all())
        random.SystemRandom().shuffle(pair_rows)
        next_sequence = max((exposure.sequence for exposure in existing_exposures), default=0) + 1
        for sequence, pair in enumerate(pair_rows, start=next_sequence):
            db.add(ABPracticeAnonymousExposure(
                session_id=session.id,
                participant_id=participant.id,
                pair_id=pair.id,
                sequence=sequence,
                image_a_is_left=bool(random.getrandbits(1)),
            ))
        if pair_rows:
            await db.commit()
        exposures = list((await db.execute(
            select(ABPracticeAnonymousExposure, ABPracticePair)
            .join(ABPracticePair, ABPracticePair.id == ABPracticeAnonymousExposure.pair_id)
            .where(
                ABPracticeAnonymousExposure.session_id == session.id,
                ABPracticeAnonymousExposure.participant_id == participant.id,
            )
            .order_by(ABPracticeAnonymousExposure.sequence)
        )).all())
        now = _now()
        for index, (exposure, _pair) in enumerate(exposures):
            if exposure.choice is None and exposure.started_at is not None:
                started = exposure.started_at
                if started.tzinfo is None:
                    started = started.replace(tzinfo=timezone.utc)
                if session.exposure_seconds > 0 and now >= started + timedelta(seconds=session.exposure_seconds):
                    exposure.choice = "skip"
                    exposure.responded_at = now
                    await db.commit()
            if exposure.choice is None:
                next_exposure = next(
                    (row for row in exposures[index + 1:] if row[0].choice is None),
                    None,
                )
                return schemas.ABPracticeCurrentExposureResponse(
                    session_id=session.id,
                    title=session.title,
                    exposure_seconds=session.exposure_seconds,
                    question=session.question,
                    status="voting_open",
                    exposure_id=exposure.id,
                    sequence=exposure.sequence,
                    total_pairs=len(exposures),
                    completed_pairs=sum(1 for row, _ in exposures if row.choice is not None),
                    image_a_url=_asset_url(token, exposure.pair_id, "a", _pair.updated_at),
                    image_b_url=_asset_url(token, exposure.pair_id, "b", _pair.updated_at),
                    next_image_a_url=(
                        _asset_url(token, next_exposure[0].pair_id, "a", next_exposure[1].updated_at)
                        if next_exposure else None
                    ),
                    next_image_b_url=(
                        _asset_url(token, next_exposure[0].pair_id, "b", next_exposure[1].updated_at)
                        if next_exposure else None
                    ),
                    image_a_is_left=exposure.image_a_is_left,
                    started_at=exposure.started_at,
                )
        return schemas.ABPracticeCurrentExposureResponse(
            session_id=session.id,
            title=session.title,
            exposure_seconds=session.exposure_seconds,
            question="",
            status="completed",
            total_pairs=len(exposures),
            completed_pairs=len(exposures),
        )


@router.post("/ab-practice/test/{token}/exposures/{exposure_id}/start", response_model=schemas.ABPracticeExposureStartResponse)
async def start_exposure(token: str, exposure_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        session = await _get_session_by_token(db, token)
        participant = await _get_anonymous_participant(request, db, session)
        if session.status != "voting_open":
            raise HTTPException(status_code=409, detail="투표가 진행 중이 아닙니다.")
        exposure = await db.scalar(select(ABPracticeAnonymousExposure).where(
            ABPracticeAnonymousExposure.id == exposure_id,
            ABPracticeAnonymousExposure.session_id == session.id,
            ABPracticeAnonymousExposure.participant_id == participant.id,
        ).with_for_update())
        if exposure is None:
            raise HTTPException(status_code=404, detail="A/B 테스트 항목을 찾을 수 없습니다.")
        if exposure.choice is not None:
            raise HTTPException(status_code=409, detail="이미 응답한 A/B 테스트 항목입니다.")
        current_id = await db.scalar(select(ABPracticeAnonymousExposure.id).where(
            ABPracticeAnonymousExposure.session_id == session.id,
            ABPracticeAnonymousExposure.participant_id == participant.id,
            ABPracticeAnonymousExposure.choice.is_(None),
        ).order_by(ABPracticeAnonymousExposure.sequence).limit(1))
        if current_id != exposure.id:
            raise HTTPException(status_code=409, detail="A/B 테스트 항목 순서가 올바르지 않습니다.")
        if exposure.started_at is None:
            exposure.started_at = _now()
            await db.commit()
        started_at = exposure.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        return schemas.ABPracticeExposureStartResponse(started_at=started_at, exposure_seconds=session.exposure_seconds)


@router.post("/ab-practice/test/{token}/exposures/{exposure_id}/vote")
async def submit_vote(token: str, exposure_id: int, payload: schemas.ABPracticeVoteRequest, request: Request):
    async with AsyncSessionLocal() as db:
        session = await _get_session_by_token(db, token)
        participant = await _get_anonymous_participant(request, db, session)
        if session.status != "voting_open":
            raise HTTPException(status_code=409, detail="투표가 종료되었습니다.")
        exposure = await db.scalar(select(ABPracticeAnonymousExposure).where(
            ABPracticeAnonymousExposure.id == exposure_id,
            ABPracticeAnonymousExposure.session_id == session.id,
            ABPracticeAnonymousExposure.participant_id == participant.id,
        ).with_for_update())
        if exposure is None or exposure.choice is not None or exposure.started_at is None:
            raise HTTPException(status_code=409, detail="현재 투표할 A/B 테스트 항목이 아닙니다.")
        started_at = exposure.started_at
        if started_at.tzinfo is None:
            started_at = started_at.replace(tzinfo=timezone.utc)
        now = _now()
        exposure.choice = (
            payload.choice
            if session.exposure_seconds == 0 or now < started_at + timedelta(seconds=session.exposure_seconds)
            else "skip"
        )
        exposure.responded_at = now
        await db.commit()
        return {"choice": exposure.choice, "status": "saved"}


@router.get("/ab-practices/assets/{token}/{pair_id}/{slot}")
async def get_asset(token: str, pair_id: int, slot: str):
    if slot not in {"a", "b"}:
        raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
    async with AsyncSessionLocal() as db:
        # The unguessable session token is the capability for viewing test
        # assets. Browser image elements cannot reliably attach session cookies
        # across frontend/API origins, so do not require cookie auth here.
        image_path_column = ABPracticePair.image_a_path if slot == "a" else ABPracticePair.image_b_path
        path_value = await db.scalar(
            select(image_path_column)
            .join(ABPracticeSession, ABPracticeSession.id == ABPracticePair.session_id)
            .where(
                ABPracticeSession.access_token == token,
                ABPracticePair.id == pair_id,
            )
        )
        if not path_value:
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
        path = Path(path_value)
        if not path.is_file():
            raise HTTPException(status_code=404, detail="이미지를 찾을 수 없습니다.")
        return FileResponse(path, headers={"Cache-Control": "private, max-age=3600, immutable"})


@router.get("/ab-practices/sessions/{session_id}/results", response_model=schemas.ABPracticeResultsResponse)
async def get_results(session_id: int, request: Request):
    async with AsyncSessionLocal() as db:
        professor = await _get_professor(request, db)
        session = await _get_professor_session(db, session_id, professor.id)
        if session.status != "ended":
            raise HTTPException(status_code=409, detail="교수가 투표를 종료한 뒤 결과를 확인할 수 있습니다.")
        pair_rows = list((await db.execute(
            select(ABPracticePair, User).join(User, User.id == ABPracticePair.created_by_user_id)
            .where(
                ABPracticePair.session_id == session.id,
                ABPracticePair.image_a_path.is_not(None),
                ABPracticePair.image_b_path.is_not(None),
            ).order_by(ABPracticePair.slot_number, ABPracticePair.id)
        )).all())
        participant_ids = set((await db.scalars(select(ABPracticeExposure.student_user_id).where(
            ABPracticeExposure.session_id == session.id,
        ).distinct())).all())
        anonymous_participants = list((await db.scalars(select(ABPracticeAnonymousParticipant).where(
            ABPracticeAnonymousParticipant.session_id == session.id,
        ))).all())
        completed_students = 0
        for participant_id in participant_ids:
            rows = list((await db.scalars(select(ABPracticeExposure).where(
                ABPracticeExposure.session_id == session.id,
                ABPracticeExposure.student_user_id == participant_id,
            ))).all())
            if rows and all(row.choice is not None for row in rows):
                completed_students += 1
        for participant in anonymous_participants:
            rows = list((await db.scalars(select(ABPracticeAnonymousExposure).where(
                ABPracticeAnonymousExposure.session_id == session.id,
                ABPracticeAnonymousExposure.participant_id == participant.id,
            ))).all())
            if rows and all(row.choice is not None for row in rows):
                completed_students += 1
        result_items = []
        for pair, submitter in pair_rows:
            counts = await db.execute(select(
                ABPracticeExposure.choice,
                func.count(ABPracticeExposure.id),
            ).where(
                ABPracticeExposure.session_id == session.id,
                ABPracticeExposure.pair_id == pair.id,
            ).group_by(ABPracticeExposure.choice))
            by_choice = {choice: int(count) for choice, count in counts.all()}
            anonymous_counts = await db.execute(select(
                ABPracticeAnonymousExposure.choice,
                func.count(ABPracticeAnonymousExposure.id),
            ).where(
                ABPracticeAnonymousExposure.session_id == session.id,
                ABPracticeAnonymousExposure.pair_id == pair.id,
            ).group_by(ABPracticeAnonymousExposure.choice))
            for choice, count in anonymous_counts.all():
                by_choice[choice] = by_choice.get(choice, 0) + int(count)
            a_count, b_count = by_choice.get("a", 0), by_choice.get("b", 0)
            total_choices = a_count + b_count
            result_items.append(schemas.ABPracticePairResultItem(
                pair_id=pair.id,
                title=pair.title,
                submitter_name=submitter.name or submitter.email,
                image_a_url=_asset_url(session.access_token, pair.id, "a", pair.updated_at),
                image_b_url=_asset_url(session.access_token, pair.id, "b", pair.updated_at),
                a_count=a_count,
                b_count=b_count,
                skipped_count=by_choice.get("skip", 0),
                a_percent=round(a_count * 100 / total_choices, 1) if total_choices else None,
                b_percent=round(b_count * 100 / total_choices, 1) if total_choices else None,
            ))
        return schemas.ABPracticeResultsResponse(
            session_id=session.id,
            status=_session_status(session),
            total_students=len(participant_ids) + len(anonymous_participants),
            completed_students=completed_students,
            pairs=result_items,
        )
