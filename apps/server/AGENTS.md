# AGENTS.md

Guidelines for AI coding agents working on GCS Auth Service.

## Project Overview

FastAPI-based Google OAuth 2.0 authentication backend with **Default DISALLOW** RBAC and terms consent management.
**Stack**: Python 3.11+, FastAPI, SQLAlchemy 2.0 (async), PostgreSQL (asyncpg), Authlib, Pydantic v2

## Build & Test Commands

### Setup
```bash
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

### Database
**CRITICAL**: Run this after adding any new API endpoint to sync permissions.
```bash
python scripts/migrate_and_seed.py
```

### Running Server
```bash
uvicorn app.main:app --reload
```

### Testing
```bash
# Run all tests (unit & integration)
pytest tests/

# Run a specific test file
pytest tests/test_role_rules.py -v

# Run a single test case
pytest tests/test_role_rules.py::test_email_pattern_rule -v

# Run E2E tests
pytest tests/test_e2e.py -v

# Verify RBAC implementation manually
python tests/verify_rbac.py
```

## Architecture

### Security Model: Default DISALLOW
All endpoints are **blocked by default**. `check_route_permissions` runs as a global dependency.
- **Flow**: Request → `check_route_permissions` → Query DB → Allow/403.
- **Tables**: `users`, `role_assignment_rules`, `route_permissions` (path+method), `terms`, `consents`.

### Key Files
- `app/main.py`: Entry point, global dependencies.
- `app/dependencies.py`: Auth/RBAC logic.
- `app/crud.py`: DB operations.
- `app/routers/`: API endpoints (`auth`, `admin`, `terms`).

## Code Style Guidelines

### 1. Imports
Order: stdlib → third-party → local.
```python
# stdlib
from typing import List, Optional
from datetime import datetime

# third-party
from fastapi import APIRouter, Depends
from sqlalchemy.future import select

# local
from app.database import get_db
from app.models import User
```

### 2. Type Hints
**MANDATORY** for all function signatures.
```python
async def get_user(db: AsyncSession, user_id: int) -> Optional[User]: ...
```

### 3. Async Database Patterns (SQLAlchemy 2.0)
- **Relationships**: ALWAYS use `selectinload` to prevent `MissingGreenlet` errors.
- **Query**:
  ```python
  result = await db.execute(
      select(User).options(selectinload(User.consents)).filter(User.id == uid)
  )
  user = result.scalars().first()
  ```
- **Write**:
  ```python
  db.add(new_item)
  await db.commit()
  await db.refresh(new_item)
  ```

### 4. Pydantic Schemas (v2)
- Use `ConfigDict(from_attributes=True)`.
- Naming: `{Name}Base`, `{Name}Create`, `{Name}Response`.
```python
class UserResponse(UserBase):
    id: int
    model_config = ConfigDict(from_attributes=True)
```

### 5. Error Handling
- Use `HTTPException` with specific status codes (400, 403, 404).
- **Never** catch generic `Exception` without re-raising or logging properly.

## Critical Patterns & Anti-Patterns

### New Endpoint Checklist
1. **Add Route**: Define in `app/routers/`.
2. **Sync DB**: Run `python scripts/migrate_and_seed.py`.
3. **Configure**: Set `is_public` or `roles` in `route_permissions` table.

### Testing
- **Session Mocking**: Use `itsdangerous` to sign session cookies in tests.
- **OAuth Mocking**: Patch `app.routers.auth.oauth.create_client` with `AsyncMock`.
- **Path Matching**: RBAC uses `request.scope["route"].path` (template path e.g. `/users/{id}`).

### Anti-Patterns (DO NOT DO)
- ❌ Accessing relationships without `selectinload` in async context.
- ❌ Adding endpoints without syncing `route_permissions`.
- ❌ Suppressing async errors with bare `except:`.
- ❌ Committing tokens/secrets to git.

## GitHub Copilot Integration
Internal Copilot client resides in `app/lib`.
- **Key Files**:
  - `app/lib/copilot_client.py`: Client wrapper.
  - `app/routers/ai.py`: OpenAI-compatible endpoint.
- **Configuration**:
  - `GITHUB_COPILOT_CREDENTIALS_JSON`: Env var for auth.
  - Scripts: `scripts/init_copilot_auth_print.py` (setup), `scripts/run_copilot_query.py` (test).
- **Security**: Never commit credentials. Use env vars.
