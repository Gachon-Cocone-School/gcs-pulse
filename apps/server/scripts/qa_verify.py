import asyncio
import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal

async def check_db():
    print("Checking database connectivity...")
    async with AsyncSessionLocal() as session:
        try:
            # Check for users table
            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            print("✅ 'users' table exists and is accessible.")

            # Check for teams table
            await session.execute(text("SELECT 1 FROM teams LIMIT 1"))
            print("✅ 'teams' table exists and is accessible.")

            # Check for daily_snippets table
            await session.execute(text("SELECT 1 FROM daily_snippets LIMIT 1"))
            print("✅ 'daily_snippets' table exists and is accessible.")

        except Exception as e:
            print(f"❌ Failed to access tables: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
