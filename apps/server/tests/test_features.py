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
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.append(os.getcwd())

from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models import Team, User
from app.dependencies_copilot import get_copilot_client

# --- Setup Mock Copilot ---
async def override_get_copilot_client(request):
    mock = AsyncMock()
    async def side_effect(messages, **kwargs):
        user_content = messages[-1]["content"]
        return {"choices": [{"message": {"content": f"Organized: {user_content}"}}]}
    mock.chat.side_effect = side_effect
    return mock

app.dependency_overrides[get_copilot_client] = override_get_copilot_client


def create_session_cookie(data: Dict[str, Any]) -> str:
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    from sqlalchemy.future import select

    result = await db_session.execute(select(User).filter(User.google_sub == "admin_sub"))
    existing_user = result.scalars().first()
    if existing_user:
        return existing_user

    user = User(
        google_sub="admin_sub",
        email="admin@example.com",
        name="Admin",
        roles=["admin", "user"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def regular_user_1(db_session: AsyncSession):
    from sqlalchemy.future import select
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


@pytest.fixture
async def regular_user_2(db_session: AsyncSession):
    from sqlalchemy.future import select
    result = await db_session.execute(select(User).filter(User.google_sub == "user2_sub"))
    existing_user = result.scalars().first()
    if existing_user:
        return existing_user

    user = User(
        google_sub="user2_sub",
        email="user2@example.com",
        name="User 2",
        roles=["user"],
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


def auth_headers(user: User):
    session_data = {"user": {"sub": user.google_sub, "email": user.email}}
    cookie = create_session_cookie(session_data)
    return {"Cookie": f"session={cookie}"}


@pytest.mark.asyncio
async def test_daily_snippets_flow(client, admin_user, regular_user_1, regular_user_2):
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

    # Verify user 2 cannot see user 1's snippet (if not in same team)
    resp = client.get(f"/daily-snippets/{snippet_id}", headers=auth_headers(regular_user_2))
    assert resp.status_code == 403 or resp.status_code == 404

    resp = client.get("/daily-snippets", headers=auth_headers(regular_user_2))
    assert resp.status_code == 200
    items = resp.json()["items"]
    # Should not see user 1's snippet
    assert not any(i["id"] == snippet_id for i in items)


@pytest.mark.asyncio
async def test_weekly_list_uses_shared_viewer_helper(client, regular_user_1, monkeypatch):
    from app.routers import snippet_utils as shared_snippet_utils

    call_count = 0

    async def fake_get_viewer_or_401(request, db):
        nonlocal call_count
        call_count += 1
        return regular_user_1

    monkeypatch.setattr(shared_snippet_utils, "get_viewer_or_401", fake_get_viewer_or_401)

    resp = client.get("/weekly-snippets", headers=auth_headers(regular_user_1))
    assert resp.status_code == 200
    assert call_count == 1


@pytest.mark.asyncio
async def test_weekly_endpoints_use_shared_viewer_helper(client, regular_user_1, monkeypatch):
    from app.routers import snippet_utils as shared_snippet_utils

    call_count = 0

    async def fake_get_viewer_or_401(request, db):
        nonlocal call_count
        call_count += 1
        return regular_user_1

    async def fake_organize_content_with_ai(content, copilot):
        return f"Organized: {content}"

    async def fake_generate_feedback_with_ai(daily_snippet_content, organized_content, playbook_content, copilot):
        return '{"playbook_update_markdown":"updated"}'

    monkeypatch.setattr(shared_snippet_utils, "get_viewer_or_401", fake_get_viewer_or_401)
    monkeypatch.setattr(shared_snippet_utils, "organize_content_with_ai", fake_organize_content_with_ai)
    monkeypatch.setattr(shared_snippet_utils, "generate_feedback_with_ai", fake_generate_feedback_with_ai)

    create_resp = client.post(
        "/weekly-snippets", json={"content": "Weekly helper coverage"}, headers=auth_headers(regular_user_1)
    )
    assert create_resp.status_code == 200
    snippet_id = create_resp.json()["id"]

    get_resp = client.get(f"/weekly-snippets/{snippet_id}", headers=auth_headers(regular_user_1))
    assert get_resp.status_code == 200

    organize_resp = client.post(
        "/weekly-snippets/organize",
        params={"request": "stub"},
        headers=auth_headers(regular_user_1),
    )
    assert organize_resp.status_code == 200

    update_resp = client.put(
        f"/weekly-snippets/{snippet_id}",
        json={"content": "Weekly helper coverage updated"},
        headers=auth_headers(regular_user_1),
    )
    assert update_resp.status_code == 200

    delete_resp = client.delete(f"/weekly-snippets/{snippet_id}", headers=auth_headers(regular_user_1))
    assert delete_resp.status_code == 200

    assert call_count == 5


@pytest.mark.asyncio
async def test_weekly_snippets_flow(client, regular_user_1):
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
