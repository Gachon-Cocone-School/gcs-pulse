import asyncio
import base64
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient
from itsdangerous import TimestampSigner
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models import RoutePermission, Team, User
from app.dependencies_copilot import get_copilot_client

# --- Setup Test Database ---
test_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
TestSessionLocal = sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def override_get_copilot_client(request):
    mock = AsyncMock()
    async def side_effect(messages, **kwargs):
        user_content = messages[-1]["content"]
        return {"choices": [{"message": {"content": f"Organized: {user_content}"}}]}
    mock.chat.side_effect = side_effect
    return mock

app.dependency_overrides[get_db] = override_get_db
app.dependency_overrides[get_copilot_client] = override_get_copilot_client

client = TestClient(app, base_url="http://localhost")


def create_session_cookie(data: Dict[str, Any]) -> str:
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()


@pytest.fixture(scope="module", autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.execute(text("DELETE FROM daily_snippets"))
        await conn.execute(text("DELETE FROM weekly_snippets"))
        await conn.execute(text("DELETE FROM consents"))
        await conn.execute(text("UPDATE users SET team_id = NULL"))
        await conn.execute(text("DELETE FROM teams"))
        await conn.execute(text("DELETE FROM route_permissions"))
        await conn.execute(text("DELETE FROM users"))

    async with TestSessionLocal() as session:
        perms = [
            RoutePermission(path="/admin/teams", method="GET", is_public=False, roles=["admin"]),
            RoutePermission(path="/admin/teams", method="POST", is_public=False, roles=["admin"]),
            RoutePermission(path="/admin/teams/{team_id}", method="GET", is_public=False, roles=["admin"]),
            RoutePermission(path="/admin/teams/{team_id}", method="PUT", is_public=False, roles=["admin"]),
            RoutePermission(path="/admin/teams/{team_id}", method="DELETE", is_public=False, roles=["admin"]),
            RoutePermission(
                path="/admin/teams/{team_id}/members/{user_id}",
                method="POST",
                is_public=False,
                roles=["admin"],
            ),
            RoutePermission(
                path="/admin/teams/{team_id}/members/{user_id}",
                method="DELETE",
                is_public=False,
                roles=["admin"],
            ),
            RoutePermission(
                path="/daily-snippets", method="GET", is_public=False, roles=["user", "admin"]
            ),
            RoutePermission(
                path="/daily-snippets", method="POST", is_public=False, roles=["user", "admin"]
            ),
            RoutePermission(
                path="/daily-snippets/{snippet_id}",
                method="GET",
                is_public=False,
                roles=["user", "admin"],
            ),
            RoutePermission(
                path="/daily-snippets/{snippet_id}",
                method="DELETE",
                is_public=False,
                roles=["user", "admin"],
            ),
            RoutePermission(
                path="/weekly-snippets", method="GET", is_public=False, roles=["user", "admin"]
            ),
            RoutePermission(
                path="/weekly-snippets", method="POST", is_public=False, roles=["user", "admin"]
            ),
            RoutePermission(
                path="/weekly-snippets/{snippet_id}",
                method="GET",
                is_public=False,
                roles=["user", "admin"],
            ),
            RoutePermission(
                path="/weekly-snippets/{snippet_id}",
                method="DELETE",
                is_public=False,
                roles=["user", "admin"],
            ),
        ]
        session.add_all(perms)
        await session.commit()
    yield


@pytest.fixture
async def admin_user():
    from sqlalchemy.future import select

    async with TestSessionLocal() as session:
        result = await session.execute(select(User).filter(User.google_sub == "admin_sub"))
        existing_user = result.scalars().first()
        if existing_user:
            return existing_user

        user = User(
            google_sub="admin_sub",
            email="admin@example.com",
            name="Admin",
            roles=["admin", "user"],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def regular_user_1():
    async with TestSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE google_sub = 'user1_sub'")
        )
        if result.first():
            # fetch user object
            from sqlalchemy.future import select
            res = await session.execute(select(User).filter(User.google_sub == "user1_sub"))
            return res.scalars().first()

        user = User(
            google_sub="user1_sub",
            email="user1@example.com",
            name="User 1",
            roles=["user"],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest.fixture
async def regular_user_2():
    async with TestSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM users WHERE google_sub = 'user2_sub'")
        )
        if result.first():
            from sqlalchemy.future import select
            res = await session.execute(select(User).filter(User.google_sub == "user2_sub"))
            return res.scalars().first()

        user = User(
            google_sub="user2_sub",
            email="user2@example.com",
            name="User 2",
            roles=["user"],
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


def auth_headers(user: User):
    session_data = {"user": {"sub": user.google_sub, "email": user.email}}
    cookie = create_session_cookie(session_data)
    return {"Cookie": f"session={cookie}"}


@pytest.mark.asyncio
async def test_teams_crud(admin_user, regular_user_1, regular_user_2):
    resp = client.post(
        "/admin/teams", json={"name": "Team Alpha"}, headers=auth_headers(admin_user)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    team_data = resp.json()
    team_id = team_data["id"]
    assert team_data["name"] == "Team Alpha"

    resp = client.post(
        "/admin/teams", json={"name": "Team Beta"}, headers=auth_headers(regular_user_1)
    )
    assert resp.status_code == 403

    resp = client.post(
        f"/admin/teams/{team_id}/members/{regular_user_1.id}", headers=auth_headers(admin_user)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"

    resp = client.post(
        f"/admin/teams/{team_id}/members/{regular_user_2.id}", headers=auth_headers(regular_user_1)
    )
    assert resp.status_code == 403

    resp = client.delete(
        f"/admin/teams/{team_id}/members/{regular_user_1.id}", headers=auth_headers(admin_user)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"


@pytest.mark.asyncio
async def test_daily_snippets_flow(admin_user, regular_user_1, regular_user_2):
    resp = client.post(
        "/admin/teams", json={"name": "Dev Team"}, headers=auth_headers(admin_user)
    )
    team_id = resp.json()["id"]
    client.post(
        f"/admin/teams/{team_id}/members/{regular_user_1.id}", headers=auth_headers(admin_user)
    )
    client.post(
        f"/admin/teams/{team_id}/members/{regular_user_2.id}", headers=auth_headers(admin_user)
    )

    content = "User 1 daily update"
    resp = client.post(
        "/daily-snippets", json={"content": content}, headers=auth_headers(regular_user_1)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    snippet_id = resp.json()["id"]
    assert resp.json()["content"] == content
    assert resp.json()["date"] == datetime.now().date().isoformat()

    resp = client.post(
        "/daily-snippets", json={"content": "Duplicate"}, headers=auth_headers(regular_user_1)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"

    resp = client.get(f"/daily-snippets/{snippet_id}", headers=auth_headers(regular_user_2))
    assert resp.status_code == 200
    assert resp.json()["content"] == "Duplicate"

    resp = client.get("/daily-snippets", headers=auth_headers(regular_user_2))
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert len(items) >= 1
    assert any(i["id"] == snippet_id for i in items)

    resp = client.get(f"/daily-snippets/{snippet_id}", headers=auth_headers(admin_user))
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_weekly_snippets_flow(regular_user_1):
    content = "Weekly Report"
    resp = client.post(
        "/weekly-snippets", json={"content": content}, headers=auth_headers(regular_user_1)
    )
    assert resp.status_code == 200, f"Error: {resp.text}"
    snippet_id = resp.json()["id"]

    resp = client.get("/weekly-snippets", headers=auth_headers(regular_user_1))
    assert resp.status_code == 200
    assert resp.json()["total"] == 1
    assert resp.json()["items"][0]["content"] == content

    resp = client.delete(f"/weekly-snippets/{snippet_id}", headers=auth_headers(regular_user_1))
    assert resp.status_code == 200

    resp = client.get(f"/weekly-snippets/{snippet_id}", headers=auth_headers(regular_user_1))
    assert resp.status_code == 404
