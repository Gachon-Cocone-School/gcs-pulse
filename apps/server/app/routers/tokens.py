from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud, schemas
from app.core.config import settings
from app.database import get_db
from app.dependencies import get_active_user, verify_csrf
from app.limiter import limiter
from app.models import User

router = APIRouter(prefix="/auth/tokens", tags=["tokens"], dependencies=[Depends(verify_csrf)])


@router.get("", response_model=List[schemas.ApiTokenResponse])
@limiter.limit(settings.TOKENS_LIST_LIMIT)
async def list_tokens(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    """
    List all API tokens for the current user.
    """
    return await crud.list_api_tokens(db, user.id)


@router.post("", response_model=schemas.NewApiTokenResponse)
@limiter.limit(settings.TOKENS_WRITE_LIMIT)
async def create_token(
    payload: schemas.ApiTokenCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
    idempotency_key: Optional[str] = Header(None, alias='Idempotency-Key'),
):
    """
    Create a new API token. The raw token is returned only once.
    """
    db_token, raw_token = await crud.create_api_token(db, user.id, payload.description, idempotency_key)

    # Map to schema
    response = schemas.NewApiTokenResponse.model_validate(db_token)
    response.token = raw_token
    return response


@router.delete("/{token_id}")
@limiter.limit(settings.TOKENS_WRITE_LIMIT)
async def delete_token(
    token_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    """
    Revoke an API token.
    """
    success = await crud.delete_api_token(db, token_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"message": "Token revoked"}
