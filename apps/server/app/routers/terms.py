from typing import List
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse

from app.database import get_db
from app.models import User as UserModel
from app.schemas import TermResponse, ConsentCreate, MessageResponse
from app.dependencies import get_current_user, get_active_user, verify_csrf
from app.limiter import limiter
from app.core.config import settings
from app import crud

router = APIRouter(dependencies=[Depends(verify_csrf)])


@router.get("/terms", summary="약관 조회", response_model=List[TermResponse])
@limiter.limit(settings.TERMS_LIMIT)
async def get_terms(request: Request, db: AsyncSession = Depends(get_db)):
    return await crud.get_active_terms(db)


@router.post("/consents", summary="약관 동의", response_model=MessageResponse)
@limiter.limit(settings.CONSENTS_LIMIT)
async def create_consent(
    consent: ConsentCreate,
    request: Request,
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # 1. 사용자 확인
    user_email = user.get("email")
    if not user_email:
        raise HTTPException(status_code=401, detail="Not authenticated")

    db_user = await crud.get_user_by_email(db, user_email)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # 2. 약관 존재 확인
    term = await crud.get_term_by_id(db, consent.term_id)
    if not term:
        raise HTTPException(status_code=404, detail="Term not found")

    # 3. 이미 동의했는지 확인
    existing_consent = await crud.get_consent(db, db_user.id, consent.term_id)
    if existing_consent:
        return JSONResponse({"message": "Consent already recorded"})

    # 4. 동의 저장
    await crud.create_consent(db, db_user.id, consent.term_id)

    return JSONResponse({"message": "Consent recorded"})
