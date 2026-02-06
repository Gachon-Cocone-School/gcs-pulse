import asyncio
import sys
import os
import json
import base64
from itsdangerous import TimestampSigner
from starlette.datastructures import MutableHeaders

# Add project root to path
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.future import select
from app.main import app
from app.database import get_db
from app.models import User
from app.core.config import settings

from sqlalchemy.pool import NullPool
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Setup Test Engine & Session
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

# Setup Test Client
client = TestClient(app, base_url="http://localhost")

def create_session_cookie(data):
    signer = TimestampSigner(settings.SECRET_KEY)
    json_data = json.dumps(data)
    return signer.sign(base64.b64encode(json_data.encode()).decode()).decode()

async def setup_test_users():
    local_engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool)
    async with local_engine.begin() as conn:
        # Delete existing test users first
        await conn.execute(text("DELETE FROM users WHERE google_sub IN ('admin_sub', 'user_sub')"))
        
        # Create Admin User
        await conn.execute(text("""
            INSERT INTO users (google_sub, email, name, roles)
            VALUES ('admin_sub', 'admin@example.com', 'Admin User', '["admin"]')
        """))
        
        # Create Normal User
        await conn.execute(text("""
            INSERT INTO users (google_sub, email, name, roles)
            VALUES ('user_sub', 'user@example.com', 'Normal User', '["user"]')
        """))
    
    await local_engine.dispose()

def run_tests():
    print("Running RBAC Verification Tests...")
    
    # 1. Public Route
    print("\nTest 1: Public Route (/docs)")
    response = client.get("/docs")
    if response.status_code == 200:
        print("PASS: /docs is accessible (200)")
    else:
        print(f"FAIL: /docs returned {response.status_code}")
        print(response.text)

    # 2. Admin Route - No Auth
    print("\nTest 2: Admin Route - No Auth")
    response = client.get("/admin/permissions")
    if response.status_code == 401:
        print("PASS: /admin/permissions returned 401 for unauthenticated user")
    else:
        print(f"FAIL: /admin/permissions returned {response.status_code}")
        print(response.text)

    # 3. Admin Route - Normal User
    print("\nTest 3: Admin Route - Normal User")
    # Clear cookies first
    client.cookies.clear()
    # Manually set session cookie
    session_data = {"user": {"sub": "user_sub", "email": "user@example.com"}}
    cookie_value = create_session_cookie(session_data)
    client.cookies.set("session", cookie_value)
    
    response = client.get("/admin/permissions")
    if response.status_code == 403:
        print("PASS: /admin/permissions returned 403 for normal user")
    else:
        print(f"FAIL: /admin/permissions returned {response.status_code}")
        print(response.json())

    # 4. Admin Route - Admin User
    print("\nTest 4: Admin Route - Admin User")
    # Clear cookies first
    client.cookies.clear()
    # Manually set session cookie
    session_data = {"user": {"sub": "admin_sub", "email": "admin@example.com"}}
    cookie_value = create_session_cookie(session_data)
    client.cookies.set("session", cookie_value)
    
    response = client.get("/admin/permissions")
    if response.status_code == 200:
        print("PASS: /admin/permissions returned 200 for admin user")
    else:
        print(f"FAIL: /admin/permissions returned {response.status_code}")
        print(response.json())

    # 5. Unknown Route (Default Disallow)
    print("\nTest 5: Unknown Route")
    response = client.get("/some/random/route")
    if response.status_code == 403:
        print("PASS: Unknown route returned 403")
    else:
        print(f"FAIL: Unknown route returned {response.status_code}")

if __name__ == "__main__":
    # Run async setup
    asyncio.run(setup_test_users())
    # Run sync tests (TestClient is sync)
    run_tests()
