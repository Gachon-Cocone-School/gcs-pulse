import asyncio
import os
import sys

# Add project root to path
# This allows importing from app.database, app.models, etc.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, Base
# Import all models to ensure they are registered in Base.metadata
from app.models import Base, User, Term, Team, DailySnippet, WeeklySnippet, Consent, ApiToken, Comment
from app.core.config import settings

async def init_db():
    print(f"Initializing database...")
    if settings.ENVIRONMENT == "production":
        active_db_url = settings.DATABASE_URL
    elif settings.ENVIRONMENT == "test" and settings.TEST_DATABASE_URL:
        active_db_url = settings.TEST_DATABASE_URL
    else:
        active_db_url = settings.DEV_DATABASE_URL

    print(f"DATABASE_URL: {active_db_url}")

    # Extract path from SQLite URL for debugging info
    if "sqlite" in active_db_url:
        db_path = active_db_url.split("///")[-1]
        abs_path = os.path.abspath(db_path)
        print(f"Resolved SQLite file path: {abs_path}")

    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Optional: Don't drop if we want to preserve
        await conn.run_sync(Base.metadata.create_all)

        print("\nTables created:")
        def inspect_tables(connection):
            from sqlalchemy import inspect
            inspector = inspect(connection)
            return inspector.get_table_names()

        tables = await conn.run_sync(inspect_tables)
        for table in tables:
            print(f" - {table}")

    print("\nDatabase initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
