import asyncio
import sys
import os
import json
import base64
from typing import Dict, Any
from itsdangerous import TimestampSigner
from starlette.datastructures import MutableHeaders
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import get_db
from app.core.config import settings
from app.models import Base, User, RoleAssignmentRule, RoutePermission, Term

# --- Setup Test Database ---
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db

client = TestClient(app, base_url="http://localhost")


# --- Helper Functions ---
def create_session_cookie(data: Dict[str, Any]) -> str:
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()


async def reset_db():
    async with test_engine.begin() as conn:
        # We don't want to drop everything if it's a real shared DB,
        # but for E2E we usually want a clean state.
        # Given the environment, we'll just truncate or delete rows.
        await conn.execute(text("DELETE FROM daily_snippets"))
        await conn.execute(text("DELETE FROM weekly_snippets"))
        await conn.execute(text("DELETE FROM consents"))
        await conn.execute(text("UPDATE users SET team_id = NULL"))
        await conn.execute(text("DELETE FROM teams"))
        await conn.execute(text("DELETE FROM role_assignment_rules"))
        await conn.execute(text("DELETE FROM route_permissions"))
        await conn.execute(text("DELETE FROM terms"))
        await conn.execute(text("DELETE FROM users"))
    print("Database reset complete.")


async def seed_data():
    async with TestSessionLocal() as session:
        # 1. Seed Role Rules
        # Rule: @gachon.ac.kr emails get '가천대학교' role
        rule1 = RoleAssignmentRule(
            rule_type="email_pattern",
            rule_value={"pattern": "%@gachon.ac.kr"},
            assigned_role="가천대학교",
            priority=10,
        )
        # Rule: Specific email gets 'admin' role
        rule2 = RoleAssignmentRule(
            rule_type="email_list",
            rule_value={"emails": ["admin@example.com"]},
            assigned_role="admin",
            priority=1,
        )
        session.add_all([rule1, rule2])

        # 2. Seed Route Permissions
        # Public routes
        perms = [
            RoutePermission(path="/auth/google/login", method="GET", is_public=True),
            RoutePermission(path="/auth/google/callback", method="GET", is_public=True),
            RoutePermission(path="/docs", method="GET", is_public=True),
            RoutePermission(path="/openapi.json", method="GET", is_public=True),
            # Protected routes
            RoutePermission(
                path="/auth/me",
                method="GET",
                is_public=False,
                roles=["user", "admin", "가천대학교"],
            ),
            RoutePermission(
                path="/admin/permissions",
                method="GET",
                is_public=False,
                roles=["admin"],
            ),
            RoutePermission(
                path="/admin/role-rules", method="GET", is_public=False, roles=["admin"]
            ),
        ]
        session.add_all(perms)

        # 3. Seed Terms
        term1 = Term(
            type="privacy",
            version="1.0",
            content="Privacy Policy...",
            is_required=True,
            is_active=True,
        )
        session.add(term1)

        await session.commit()
    print("Seed data complete.")


# --- Test Cases ---


def test_public_routes():
    print("Testing public routes...")
    for path in ["/docs", "/openapi.json"]:
        response = client.get(path)
        assert (
            response.status_code == 200
        ), f"Expected 200 for {path}, got {response.status_code}"
    print("✅ Public routes OK.")


@patch("app.routers.auth.oauth.create_client")
def test_oauth_callback_and_role_assignment(mock_create_client):
    print("Testing OAuth callback and role assignment...")

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
    assert response.status_code == 307
    assert response.headers["location"] == settings.AUTH_SUCCESS_URL

    # Verify session cookie is set
    cookie = client.cookies.get("session")
    assert cookie is not None

    # Check /auth/me to see roles
    response = client.get("/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["authenticated"] is True
    assert "가천대학교" in data["user"]["roles"]
    assert "user" in data["user"]["roles"]
    print("✅ OAuth and Auto-role assignment OK.")


def test_rbac_enforcement():
    print("Testing RBAC enforcement...")

    # 1. Normal user (Gachon Student) attempts admin route
    session_data = {"user": {"sub": "gachon_user_sub", "email": "student@gachon.ac.kr"}}
    client.cookies.set("session", create_session_cookie(session_data))

    response = client.get("/admin/permissions")
    assert response.status_code == 403, "Gachon student should not access admin route"
    assert response.json()["detail"] == "Access denied: Insufficient permissions"

    # 2. Mock Admin user
    client.cookies.clear()
    with patch("app.routers.auth.oauth.create_client") as mock_create_client:
        mock_google = MagicMock()
        mock_google.authorize_access_token = AsyncMock(
            return_value={
                "userinfo": {
                    "sub": "admin_user_sub",
                    "email": "admin@example.com",
                    "name": "Admin User",
                    "picture": "http://example.com/admin.jpg",
                    "email_verified": True,
                }
            }
        )
        mock_create_client.return_value = mock_google
        response = client.get("/auth/google/callback", follow_redirects=False)
        assert response.status_code == 307

    # Verify admin has 'admin' role
    response = client.get("/auth/me")
    data = response.json()
    assert (
        "admin" in data["user"]["roles"]
    ), f"Admin should have 'admin' role, got {data['user']['roles']}"

    response = client.get("/admin/permissions")
    assert response.status_code == 200, "Admin should access admin route"
    print("✅ RBAC enforcement OK.")


def test_default_disallow():
    print("Testing default disallow policy...")
    # Route that exists in code (/auth/logout) but NOT in route_permissions table in our seed
    response = client.get("/auth/logout")
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied: No permission rule found"
    print("✅ Default disallow OK.")


# --- Main Runner ---
async def main():
    try:
        await reset_db()
        await seed_data()

        test_public_routes()
        test_oauth_callback_and_role_assignment()
        test_rbac_enforcement()
        test_default_disallow()

        print("\n🎉 ALL E2E TESTS PASSED!")
    except Exception as e:
        print(f"\n❌ E2E TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        await test_engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
