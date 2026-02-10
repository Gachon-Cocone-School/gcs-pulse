import asyncio
import os
import sys

# Add project root to path
# This allows importing from app.database, app.models, etc.
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, Base
# Import all models to ensure they are registered in Base.metadata
from app.models import Base, User, Term, Team, DailySnippet, WeeklySnippet, Consent, ApiToken
from app.core.config import settings

async def init_db():
    print(f"Initializing database...")
    print(f"DATABASE_URL: {settings.DATABASE_URL}")

    # Extract path from SQLite URL for debugging info
    if "sqlite" in settings.DATABASE_URL:
        db_path = settings.DATABASE_URL.split("///")[-1]
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
