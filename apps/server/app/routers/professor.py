from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.database import get_db
from app.dependencies import verify_csrf
from app.routers import snippet_utils

router = APIRouter(prefix="/professor", tags=["professor"], dependencies=[Depends(verify_csrf)])


def _assert_student_user_or_404(user) -> None:
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if not crud.is_student_user(user):
        raise HTTPException(status_code=404, detail="Student not found")


@router.get("/overview", response_model=schemas.ProfessorOverviewResponse)
async def get_professor_overview(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await snippet_utils.get_viewer_or_401(request, db, include_consents=False)
    await crud.ensure_latest_snapshots_for_all_students(db)
    return await crud.build_overview_counts(db)


@router.get("/risk-queue", response_model=schemas.ProfessorRiskQueueResponse)
async def get_professor_risk_queue(
    request: Request,
    limit: int = Query(30, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    await snippet_utils.get_viewer_or_401(request, db, include_consents=False)
    await crud.ensure_latest_snapshots_for_all_students(db)
    items = await crud.build_risk_queue(db, limit=limit)
    return {
        "items": items,
        "total": len(items),
    }


@router.get("/students/{user_id}/risk-history", response_model=schemas.ProfessorRiskHistoryResponse)
async def get_professor_student_risk_history(
    user_id: int,
    request: Request,
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    await snippet_utils.get_viewer_or_401(request, db, include_consents=False)
    user = await crud.get_user_by_id(db, user_id)
    _assert_student_user_or_404(user)

    await crud.ensure_latest_snapshot_for_user(db, user_id)
    items = await crud.build_risk_history_payload(db, user_id, limit=limit)
    return {
        "items": items,
        "total": len(items),
    }


@router.post("/students/{user_id}/risk-evaluate", response_model=schemas.ProfessorRiskEvaluateResponse)
async def evaluate_professor_student_risk(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    await snippet_utils.get_viewer_or_401(request, db, include_consents=False)
    user = await crud.get_user_by_id(db, user_id)
    _assert_student_user_or_404(user)

    snapshot = await crud.evaluate_student_and_create_snapshot(db, user_id)
    return {
        "snapshot": snapshot,
    }
