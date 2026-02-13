import os
import sys
import pytest
import asyncio

# Add project root to path before other imports
sys.path.append(os.getcwd())

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient
from app.database import get_db
from app.main import app
from app.models import Base
import sqlalchemy as sa

# Read TEST_DATABASE_URL from environment so CI or developers can override.
# Fallback to a file-based sqlite for local development/testing parity with existing behavior.
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "sqlite+aiosqlite:///./test_shared.db"
)

IS_SQLITE = TEST_DATABASE_URL.startswith("sqlite")

# Create async engine depending on the database URL
# Use NullPool to avoid connection pooling issues in test environments/CI
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool, future=True)
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
    """Create (and later drop) all tables for the test database.

    Behavior:
    - If TEST_DATABASE_URL points to sqlite file, remove the file before/after to keep parity
      with previous behavior.
    - If a Postgres URL is used, run create_all/drop_all using the engine.
    """
    if IS_SQLITE:
        # Remove existing sqlite file for a clean start
        db_path = TEST_DATABASE_URL.replace("sqlite+aiosqlite://", "")
        if db_path.startswith("./"):
            db_file = db_path.replace("./", "")
        else:
            db_file = db_path
        if os.path.exists(db_file):
            os.remove(db_file)

    async with test_engine.begin() as conn:
        # create_all works for both sqlite and Postgres engines
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Teardown: drop all tables and remove sqlite file if used
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    if IS_SQLITE:
        db_path = TEST_DATABASE_URL.replace("sqlite+aiosqlite://", "")
        if db_path.startswith("./"):
            db_file = db_path.replace("./", "")
        else:
            db_file = db_path
        if os.path.exists(db_file):
            os.remove(db_file)


@pytest.fixture(scope="function")
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest.fixture(scope="function", autouse=True)
def override_dependencies(db_session):
    """Override the FastAPI dependency to use the test session."""

    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(scope="function")
def client():
    with TestClient(app, base_url="http://localhost") as c:
        yield c


@pytest.fixture(scope="function", autouse=True)
async def clean_tables(db_session: AsyncSession):
    """Clean tables before each test to ensure isolation.

    For Postgres we prefer TRUNCATE ... RESTART IDENTITY CASCADE for speed and to reset
    sequences. For sqlite we'll delete rows via SQLAlchemy table.delete().
    """
    if IS_SQLITE:
        for table in reversed(Base.metadata.sorted_tables):
            await db_session.execute(table.delete())
    else:
        # Postgres: use TRUNCATE for faster cleanup and cascade to child tables when needed
        table_names = ", ".join([f'"{t.name}"' for t in Base.metadata.sorted_tables])
        if table_names:
            await db_session.execute(sa.text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))
    await db_session.commit()
