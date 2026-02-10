# Snippet Error, Time, Team & Token Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement strict time constraints for snippets, a team snippet feed, API token management, and a standardized error UI.

**Architecture:**
- **Time Constraints:** Python backend logic in `utils_time.py` enforcing 9:00 AM cutoff for daily/weekly snippet creation/edits.
- **Team View:** React frontend using a unified feed component fetching snippets with a `scope=team` parameter (or implied access).
- **Tokens:** New `api_tokens` table and CRUD endpoints for managing long-lived access tokens.
- **Error UI:** Global error toast (Sonner) and a dedicated Error View component for routing errors.

**Tech Stack:** FastAPI, SQLAlchemy, Next.js 14 (App Router), Tailwind CSS, Shadcn UI (Sonner).

---

## Phase 1: Backend - Time Constraints & API Tokens

### Task 1: Implement Strict Time Validation Logic

**Files:**
- Modify: `apps/server/app/utils_time.py`
- Test: `apps/server/tests/test_utils_time.py` (Create new)

**Step 1.1: Create test file `apps/server/tests/test_utils_time.py`**
- Test `validate_snippet_date` with current date (pass) and future/past date (fail).
- Test `validate_snippet_week` with current week (pass) and future/past week (fail).
- Mock `datetime.now()` to simulate before/after 9:00 AM scenarios.

**Step 1.2: Implement validation functions in `apps/server/app/utils_time.py`**
- Add `validate_snippet_date(target_date: date)`:
  - If `target_date != current_business_date(now)`, raise `HTTPException(400, "Invalid date")`.
- Add `validate_snippet_week(target_week: date)`:
  - If `target_week != current_business_week_start(now)`, raise `HTTPException(400, "Invalid week")`.

**Step 1.3: Run tests**
- `pytest apps/server/tests/test_utils_time.py`

### Task 2: Enforce Time Constraints in Snippet Routes

**Files:**
- Modify: `apps/server/app/routers/daily_snippets.py`
- Modify: `apps/server/app/routers/weekly_snippets.py`

**Step 2.1: Update `create_daily_snippet` and `update_daily_snippet`**
- Call `validate_snippet_date(payload.date)` (if date is in payload) OR ensure date is derived from server time.
- *Correction*: The current implementation `create_daily_snippet` calculates date on server: `snippet_date = current_business_date(now)`.
- **Change**: We need to allow the client to *attempt* to send a date (if we supported it), but the requirement says "time is checked on server".
- **Refinement**: Since the *server* decides the date in `create_daily_snippet`, we just need to ensure `update_daily_snippet` also respects the window.
- **Logic**:
  - `create`: No change needed if it always uses `current_business_date`.
  - `update`: `require_daily_snippet_not_past` is already there. CHECK if it allows editing *today's* snippet.
  - **Requirement Check**: "Time is checked on server and if wrong, error". This implies the client MIGHT send a date.
  - **Decision**: Modify `DailySnippetCreate` schema to OPTIONALLY accept a date? No, the requirement says "server checks time".
  - **Action**: Just ensure the existing `require_daily_snippet_not_past` logic is strict enough. Currently it says "Past date is read-only".
  - **Strictness**: Ensure `update` only allows the *current business date*.
  - **Edit**: In `daily_snippets.py`, update `update_daily_snippet` to use `validate_snippet_date(snippet.date)`.

**Step 2.2: Update `weekly_snippets.py`**
- Similar to daily, ensure `update` calls `validate_snippet_week(snippet.week)`.

### Task 3: API Token Model & Migration

**Files:**
- Modify: `apps/server/app/models.py`
- Create: `apps/server/scripts/migrations/versions/xxxx_add_api_tokens.py` (if using alembic) OR just update `models.py` and rely on `init_db` if dev mode.
- *Note*: We'll assume dev mode `init_db` syncs models or manual SQL if no migration tool active. We will add the model.

**Step 3.1: Add `ApiToken` model to `models.py`**
- Columns: `id` (int), `user_id` (int, FK), `token_hash` (str), `description` (str), `created_at` (datetime).

**Step 3.2: Create migration/schema update**
- If `alembic` is configured, generate migration. If not, just update the model class.

### Task 4: API Token Routes

**Files:**
- Create: `apps/server/app/routers/tokens.py`
- Modify: `apps/server/app/main.py` (include router)

**Step 4.1: Implement CRUD**
- `GET /auth/tokens`: List tokens for current user.
- `POST /auth/tokens`: Generate random string, hash it, store hash, return raw string.
- `DELETE /auth/tokens/{id}`: Delete token.

## Phase 2: Frontend - Error UI, Team View, Settings

### Task 5: Common Error UI

**Files:**
- Create: `apps/client/src/components/views/ErrorView.tsx`
- Modify: `apps/client/src/lib/api.ts`

**Step 5.1: Create `ErrorView`**
- Props: `code` (number), `message` (string).
- UI: Centered, styled with `design-system.md` tokens.

**Step 5.2: Update `api.ts`**
- Import `toast` from `sonner`.
- In `apiFetch` catch block, call `toast.error(message)`.

### Task 6: Team Snippet Feed

**Files:**
- Create: `apps/client/src/components/views/TeamSnippetFeed.tsx`
- Create: `apps/client/src/components/views/TeamSnippetCard.tsx`
- Modify: `apps/client/src/app/daily-snippets/page.tsx` (add tab or toggle)

**Step 6.1: Create `TeamSnippetCard`**
- Reuse `SnippetItem` styles but add User Avatar/Name header.
- Include `SnippetAnalysisReport` (collapsed by default).

**Step 6.2: Create `TeamSnippetFeed`**
- Fetch snippets with `scope=team` (if backend supports) OR filter client side if list returns all.
- *Backend Update Check*: `list_daily_snippets` in `crud.py` filters by viewer?
- *Check*: `crud.list_daily_snippets` usually filters by `user_id=viewer.id`.
- **Correction**: We need to update backend `crud.py` to allow fetching team snippets.

### Task 7: Update Backend List Logic for Team

**Files:**
- Modify: `apps/server/app/crud.py`
- Modify: `apps/server/app/routers/daily_snippets.py`

**Step 7.1: Update `list_daily_snippets` in `crud.py`**
- Add `scope` parameter (default 'own').
- If `scope == 'team'`, filter by `user.team_id == viewer.team_id`.

**Step 7.2: Update Router**
- Accept `scope: str = "own"` query param.
- Pass to crud.

### Task 8: Settings & Token Management UI

**Files:**
- Create: `apps/client/src/app/settings/page.tsx`
- Create: `apps/client/src/components/views/TokenManager.tsx`

**Step 8.1: Create `TokenManager` component**
- List tokens (table).
- "Generate Token" button -> Dialog -> Show token -> API call.
- Delete button -> Confirm -> API call.

**Step 8.2: Create Settings Page**
- Layout with "Profile" (placeholder) and "API Tokens" sections.
- Embed `TokenManager`.

---
