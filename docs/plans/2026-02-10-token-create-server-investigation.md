I'm using the writing-plans skill to create the implementation plan.

# Token 생성: 서버-클라이언트 응답 불일치 조사 및 중복 방지 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 클라이언트가 POST 요청 직후 네트워크 오류를 받는데도 서버에는 토큰이 생성되는 문제를 재현·진단하고, 근본적으로 중복 생성이 발생하지 않도록 안전한 서버/클라이언트 조치를 도입한다.

**Architecture:** 문제는 네트워크 응답/연결 손실 또는 인프라(프록시/CORS/타임아웃)로 클라이언트가 응답을 받지 못하는 상황에서 발생합니다. 우선 재현과 로그/타이밍을 통해 원인을 규명한 뒤, 단기적으로는 클라이언트에서 비파괴적 재시도를 차단(이미 적용됨)하고, 중장기적으로는 서버에서 idempotency-key 기반 보장을 추가하여 동일 요청이 중복으로 처리되지 않게 한다.

**Tech Stack:** Python (FastAPI), SQLAlchemy (Async), PostgreSQL, TypeScript (Next.js), fetch API, pytest

---

### Task 1: 로컬 재현 및 네트워크 캡처 (진단 시작)

**Files:** (수정 없음)

**Step 1: Start dev servers**
Run:
```
# 터미널 A: 루트에서 turborepo dev
cd /Users/hexa/projects/temp/gcs-mono
npx turbo run dev
```
Expected: 클라이언트(Next)와 서버(FastAPI)가 실행됨. 서버는 기본적으로 http://localhost:8000 에 바인딩.

**Step 2: 재현(브라우저)**
- Open: http://localhost:3000 → TokenManager 화면 → 새 토큰 생성 → 생성하기
Expected: 증상 재현(다이얼로그에서 "백엔드가 실행되는지 확인" 토스트가 뜸) 및 이후 새로고침 시 토큰이 보임.

**Step 3: 클라이언트 네트워크 캡처**
Run (local machine):
- 브라우저 DevTools Network 탭에서 POST /auth/tokens 요청을 선택
- 또는 curl로 동일 요청 실행 (세션에서 cookie 포함 필요)

Example curl (cookie-based 세션이 있으면 사용):
```
curl -v -X POST http://localhost:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{"description": "test-desc"}'
```
Expected:
- curl 출력에 HTTP status (201/200) 또는 connection error 정보가 보임. 만약 curl에서도 응답이 정상(200/201)인데 브라우저에서 실패라면 브라우저-프록시/CORS/credential 이슈 가능성이 높음.

---

### Task 2: 서버 로그/타이밍 증거 수집

**Files:** (수정 없음 for now) `/Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py` and `/Users/hexa/projects/temp/gcs-mono/apps/server/app/crud.py`

**Step 1: 활성화된 서버 로그 수준 올리기**
Run (in server env):
- Set uvicorn debug logging or run with --reload --log-level debug
```
# from repo root
cd /Users/hexa/projects/temp/gcs-mono/apps/server
uvicorn app.main:app --reload --log-level debug
```
Expected: 각 요청에 대한 상세 로그(접속, 처리, 예외)가 콘솔에 찍힘.

**Step 2: 원자적 로그 추가(임시)**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py:24-38 (wrap create_token to log before/after db commit)

Modify lines:
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py:24-38

**Step 3: Add minimal logging**
Insert (example):
```python
import time, logging
logger = logging.getLogger(__name__)

@router.post("", response_model=schemas.NewApiTokenResponse)
async def create_token(...):
    start = time.time()
    logger.debug(f"create_token: start user_id={user.id} desc={payload.description}")
    db_token, raw_token = await crud.create_api_token(db, user.id, payload.description)
    logger.debug(f"create_token: committed user_id={user.id} token_id={db_token.id} elapsed={time.time()-start}")
    response = schemas.NewApiTokenResponse.model_validate(db_token)
    response.token = raw_token
    logger.debug(f"create_token: returning response user_id={user.id} token_id={db_token.id}")
    return response
```

**Step 4: Reproduce with logging on**
- Perform the same browser POST and observe server console logs: we need to see the sequence: request received → commit logged → return logged. If commit logged but client gets connection error, it indicates network loss after commit.

Expected:
- Server logs show timing (commit happened) and return attempted. If server logs stop before return, server-side error occurred.

---

### Task 3: Verify DB commit timing and network response with curl (fast path)

**Files:** (use existing server and DB)

**Step 1: Direct curl test (no browser)**
Run (from dev machine):
```
curl -v -X POST http://localhost:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -d '{"description": "curl-test-$(date +%s)"}'
```
Expected:
- If curl receives HTTP 200/201 and JSON body with token, server returned correctly. If curl fails with connection error while server logs indicate commit, then network stack is suspect.

**Step 2: Check DB for token row**
Run (psql or SQL):
```
# adjust connection settings as needed
psql $DATABASE_URL -c "SELECT id, description, created_at FROM api_token WHERE description LIKE 'curl-test-%' ORDER BY created_at DESC LIMIT 5;"
```
Expected: row exists matching the description if commit succeeded.

---

### Task 4: Instrument server response path for low-level failure (if needed)

**Files to modify (temporary instrumentation):**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py:24-38 (add try/except around return and log exception)

**Step 1: wrap response with try/except**
```python
try:
    return response
except Exception as e:
    logger.exception("create_token: error while returning response")
    # still return 500 to client
    raise
```

Expected: If an exception is thrown while serializing/returning response, it will be logged here.

---

### Task 5: Short-term mitigation (server-side idempotency support) — design + implement minimal safe option

Rationale: 네트워크 불안정으로 인해 클라이언트가 응답을 못 받는 경우에도 서버가 동일한 요청을 중복 처리하지 않도록 idempotency-key 기반 보장 추가를 권장합니다. 이 변경은 서버·DB에 약간의 작업이 필요합니다.

**Files to change:**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/models.py (add optional column `idempotency_key`) *and create DB migration or SQL script*
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/crud.py:258-272 (create_api_token) to accept optional idempotency_key and return existing token if present
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py:24-38 to read header `Idempotency-Key` and pass to crud
- Create: /Users/hexa/projects/temp/gcs-mono/apps/server/scripts/0001_add_idempotency_key.sql (SQL migration)

**DB migration SQL (create file):**
Create: /Users/hexa/projects/temp/gcs-mono/apps/server/scripts/0001_add_idempotency_key.sql
```sql
ALTER TABLE api_token ADD COLUMN idempotency_key VARCHAR(255);
CREATE UNIQUE INDEX IF NOT EXISTS ux_api_token_user_id_idempotency_key ON api_token (user_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
```
Expected: allows optional idempotency_key per user and prevents duplicate rows for same key.

**Server code changes (crud):**
Modify function signature and logic:
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/crud.py:258-272

Example change (complete code block to paste):
```python
async def create_api_token(
    db: AsyncSession, user_id: int, description: str, idempotency_key: Optional[str] = None
) -> Tuple[ApiToken, str]:
    # If idempotency_key provided, check existing
    if idempotency_key:
        result = await db.execute(
            select(ApiToken).filter(ApiToken.user_id == user_id, ApiToken.idempotency_key == idempotency_key)
        )
        existing = result.scalars().first()
        if existing:
            # No raw token available; return existing db object and empty raw token (caller should not expect raw token again)
            return existing, ''

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode()).hexdigest()

    db_token = ApiToken(
        user_id=user_id,
        token_hash=token_hash,
        description=description,
        idempotency_key=idempotency_key,
    )
    db.add(db_token)
    await db.commit()
    await db.refresh(db_token)
    return db_token, raw_token
```

**Router change (read header):**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/tokens.py:24-38
Add reading header and passing to crud:
```python
from fastapi import Header

@router.post("", response_model=schemas.NewApiTokenResponse)
async def create_token(
    payload: schemas.ApiTokenCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_active_user),
    idempotency_key: Optional[str] = Header(None, alias='Idempotency-Key'),
):
    db_token, raw_token = await crud.create_api_token(db, user.id, payload.description, idempotency_key)
    response = schemas.NewApiTokenResponse.model_validate(db_token)
    response.token = raw_token
    return response
```

**Step 1: Apply SQL migration**
Run (db connection env):
```
psql $DATABASE_URL -f /Users/hexa/projects/temp/gcs-mono/apps/server/scripts/0001_add_idempotency_key.sql
```
Expected: ALTER TABLE success and index created.

**Step 2: Update server code and restart server**
Run:
```
# edit files, then restart
uvicorn app.main:app --reload
```

**Step 3: Client: send Idempotency-Key** (minimal client change)
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TokenManager.tsx:54-69 (handleCreateToken) to generate a UUID and include header in api.post options.

Client code example (exact snippet):
```ts
import { v4 as uuidv4 } from 'uuid';

const idempotencyKey = uuidv4();
const result = await api.post<APITokenCreateResponse>('/auth/tokens', { description }, { headers: { 'Idempotency-Key': idempotencyKey } });
```
Expected: If request is retried or duplicated, server deduplicates by idempotency_key and returns existing record instead of creating a new one.

Commit messages:
- Server migration + code: "feat(server): add idempotency_key support to api_token to prevent duplicate token creation\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
- Client: "feat(client): send Idempotency-Key for token creation to prevent duplicates\n\nCo-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"

---

### Task 6: Tests (unit + integration)

**Files to create/test:**
- Create: /Users/hexa/projects/temp/gcs-mono/apps/server/tests/test_tokens_idempotency.py

Test 1: idempotency prevents duplicate
**Step 1: Write failing test**
```python
# /Users/hexa/projects/temp/gcs-mono/apps/server/tests/test_tokens_idempotency.py
import pytest
from httpx import AsyncClient
from app.main import app

@pytest.mark.asyncio
async def test_create_token_idempotent(async_db):
    async with AsyncClient(app=app, base_url='http://test') as ac:
        headers = {'Idempotency-Key': 'test-key-123'}
        r1 = await ac.post('/auth/tokens', json={'description': 'dup-test'}, headers=headers)
        r2 = await ac.post('/auth/tokens', json={'description': 'dup-test'}, headers=headers)
        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json()['id'] == r2.json()['id']
```

**Step 2: Run test**
Run:
```
cd /Users/hexa/projects/temp/gcs-mono/apps/server
pytest -q tests/test_tokens_idempotency.py::test_create_token_idempotent -q
```
Expected: PASS (single DB row created, both responses reference same id)

---

### Task 7: Manual verification checklist

1. Apply DB migration and restart server.
2. Update client to send Idempotency-Key header; rebuild client.
3. Reproduce with network flakiness (stop backend after commit, or simulate slow responses) and confirm:
   - Refresh shows token exists
   - UI no longer shows confusing network error when server returned successfully (if error persists, server-side response path/logging must be checked)
   - Duplicate tokens are not created when same Idempotency-Key used

Commands summary for verification:
```
# Apply migration
psql $DATABASE_URL -f /Users/hexa/projects/temp/gcs-mono/apps/server/scripts/0001_add_idempotency_key.sql

# Restart server
cd /Users/hexa/projects/temp/gcs-mono/apps/server
uvicorn app.main:app --reload --log-level debug

# Update client (if changed)
cd /Users/hexa/projects/temp/gcs-mono
npm install # if adding uuid
npx turbo run dev
```

---

Plan file saved to: /Users/hexa/projects/temp/gcs-mono/docs/plans/2026-02-10-token-create-server-investigation.md

Execution options:
1. Subagent-Driven (this session) — 제가 단계별로 수정/커밋/검증을 진행합니다. (REQUIRED SUB-SKILL: superpowers:subagent-driven-development)
2. Parallel Session (separate worktree) — 새 worktree 만들고 superpowers:executing-plans로 배치 실행합니다.

어떤 방식으로 진행할까요? (1 또는 2)