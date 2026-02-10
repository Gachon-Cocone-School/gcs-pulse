import os
import sys
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from app.database import get_db
from app.main import app
from app.models import Base

sys.path.append(os.getcwd())

# Use a file-based DB for persistence across connections in tests if needed,
# or in-memory shared cache. File is safer for debugging "no such table".
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_shared.db"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = sessionmaker(
    bind=test_engine, class_=AsyncSession, expire_on_commit=False
)

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    if os.path.exists("./test_shared.db"):
        os.remove("./test_shared.db")

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    if os.path.exists("./test_shared.db"):
        os.remove("./test_shared.db")

@pytest.fixture(scope="function")
async def db_session():
    async with TestSessionLocal() as session:
        yield session

@pytest.fixture(scope="function", autouse=True)
def override_dependencies(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)
