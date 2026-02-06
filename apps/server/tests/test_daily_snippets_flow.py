import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.config import settings
from itsdangerous import TimestampSigner
import base64
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.dependencies_copilot import get_copilot_client
from app.models import User, DailySnippet
from app.dependencies import check_route_permissions
from datetime import date, datetime

def create_session_cookie(data: dict) -> str:
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()

@pytest.mark.asyncio
async def test_create_daily_snippet_success():
    app.dependency_overrides[check_route_permissions] = lambda: True

    with patch("app.routers.daily_snippets.crud") as mock_crud, \
         patch("app.routers.snippet_utils.crud", mock_crud):
        mock_user = User(id=1, google_sub="test_sub", email="test@example.com", roles=["user"])
        mock_crud.get_user_by_sub = AsyncMock(return_value=mock_user)
        
        mock_snippet = DailySnippet(
            id=100, 
            user_id=1, 
            date=date.today(),
            content="Raw content",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_crud.upsert_daily_snippet = AsyncMock(return_value=mock_snippet)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
            session_data = {"user": {"sub": "test_sub", "email": "test@example.com"}}
            ac.cookies.set("session", create_session_cookie(session_data))
            
            response = await ac.post("/daily-snippets", json={"content": "Raw content"})
            
            if response.status_code != 200:
                print(response.json())

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "Raw content"
            assert data["user_id"] == 1
            
            mock_crud.upsert_daily_snippet.assert_called_once()


@pytest.mark.asyncio
async def test_update_daily_snippet_success():
    app.dependency_overrides[check_route_permissions] = lambda: True
    
    with patch("app.routers.daily_snippets.crud") as mock_crud, \
         patch("app.routers.snippet_utils.crud", mock_crud):
        mock_user = User(id=1, google_sub="test_sub", email="test@example.com", roles=["user"])
        mock_crud.get_user_by_sub = AsyncMock(return_value=mock_user)
        mock_crud.get_user_by_id = AsyncMock(return_value=mock_user)
        
        mock_snippet = DailySnippet(
            id=100, 
            user_id=1, 
            date=date.today(),
            content="Old Content",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_crud.get_daily_snippet_by_id = AsyncMock(return_value=mock_snippet)
        
        mock_updated = DailySnippet(
            id=100,
            user_id=1,
            date=date.today(),
            content="New Content",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        mock_crud.update_daily_snippet = AsyncMock(return_value=mock_updated)

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://localhost") as ac:
            session_data = {"user": {"sub": "test_sub", "email": "test@example.com"}}
            ac.cookies.set("session", create_session_cookie(session_data))
            
            response = await ac.put("/daily-snippets/100", json={"content": "New Content"})
            
            if response.status_code != 200:
                print(response.json())

            assert response.status_code == 200
            data = response.json()
            assert data["content"] == "New Content"
            
            mock_crud.update_daily_snippet.assert_called_once()
