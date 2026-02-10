# QA & Fix Plan: SQLite Migration

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the "no such table: users" error by ensuring the SQLite database is properly initialized in the actual runtime environment, then perform a comprehensive QA pass.

**Architecture:**
- **Issue:** The DB was initialized for tests but likely not for the running `dev` server, or `uvicorn` is looking at a different path/file than the init script created.
- **Fix:** Create a robust `init_db.py` script that ensures tables exist, and run it explicitly before starting the server. Verify `DATABASE_URL` consistency.
- **QA:** Run through key user flows manually (via script/curl) to verify functionality.

**Tech Stack:** FastAPI, SQLite, Python

---

### Task 1: Verify & Fix Database Initialization

**Files:**
- Modify: `apps/server/scripts/init_db.py`
- Modify: `apps/server/.env` (Verify)

**Step 1: Check Environment Config**

Read `apps/server/.env` and `apps/server/app/core/config.py` to confirm `DATABASE_URL`.
Ensure `DATABASE_URL` uses an absolute path or strictly relative path that works from root.
Recommendation: `sqlite+aiosqlite:////absolute/path/to/project/apps/server/gcs_lms.db` to avoid ambiguity, or `./gcs_lms.db` if CWD is consistent.

**Step 2: Update Init Script**

Update `apps/server/scripts/init_db.py` to import ALL models and creating tables.
Make it robust (print DB path).

```python
import asyncio
import os
import sys

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import engine, Base
# Import all models to ensure they are registered
from app.models import Base, User, Term, Team, DailySnippet, WeeklySnippet, Consent
from app.core.config import settings

async def init_db():
    print(f"Initializing database at: {settings.DATABASE_URL}")
    async with engine.begin() as conn:
        # await conn.run_sync(Base.metadata.drop_all) # Optional: Don't drop if we want to preserve
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created:")
        for table in Base.metadata.tables:
            print(f" - {table}")
    print("Database initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_db())
```

**Step 3: Run Init Script**

Run:
```bash
cd apps/server && source venv/bin/activate && python scripts/init_db.py
```

**Step 4: Commit**

```bash
git add apps/server/scripts/init_db.py
git commit -m "fix(server): robust database initialization script"
```

---

### Task 2: Create QA Verification Script

**Files:**
- Create: `apps/server/scripts/qa_verify.py`

**Step 1: Create QA Script**

Create a script that uses `httpx` or `requests` to hit the *running server* (localhost:8000) and verify flows. This mimics the frontend.

Flows to test:
1.  **Public Routes**: `/docs`, `/openapi.json` (GET 200)
2.  **Auth (Mock)**: Since we can't easily do OAuth, we might need to rely on Unit Tests for Auth, OR temporarily enable a "Dev Login" endpoint if environment is dev.
    *   *Alternative*: Just verify DB tables exist using python script directly.
    *   *Better*: Verify the server is UP and DB is accessible.

Let's stick to a script that checks DB directly for the error "no such table".

```python
import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.database import AsyncSessionLocal
from sqlalchemy import text

async def check_db():
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("SELECT 1 FROM users LIMIT 1"))
            print("✅ 'users' table exists and is accessible.")
        except Exception as e:
            print(f"❌ Failed to access 'users' table: {e}")
            sys.exit(1)

if __name__ == "__main__":
    asyncio.run(check_db())
```

**Step 2: Run Verification**

Run:
```bash
cd apps/server && source venv/bin/activate && python scripts/qa_verify.py
```

**Step 3: Commit**

```bash
git add apps/server/scripts/qa_verify.py
git commit -m "chore(server): add QA verification script"
```

---

### Task 3: Restart Server & Manual QA (Report)

**Files:**
- Action only.

**Step 1: Restart Server**

Kill existing server process (port 8000).
Start server again: `cd apps/server && source venv/bin/activate && uvicorn app.main:app --reload`

**Step 2: Generate QA Report**

Create a markdown file `QA_REPORT.md` with:
- Check 1: Database Initialization (Pass/Fail)
- Check 2: Server Startup (Pass/Fail)
- Check 3: Login Page Load (Frontend)
- Check 4: Login Flow (Frontend - Google Auth)

**Step 3: Commit**

```bash
git add QA_REPORT.md
git commit -m "docs: add QA report"
```
