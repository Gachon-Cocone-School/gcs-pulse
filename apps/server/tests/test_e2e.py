import asyncio
import sys
import os
import json
import base64
from typing import Dict, Any
from itsdangerous import TimestampSigner
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

# Add project root to path
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.database import get_db
from app.core.config import settings
from app.models import User, Term

# --- Helper Functions ---
def create_session_cookie(data: Dict[str, Any]) -> str:
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()


@pytest.fixture(autouse=True)
async def seed_data(db_session: AsyncSession):
    # Seed Terms
    term1 = Term(
        type="privacy",
        version="1.0",
        content="Privacy Policy...",
        is_required=True,
        is_active=True,
    )
    db_session.add(term1)
    await db_session.commit()


# --- Test Cases ---

def test_public_routes(client):
    print("Testing public routes...")
    for path in ["/docs", "/openapi.json"]:
        response = client.get(path)
        assert (
            response.status_code == 200
        ), f"Expected 200 for {path}, got {response.status_code}"
    print("✅ Public routes OK.")


@patch("app.routers.auth.oauth.create_client")
def test_oauth_callback(mock_create_client, client):
    print("Testing OAuth callback...")

    # Mock the OAuth client
    mock_google = MagicMock()
    # Use AsyncMock for the awaited method
    mock_google.authorize_access_token = AsyncMock(
        return_value={
            "userinfo": {
                "sub": "gachon_user_sub",
                "email": "student@gachon.ac.kr",
                "name": "Gachon Student",
                "picture": "http://example.com/pic.jpg",
                "email_verified": True,
            }
        }
    )
    mock_create_client.return_value = mock_google

    # Call callback
    response = client.get("/auth/google/callback", follow_redirects=False)

    if response.status_code != 307:
        print(f"Callback failed: {response.status_code} - {response.text}")

    assert response.status_code == 307
    assert response.headers["location"] == settings.AUTH_SUCCESS_URL

    # Verify session cookie is set
    cookie = client.cookies.get("session")
    assert cookie is not None

    # Check /auth/me
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    print("✅ OAuth callback OK.")
