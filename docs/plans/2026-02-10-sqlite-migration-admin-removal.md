# SQLite Migration & Admin Removal Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Migrate backend from PostgreSQL to SQLite, and remove all Admin/RBAC features from both client and server to simplify the architecture for agentic testing.

**Architecture:**
- **Backend**: Switch `asyncpg` to `aiosqlite`. Replace dynamic RBAC with simple authentication. Remove `admin` router and related models.
- **Frontend**: Remove `/admin` routes and navigation links.

**Tech Stack:** FastAPI, SQLAlchemy (SQLite), Next.js

---

### Task 1: Backend - Add SQLite Dependency

**Files:**
- Modify: `apps/server/requirements.txt`

**Step 1: Add aiosqlite to requirements**

Add `aiosqlite` to the file.

```text
aiosqlite
```

**Step 2: Install dependencies**

Run:
```bash
pip install aiosqlite
```

**Step 3: Commit**

```bash
git add apps/server/requirements.txt
git commit -m "chore(server): add aiosqlite dependency"
```

---

### Task 2: Backend - Remove Admin Router & Global Dependency

**Files:**
- Delete: `apps/server/app/routers/admin.py`
- Modify: `apps/server/app/main.py`
- Modify: `apps/server/app/dependencies.py`

**Step 1: Delete Admin Router**

Run:
```bash
rm apps/server/app/routers/admin.py
```

**Step 2: Remove Admin/RBAC from main.py**

Modify `apps/server/app/main.py`:
1. Remove `from app.routers import admin`
2. Remove `from app.dependencies import check_route_permissions`
3. Remove `dependencies=[Depends(check_route_permissions)]` from `FastAPI()`
4. Remove `app.include_router(admin.router)`

**Step 3: Update dependencies.py**

Modify `apps/server/app/dependencies.py` to remove `check_route_permissions` function. If the file becomes empty or unused, we can just clear it or leave only necessary deps.
(If `check_route_permissions` was the only thing, clear the file or remove it. Let's assume we empty it for now or check contents first. For now, remove the function).

**Step 4: Commit**

```bash
git add apps/server/app/
git commit -m "refactor(server): remove admin router and RBAC middleware"
```

---

### Task 3: Backend - Update Models (Remove RBAC)

**Files:**
- Modify: `apps/server/app/models.py`

**Step 1: Remove Admin/RBAC Models**

Open `apps/server/app/models.py` and remove:
- `class RoutePermission(Base): ...`
- `class RoleAssignmentRule(Base): ...`

**Step 2: Verify JSON Compatibility**

Ensure `JSON` is imported from `sqlalchemy` (it is already Generic).
Ensure `user.roles` and `route_permissions.roles` (deleted) usage is safe.
The `User` model uses `roles = Column(JSON, default=["user"])`. This works in SQLite with SQLAlchemy.

**Step 3: Commit**

```bash
git add apps/server/app/models.py
git commit -m "refactor(server): remove RoutePermission and RoleAssignmentRule models"
```

---

### Task 4: Backend - Configure SQLite

**Files:**
- Modify: `apps/server/app/core/config.py`

**Step 1: Update DATABASE_URL default**

Modify `apps/server/app/core/config.py`:
Change `DATABASE_URL` default value or logic to use SQLite.

```python
# Before
# DATABASE_URL: str

# After (Set default for dev)
DATABASE_URL: str = "sqlite+aiosqlite:///./gcs_lms.db"
```
(Or ensure `.env` is ignored/overridden if we want to force SQLite).
*Self-correction*: If `.env` exists, it might override. We should probably update `.env` if it exists, but modifying `config.py` default is a safe fallback.
Let's modify `config.py` to use `sqlite+aiosqlite:///./gcs_lms.db` if no env var is provided, AND we will create/update `.env` in execution.

**Step 2: Commit**

```bash
git add apps/server/app/core/config.py
git commit -m "config(server): set default DATABASE_URL to SQLite"
```

---

### Task 5: Backend - Reset Database

**Files:**
- Delete: `apps/server/migrations/` (if exists)
- Create: New DB

**Step 1: Clean up old migrations**

Run:
```bash
rm -rf apps/server/migrations
rm -f apps/server/gcs_lms.db
```

**Step 2: Initialize Database**

(Since we are switching to SQLite and removing Alembic migrations for now to simplify, we can just rely on `Base.metadata.create_all` if `main.py` or startup event does it. BUT, usually `alembic` is used.
For this "Agentic Testing" phase, we can use a script to init DB.)

Create `apps/server/scripts/init_db.py`:
```python
import asyncio
from app.database import engine, Base
from app.models import User # Import all models to register them

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized (SQLite)")

if __name__ == "__main__":
    asyncio.run(init_db())
```

**Step 3: Run Init Script**

Run:
```bash
cd apps/server && python scripts/init_db.py
```

**Step 4: Commit**

```bash
git add apps/server/scripts/init_db.py
git commit -m "chore(server): add init_db script for SQLite"
```

---

### Task 6: Client - Remove Admin Pages

**Files:**
- Delete: `apps/client/src/app/admin/`

**Step 1: Remove Admin Directory**

Run:
```bash
rm -rf apps/client/src/app/admin
```

**Step 2: Commit**

```bash
git add apps/client/src/app/
git commit -m "feat(client): remove admin pages"
```

---

### Task 7: Client - Remove Admin Navigation

**Files:**
- Modify: `apps/client/src/components/Navigation.tsx`

**Step 1: Remove Admin Link**

Remove the `{user?.roles.includes('admin') && ...}` block.

**Step 2: Commit**

```bash
git add apps/client/src/components/Navigation.tsx
git commit -m "feat(client): remove admin link from navigation"
```

---

### Task 8: Client - Update ProtectedRoute

**Files:**
- Modify: `apps/client/src/components/ProtectedRoute.tsx`

**Step 1: Remove adminOnly logic**

Remove `adminOnly` prop and the check:
`else if (!isLoading && adminOnly && !user?.roles.includes('admin')) { router.push('/'); }`

Simplify the component to only check `isAuthenticated`.

**Step 2: Commit**

```bash
git add apps/client/src/components/ProtectedRoute.tsx
git commit -m "feat(client): remove adminOnly check from ProtectedRoute"
```
