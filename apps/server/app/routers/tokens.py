from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.ext.asyncio import AsyncSession
import time
import logging

from app import crud, schemas
from app.database import get_db
from app.dependencies import get_active_user
from app.models import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/tokens", tags=["tokens"])


@router.get("", response_model=List[schemas.ApiTokenResponse])
async def list_tokens(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
):
    """
    List all API tokens for the current user.
    """
    return await crud.list_api_tokens(db, user.id)


@router.post("", response_model=schemas.NewApiTokenResponse)
async def create_token(
    payload: schemas.ApiTokenCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
    idempotency_key: Optional[str] = Header(None, alias='Idempotency-Key'),
):
    """
    Create a new API token. The raw token is returned only once.
    This endpoint logs start/commit/return timings for investigation.
    """
    start = time.time()
    logger.debug(f"create_token: start user_id={user.id} desc={payload.description} idempotency_key={idempotency_key}")

    db_token, raw_token = await crud.create_api_token(db, user.id, payload.description, idempotency_key)

    logger.debug(f"create_token: committed user_id={user.id} token_id={getattr(db_token, 'id', None)} elapsed={time.time()-start}")

    # Map to schema
    response = schemas.NewApiTokenResponse.model_validate(db_token)
    response.token = raw_token

    logger.debug(f"create_token: returning response user_id={user.id} token_id={getattr(db_token, 'id', None)} elapsed={time.time()-start}")
    return response


@router.delete("/{token_id}")
async def delete_token(
    token_id: int,
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
