import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import text
from app.database import engine, Base
from app.models import RoutePermission
from app.main import app
from sqlalchemy.future import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession

AsyncSessionLocal = sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)


async def migrate_and_seed():
    async with engine.begin() as conn:
        print("Ensuring tables and columns exist...")
        try:
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS roles JSON DEFAULT '[\"user\"]'"
                )
            )
        except Exception as e:
            print(f"  - Skipping users.roles migration: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS teams ("
                    "id SERIAL PRIMARY KEY, "
                    "name VARCHAR(255) NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP"
                    ")"
                )
            )
        except Exception as e:
            print(f"  - Skipping teams table creation: {e}")

        try:
            await conn.execute(
                text(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS team_id INTEGER REFERENCES teams(id)"
                )
            )
        except Exception as e:
            print(f"  - Skipping users.team_id migration: {e}")

        try:
            await conn.execute(
                text("ALTER TABLE daily_snippets ADD COLUMN IF NOT EXISTS playbook TEXT")
            )
            await conn.execute(
                text("ALTER TABLE daily_snippets ADD COLUMN IF NOT EXISTS feedback TEXT")
            )
        except Exception as e:
            print(f"  - Skipping daily_snippets columns migration: {e}")

        try:
            await conn.execute(
                text(
                    "ALTER TABLE weekly_snippets ADD COLUMN IF NOT EXISTS structured TEXT"
                )
            )
            await conn.execute(
                text("ALTER TABLE weekly_snippets ADD COLUMN IF NOT EXISTS playbook TEXT")
            )
            await conn.execute(
                text("ALTER TABLE weekly_snippets ADD COLUMN IF NOT EXISTS feedback TEXT")
            )
        except Exception as e:
            print(f"  - Skipping weekly_snippets columns migration: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS daily_snippets ("
                    "id SERIAL PRIMARY KEY, "
                    "user_id INTEGER NOT NULL REFERENCES users(id), "
                    "date DATE NOT NULL, "
                    "content TEXT NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "CONSTRAINT _user_date_uc UNIQUE (user_id, date)"
                    ")"
                )
            )
        except Exception as e:
            print(f"  - Skipping daily_snippets table creation: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE TABLE IF NOT EXISTS weekly_snippets ("
                    "id SERIAL PRIMARY KEY, "
                    "user_id INTEGER NOT NULL REFERENCES users(id), "
                    "week DATE NOT NULL, "
                    "content TEXT NOT NULL, "
                    "created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP, "
                    "CONSTRAINT _user_week_uc UNIQUE (user_id, week)"
                    ")"
                )
            )
        except Exception as e:
            print(f"  - Skipping weekly_snippets table creation: {e}")

        try:
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_daily_snippets_user_id ON daily_snippets(user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_daily_snippets_date ON daily_snippets(date)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_weekly_snippets_user_id ON weekly_snippets(user_id)"
                )
            )
            await conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_weekly_snippets_week ON weekly_snippets(week)"
                )
            )
        except Exception as e:
            print(f"  - Skipping snippet index creation: {e}")

        # 2. Create tables
        await conn.run_sync(Base.metadata.create_all)
        print("  - Tables created/verified.")

    async with AsyncSessionLocal() as session:
        # 3. Sync Routes from FastAPI App
        print("Syncing routes from FastAPI app to route_permissions table...")

        # Define security rules
        # (path_pattern, method) -> (is_public, [roles])
        special_rules = {
            ("/auth/google/login", "GET"): (True, []),
            ("/auth/google/callback", "GET"): (True, []),
            ("/auth/logout", "GET"): (False, ["user", "admin"]),
            ("/auth/me", "GET"): (False, ["user", "admin", "가천대학교"]),
            ("/docs", "GET"): (True, []),
            ("/openapi.json", "GET"): (True, []),
            ("/redoc", "GET"): (True, []),
            ("/docs/oauth2-redirect", "GET"): (True, []),
            ("/terms", "GET"): (True, []),
            ("/consents", "POST"): (False, ["user", "admin"]),
            ("/protected", "GET"): (False, ["user", "admin"]),
            ("/daily-snippets", "GET"): (False, ["user", "admin"]),
            ("/daily-snippets", "POST"): (False, ["user", "admin"]),
            ("/daily-snippets/{snippet_id}", "GET"): (False, ["user", "admin"]),
            ("/daily-snippets/{snippet_id}", "PUT"): (False, ["user", "admin"]),
            ("/daily-snippets/{snippet_id}", "DELETE"): (False, ["user", "admin"]),
            ("/daily-snippets/organize", "POST"): (False, ["user", "admin"]),
            ("/weekly-snippets", "GET"): (False, ["user", "admin"]),
            ("/weekly-snippets", "POST"): (False, ["user", "admin"]),
            ("/weekly-snippets/{snippet_id}", "GET"): (False, ["user", "admin"]),
            ("/weekly-snippets/{snippet_id}", "PUT"): (False, ["user", "admin"]),
            ("/weekly-snippets/{snippet_id}", "DELETE"): (False, ["user", "admin"]),
            ("/weekly-snippets/organize", "POST"): (False, ["user", "admin"]),
            ("/snippet_date", "GET"): (False, ["user", "admin"]),
        }

        for route in app.routes:
            if not (hasattr(route, "path") and hasattr(route, "methods")):
                continue

            path = route.path
            for method in route.methods:
                # Default security: Private, Admin-only
                is_public = False
                allowed_roles = ["admin"]

                # Apply rules
                if (path, method) in special_rules:
                    is_public, allowed_roles = special_rules[(path, method)]
                elif path.startswith("/admin"):
                    is_public = False
                    allowed_roles = ["admin"]
                elif method == "HEAD":
                    # Copy from GET if available
                    if (path, "GET") in special_rules:
                        is_public, allowed_roles = special_rules[(path, "GET")]
                    else:
                        is_public = False
                        allowed_roles = ["admin"]
                elif path in ["/auth/logout", "/consents", "/protected"]:
                    # General protected routes for everyone authenticated
                    is_public = False
                    allowed_roles = ["user", "admin"]

                # Check if exists
                result = await session.execute(
                    select(RoutePermission).filter(
                        RoutePermission.path == path, RoutePermission.method == method
                    )
                )
                db_perm = result.scalars().first()

                if not db_perm:
                    print(f"  + Adding {method} {path}")
                    db_perm = RoutePermission(
                        path=path,
                        method=method,
                        is_public=is_public,
                        roles=allowed_roles,
                    )
                    session.add(db_perm)
                else:
                    # Update existing for consistency
                    db_perm.is_public = is_public
                    db_perm.roles = allowed_roles

        await session.commit()
        print("Sync and Seeding Complete.")


if __name__ == "__main__":
    asyncio.run(migrate_and_seed())
