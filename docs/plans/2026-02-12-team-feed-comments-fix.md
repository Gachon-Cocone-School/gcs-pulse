I'm using the writing-plans skill to create the implementation plan.

# Team Feed Comments Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix the client-side "comments show 0 but actually 2" bug and the Console ApiError (Failed to fetch) originating from fetchWithRetry, plus add tests and small server sanity-check for the comments endpoint.

**Architecture:** Debug and harden the client fetch helper (apps/client/src/lib/api.ts), ensure CommentList component handles responses and errors correctly (apps/client/src/components/views/CommentList.tsx), and verify the server comments router returns expected data (apps/server/app/routers/comments.py). Keep changes minimal and TDD-driven.

**Tech Stack:** Next.js 16 (React 18), TypeScript, React Testing Library / Vitest (client), FastAPI, pytest (server), SQLAlchemy (server).

---

### Task 1: Investigate and add observability to fetchWithRetry

**Files:**
- Modify: `apps/client/src/lib/api.ts` (add temporary logging and a focused unit test)
- Test: `apps/client/tests/lib/api.test.ts` (create)

Step 1: Write the failing test (client unit test mocking global fetch)

```ts
// apps/client/tests/lib/api.test.ts
import { fetchWithRetry } from '../../../src/lib/api';

describe('fetchWithRetry', () => {
  it('throws ApiError(status=0) when fetch rejects with network error', async () => {
    global.fetch = jest.fn(() => Promise.reject(new TypeError('Failed to fetch')));

    await expect(fetchWithRetry('/api/test', { method: 'GET' })).rejects.toMatchObject({ status: 0 });

    // restore
    (global.fetch as any).mockRestore?.();
  });
});
```

Step 2: Run test to verify it fails (expected: test runs but implementation might already throw; this ensures behavior is reproducible)

Run: `npm --prefix apps/client test -- apps/client/tests/lib/api.test.ts -t "fetchWithRetry"`
Expected: Test runs and currently should either PASS or FAIL depending on current implementation; this documents behavior.

Step 3: Make minimal, safe change to add logging and ensure ApiError is thrown with helpful message

Modify `apps/client/src/lib/api.ts` around fetchWithRetry to log the error before throwing (example patch below). Keep behavior (status=0) the same so callers still receive ApiError, but add console.error with URL and error. This helps reproduce the CI/local issue and clarifies whether URL is wrong or server unreachable.

```ts
// apps/client/src/lib/api.ts (patch example)
async function fetchWithRetry(input: RequestInfo, init?: RequestInit, retries = 3, backoff = 200) {
  try {
    const res = await fetch(input, init);
    // existing logic unchanged
  } catch (err) {
    console.error('[fetchWithRetry] network error for', input, err);
    const message = err instanceof Error ? err.message : String(err);
    // preserve existing ApiError behavior
    throw new ApiError(message, 0);
  }
}
```

Step 4: Run the unit test again

Run: `npm --prefix apps/client test -- apps/client/tests/lib/api.test.ts -t "fetchWithRetry"`
Expected: PASS (test asserts ApiError with status 0)

Step 5: Commit

```bash
git add apps/client/src/lib/api.ts apps/client/tests/lib/api.test.ts
git commit -m "fix(client): add logging to fetchWithRetry and add unit test for network error\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Fix CommentList rendering and defensive error handling

**Files:**
- Modify: `apps/client/src/components/views/CommentList.tsx:1-200` (adjust rendering logic and error handling)
- Create: `apps/client/src/components/views/__tests__/CommentList.test.tsx`

Step 1: Read the current component to understand logic (developer should open file)

File path: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/CommentList.tsx`

Step 2: Write a failing test that mounts CommentList with two comments and asserts that the visible count is 2

```tsx
// apps/client/src/components/views/__tests__/CommentList.test.tsx
import React from 'react';
import { render, screen } from '@testing-library/react';
import CommentList from '../../CommentList';

const comments = [
  { id: '1', body: 'First', author: { name: 'A' } },
  { id: '2', body: 'Second', author: { name: 'B' } },
];

test('renders correct comment count', () => {
  render(<CommentList comments={comments} />);
  expect(screen.getByText(/2 comments/i)).toBeInTheDocument();
});
```

Step 3: Run test to verify it fails (expected: fail if component currently shows 0)

Run: `npm --prefix apps/client test -- apps/client/src/components/views/__tests__/CommentList.test.tsx -t "renders correct comment count"`
Expected: FAIL (reproduces bug locally)

Step 4: Implement minimal fix in CommentList.tsx

- Defend against undefined comments (use default []), and compute count from array length
- Ensure UI text uses pluralization properly (0/1/2)
- Ensure fetchErrors set to visible error state instead of silently swallowing

Example change (replace or patch relevant block):

```tsx
// apps/client/src/components/views/CommentList.tsx (excerpt)
export default function CommentList({ comments = [] }: { comments?: Comment[] }) {
  const count = Array.isArray(comments) ? comments.length : 0;

  return (
    <div>
      <div data-testid="comment-count">{count} {count === 1 ? 'comment' : 'comments'}</div>
      {comments.map((c) => (
        <div key={c.id}>{c.body}</div>
      ))}
    </div>
  );
}
```

Step 5: Run the test and local storybook/playground if available

Run: `npm --prefix apps/client test -- apps/client/src/components/views/__tests__/CommentList.test.tsx -t "renders correct comment count"`
Expected: PASS

Step 6: Commit

```bash
git add apps/client/src/components/views/CommentList.tsx apps/client/src/components/views/__tests__/CommentList.test.tsx
git commit -m "fix(client): defensive CommentList rendering and correct comment count\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Server: sanity-check comments router and add an integration test

**Files:**
- Create/Modify: `apps/server/app/routers/comments.py`
- Test: `apps/server/tests/test_comments_routes.py`

Step 1: Write a pytest that calls the comments endpoint for a known snippet and expects 200 and a list of comments length 2 (adjust snippet id to match seed data)

```py
# apps/server/tests/test_comments_routes.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_comments_for_snippet():
    # adjust snippet_id to a seeded value; if none seeded, create via fixture
    snippet_id = 1
    r = client.get(f"/api/snippets/{snippet_id}/comments")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # expect at least 2 comments in seeded DB
```

Step 2: Run pytest for this test

Run: `pytest apps/server/tests/test_comments_routes.py::test_get_comments_for_snippet -q`
Expected: FAIL if route missing or returns network error; otherwise PASS.

Step 3: If failing, implement minimal FastAPI route at `apps/server/app/routers/comments.py` that queries DB and returns comments (follow existing patterns in other routers). Example sketch:

```py
# apps/server/app/routers/comments.py
from fastapi import APIRouter, Depends
from app import crud, schemas

router = APIRouter(prefix='/api')

@router.get('/snippets/{snippet_id}/comments')
async def get_comments(snippet_id: int):
    comments = await crud.get_comments_for_snippet(snippet_id)
    return [schemas.Comment.from_orm(c).dict() for c in comments]
```

Step 4: Run pytest again

Run: `pytest apps/server/tests/test_comments_routes.py::test_get_comments_for_snippet -q`
Expected: PASS

Step 5: Commit server changes

```bash
git add apps/server/app/routers/comments.py apps/server/tests/test_comments_routes.py
git commit -m "feat(server): add comments router and integration test for snippet comments\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: Manual integration and UI verification

**Files:**
- No file changes, run and verify

Step 1: Start server and client dev servers

Run server (in separate terminal):
```
cd apps/server
python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
uvicorn app.main:app --reload
```

Run client:
```
cd apps/client
npm install
npm run dev
```

Step 2: Open the team feed UI (local URL shown by Next dev) and navigate to the snippet that previously showed 0 comments.
Expected: UI shows 2 comments and no Console "Failed to fetch" error. If Console still shows error, check logs printed from fetchWithRetry (Task 1).

Step 3: If fetch shows network error, inspect the logged URL from fetchWithRetry and verify the client is calling the correct path (e.g., `/api/...`) and that the server route exists and isn't blocked by CORS. Adjust base URL in client API if necessary (file: `apps/client/src/lib/api.ts` or `apps/client/src/lib/config.ts`).

Step 4: If fixes were required, repeat focused tests (client unit test, server pytest) and commit changes.

---

### Task 5: Final verification and PR prep

Step 1: Run full server tests

Run: `pytest -q` inside `apps/server`
Expected: All tests pass

Step 2: Run client tests

Run: `npm --prefix apps/client test`
Expected: All client tests (new and existing) pass

Step 3: Create a focused branch and PR (if not already on one). Provide PR template notes explaining the debugging logs added and that temporary console logs were added and should be removed after successful deployment. Prefer small follow-up to remove logging.

Commit message guidance: short summary and body with rationale. Example:

```
git checkout -b fix/team-feed-comments
# after changes
git add ...
git commit -m "fix(client/server): ensure comments endpoint and client rendering show correct counts; add tests\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

Execution handoff

Plan complete and saved to `docs/plans/2026-02-12-team-feed-comments-fix.md`. Two execution options:

1) Subagent-Driven (this session) - I dispatch a focused subagent per task, implement tests and code changes step-by-step, and request review between tasks (@superpowers:subagent-driven-development required).

2) Parallel Session (separate) - Open a new isolated worktree and run @superpowers:executing-plans in a separate session to execute the plan in batch with checkpoints.

Which approach do you want? Reply with the option label (1 or 2). If you want me to start implementing now, choose 1 and I will begin with Task 1.
