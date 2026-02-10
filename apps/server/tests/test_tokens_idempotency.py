import json
import base64
import pytest
from itsdangerous import TimestampSigner
from app.core.config import settings
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

# Helper to create auth headers (copied/adapted from test_features.py)
def create_auth_headers(user: User):
    session_data = {"user": {"sub": user.google_sub, "email": user.email}}
    json_data = json.dumps(session_data)
    signer = TimestampSigner(settings.SECRET_KEY)
    cookie = signer.sign(base64.b64encode(json_data.encode()).decode()).decode()
    return {"Cookie": f"session={cookie}"}

@pytest.fixture
async def regular_user_1(db_session: AsyncSession):
    result = await db_session.execute(select(User).filter(User.google_sub == "user1_sub"))
    existing_user = result.scalars().first()
    if existing_user:
        return existing_user

    user = User(
        google_sub="user1_sub",
        email="user1@example.com",
        name="User 1",
        roles=["user"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user

@pytest.mark.asyncio
async def test_create_token_idempotent(client, regular_user_1):
    headers = create_auth_headers(regular_user_1)
    # Add Idempotency-Key
    headers['Idempotency-Key'] = 'test-key-123'

    # First request
    r1 = client.post('/auth/tokens', json={'description': 'dup-test'}, headers=headers)
    assert r1.status_code == 200
    token1 = r1.json()

    # Second request with same key
    r2 = client.post('/auth/tokens', json={'description': 'dup-test-retry'}, headers=headers)
    assert r2.status_code == 200
    token2 = r2.json()

    # IDs should be same
    assert token1['id'] == token2['id']
    # Raw token returned first time
    assert token1['token'] is not None and len(token1['token']) > 0
    # Second time, raw token should be empty string (as per implementation)
    assert token2['token'] == ""

    # Third request with different key
    headers['Idempotency-Key'] = 'test-key-456'
    r3 = client.post('/auth/tokens', json={'description': 'new-token'}, headers=headers)
    assert r3.status_code == 200
    token3 = r3.json()
    assert token3['id'] != token1['id']
    assert token3['token'] is not None and len(token3['token']) > 0
