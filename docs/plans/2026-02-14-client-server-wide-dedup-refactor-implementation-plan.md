# Client/Server Wide Dedup Refactor Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 클라이언트/서버 전반의 중복 코드를 제거하고 구조를 단순화하되, API 계약/DB 스키마/사용자 화면 동작은 그대로 유지한다.

**Architecture:** 서버는 weekly 라우터 인증 경로를 daily와 동일한 공통 유틸(`snippet_utils.get_viewer_or_401`)로 통일하고, `crud.py`의 중복 토큰 함수 정의를 단일 블록으로 정리한다. 클라이언트는 daily/weekly 페이지의 공통 날짜/탐색/로딩 흐름을 공유 유틸로 추출하고, 분산된 auth/comment 타입을 단일 타입 모듈로 통합한다. 전체 변경은 내부 구현에만 한정하고 외부 계약(API/DB/UX)은 고정한다.

**Tech Stack:** FastAPI, SQLAlchemy, Pytest, Next.js 16, React 18, TypeScript, Vitest

---

## 작업 전 고정 원칙
- @superpowers:test-driven-development 방식으로 **테스트 먼저** 작성한다.
- DRY/YAGNI를 유지하고, 이번 범위에 없는 기능 추가는 금지한다.
- 각 Task 종료 시 작은 커밋 1개를 만든다.
- 작업은 별도 워크트리에서 진행한다. (필요 시 @superpowers:using-git-worktrees)

---

### Task 1: Weekly 라우터 인증 경로를 공통 유틸로 통일

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py:137-156`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/server/app/routers/weekly_snippets.py:25-29,52-56,90-94,140-143,164-167,223-226,251-254`
- Test: `/Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py`

**Step 1: Write the failing test**

`test_features.py`에 아래 테스트를 추가한다.

```python
@pytest.mark.asyncio
async def test_weekly_list_uses_shared_viewer_helper(client, regular_user_1, monkeypatch):
    from app.routers import snippet_utils

    call_count = {"value": 0}

    async def fake_get_viewer_or_401(request, db):
        call_count["value"] += 1
        return regular_user_1

    monkeypatch.setattr(snippet_utils, "get_viewer_or_401", fake_get_viewer_or_401)

    resp = client.get("/weekly-snippets", headers=auth_headers(regular_user_1))

    assert resp.status_code == 200
    assert call_count["value"] == 1
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py::test_weekly_list_uses_shared_viewer_helper -q
```

Expected: FAIL with `assert 0 == 1` (현재 weekly 라우터가 공통 helper를 호출하지 않기 때문)

**Step 3: Write minimal implementation**

`weekly_snippets.py`에서 각 엔드포인트의 중복 인증 블록을 공통 유틸 호출로 치환한다.

```python
# before
sub = _get_user_sub(request)
viewer = await crud.get_user_by_sub(db, sub)
if not viewer:
    raise HTTPException(status_code=401, detail="User not found")

# after
viewer = await _snippet_utils.get_viewer_or_401(request, db)
```

위 치환을 `get/list/create/organize/update/delete` 엔드포인트에 동일 적용한다.

**Step 4: Run tests to verify they pass**

Run:
```bash
python -m pytest /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py::test_weekly_list_uses_shared_viewer_helper /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py::test_weekly_snippets_flow -q
```

Expected: PASS (`2 passed`)

**Step 5: Commit**

```bash
git add /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py /Users/hexa/projects/temp/gcs-lms/apps/server/app/routers/weekly_snippets.py
git commit -m "refactor(server): unify weekly viewer auth path with snippet utils"
```

---

### Task 2: CRUD 토큰 함수 중복 정의 제거

**Files:**
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_crud_dedup.py`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/server/app/crud.py:278-323,447-491`
- Test: `/Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_tokens_idempotency.py`

**Step 1: Write the failing test**

`test_crud_dedup.py`를 생성하고 아래 테스트를 작성한다.

```python
import re
from pathlib import Path
from app import crud


def test_api_token_functions_defined_once():
    source = Path(crud.__file__).read_text(encoding="utf-8")

    assert len(re.findall(r"^async def create_api_token\(", source, flags=re.MULTILINE)) == 1
    assert len(re.findall(r"^async def list_api_tokens\(", source, flags=re.MULTILINE)) == 1
    assert len(re.findall(r"^async def delete_api_token\(", source, flags=re.MULTILINE)) == 1
```

**Step 2: Run test to verify it fails**

Run:
```bash
python -m pytest /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_crud_dedup.py -q
```

Expected: FAIL with `assert 2 == 1`

**Step 3: Write minimal implementation**

`crud.py`에서 두 번째 중복 블록(`create_api_token/list_api_tokens/delete_api_token`)을 제거하고 단일 정의만 남긴다.

```python
# keep first definition block only
async def create_api_token(...):
    ...

async def list_api_tokens(...):
    ...

async def delete_api_token(...):
    ...

# remove duplicated second block near end of file
```

**Step 4: Run tests to verify they pass**

Run:
```bash
python -m pytest /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_crud_dedup.py /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_tokens_idempotency.py -q
```

Expected: PASS

**Step 5: Commit**

```bash
git add /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_crud_dedup.py /Users/hexa/projects/temp/gcs-lms/apps/server/app/crud.py
git commit -m "refactor(server): remove duplicated api token CRUD definitions"
```

---

### Task 3: 클라이언트 날짜/이동 공통 유틸 추출

**Files:**
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/dateKeys.ts`
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/dateKeys.test.ts`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/daily-snippets/page.tsx:15-17,96-104`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/weekly-snippets/page.tsx:15-21,63-70,98-106`

**Step 1: Write the failing test**

`dateKeys.test.ts`에 아래 테스트를 작성한다.

```ts
import { describe, it, expect } from 'vitest';
import { toISODateKey, toWeeklyKey, getAdjacentKey } from './dateKeys';

describe('date key helpers', () => {
  it('builds daily key', () => {
    expect(toISODateKey(new Date('2026-02-14T00:00:00Z'))).toBe('2026-02-14');
  });

  it('normalizes weekly key to monday', () => {
    expect(toWeeklyKey(new Date('2026-02-15T00:00:00Z'))).toBe('2026-02-09');
  });

  it('returns adjacent keys by kind', () => {
    expect(getAdjacentKey('2026-02-14', 'daily', 'prev')).toBe('2026-02-13');
    expect(getAdjacentKey('2026-02-10', 'weekly', 'next')).toBe('2026-02-17');
  });
});
```

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/snippet-page/dateKeys.test.ts
```

Expected: FAIL with module-not-found (`./dateKeys`)

**Step 3: Write minimal implementation**

`dateKeys.ts`를 생성한다.

```ts
export type SnippetKind = 'daily' | 'weekly';

export function toISODateKey(date: Date): string {
  return date.toISOString().split('T')[0];
}

export function toWeeklyKey(date: Date): string {
  const d = new Date(date);
  const day = d.getDay();
  const diff = d.getDate() - day + (day === 0 ? -6 : 1);
  d.setDate(diff);
  return toISODateKey(d);
}

export function getAdjacentKey(
  currentKey: string,
  kind: SnippetKind,
  direction: 'prev' | 'next'
): string {
  const d = new Date(currentKey);
  const delta = kind === 'daily' ? 1 : 7;
  d.setDate(d.getDate() + (direction === 'next' ? delta : -delta));
  return toISODateKey(d);
}
```

이후 daily/weekly 페이지의 로컬 날짜 헬퍼를 위 유틸 import로 대체한다.

**Step 4: Run test to verify it passes**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/snippet-page/dateKeys.test.ts
```

Expected: PASS

**Step 5: Commit**

```bash
git add /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/dateKeys.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/dateKeys.test.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/app/daily-snippets/page.tsx /Users/hexa/projects/temp/gcs-lms/apps/client/src/app/weekly-snippets/page.tsx
git commit -m "refactor(client): extract shared snippet date key helpers"
```

---

### Task 4: daily/weekly 페이지 공통 로딩 로직 추출

**Files:**
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/loadSnippetPageData.ts`
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/loadSnippetPageData.test.ts`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/daily-snippets/page.tsx:35-122`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/weekly-snippets/page.tsx:38-124`

**Step 1: Write the failing test**

`loadSnippetPageData.test.ts`를 작성한다.

```ts
import { describe, it, expect } from 'vitest';
import { loadSnippetPageData } from './loadSnippetPageData';

function createFakeClient() {
  const calls: string[] = [];
  const client = {
    calls,
    async get(url: string): Promise<any> {
      calls.push(url);
      if (url === '/snippet_date') return { date: '2026-02-14' };
      if (url.startsWith('/daily-snippets?from_date=2026-02-14')) {
        return { items: [{ id: 101, date: '2026-02-14', content: 'x', editable: true }] };
      }
      if (url.startsWith('/daily-snippets?to_date=2026-02-13')) {
        return { items: [{ id: 100 }] };
      }
      if (url.startsWith('/daily-snippets?from_date=2026-02-15')) {
        return { items: [{ id: 102 }] };
      }
      throw new Error(`Unhandled URL: ${url}`);
    },
  };
  return client;
}

describe('loadSnippetPageData', () => {
  it('loads daily snippet and adjacent ids', async () => {
    const client = createFakeClient();

    const result = await loadSnippetPageData({
      kind: 'daily',
      idParam: null,
      fallbackKey: '2026-02-14',
      client,
      normalizeServerDate: (d) => d,
    });

    expect(result.snippet?.id).toBe(101);
    expect(result.prevId).toBe(100);
    expect(result.nextId).toBe(102);
    expect(result.readOnly).toBe(false);
  });
});
```

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/snippet-page/loadSnippetPageData.test.ts
```

Expected: FAIL with module-not-found (`./loadSnippetPageData`)

**Step 3: Write minimal implementation**

`loadSnippetPageData.ts`를 생성하고 페이지에서 이를 사용한다.

```ts
import { getAdjacentKey, type SnippetKind } from './dateKeys';

type ApiClient = { get<T = any>(url: string): Promise<T> };

type Params = {
  kind: SnippetKind;
  idParam: string | null;
  fallbackKey: string;
  client: ApiClient;
  normalizeServerDate: (serverDate: string) => string;
};

export async function loadSnippetPageData({ kind, idParam, fallbackKey, client, normalizeServerDate }: Params) {
  const endpoint = kind === 'daily' ? '/daily-snippets' : '/weekly-snippets';
  const keyName = kind === 'daily' ? 'date' : 'week';
  const fromKey = kind === 'daily' ? 'from_date' : 'from_week';
  const toKey = kind === 'daily' ? 'to_date' : 'to_week';

  let currentSnippet: any = null;
  let currentKey = fallbackKey;
  let serverKey = fallbackKey;

  const dateRes = await client.get<{ date: string }>('/snippet_date').catch(() => null);
  if (dateRes?.date) serverKey = normalizeServerDate(dateRes.date);

  if (idParam) {
    currentSnippet = await client.get(`${endpoint}/${idParam}`).catch(() => null);
  } else {
    const res = await client.get<any>(`${endpoint}?${fromKey}=${serverKey}&${toKey}=${serverKey}&limit=1`).catch(() => null);
    currentSnippet = res?.items?.[0] ?? null;
  }

  if (currentSnippet?.[keyName]) currentKey = currentSnippet[keyName];

  const serverEditable = currentSnippet?.editable;
  const readOnly = serverEditable === undefined ? currentKey < serverKey : !serverEditable;

  const prevKey = getAdjacentKey(currentKey, kind, 'prev');
  const nextKey = getAdjacentKey(currentKey, kind, 'next');

  const [prevRes, nextRes] = await Promise.all([
    client.get<any>(`${endpoint}?${toKey}=${prevKey}&order=desc&limit=1`),
    client.get<any>(`${endpoint}?${fromKey}=${nextKey}&order=asc&limit=1`),
  ]);

  return {
    snippet: currentSnippet,
    readOnly,
    prevId: prevRes?.items?.[0]?.id ?? null,
    nextId: nextRes?.items?.[0]?.id ?? null,
  };
}
```

daily/weekly 페이지에서는 기존 중복 `loadSnippet` 내부 본문을 위 helper 호출로 교체한다.

**Step 4: Run tests to verify it passes**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/snippet-page/dateKeys.test.ts src/lib/snippet-page/loadSnippetPageData.test.ts
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run build
```

Expected: PASS (Vitest 통과 + Next build 성공)

**Step 5: Commit**

```bash
git add /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/loadSnippetPageData.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/snippet-page/loadSnippetPageData.test.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/app/daily-snippets/page.tsx /Users/hexa/projects/temp/gcs-lms/apps/client/src/app/weekly-snippets/page.tsx
git commit -m "refactor(client): share snippet page loading flow for daily and weekly"
```

---

### Task 5: Auth/Comment 타입 단일 소스로 통합

**Files:**
- Create: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/types/dedup-guard.test.ts`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/types.ts:1-26`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/context/auth-context.tsx:6-27`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/CommentList.tsx:15-35`

**Step 1: Write the failing test**

`dedup-guard.test.ts`를 추가한다.

```ts
import fs from 'node:fs';
import { describe, it, expect } from 'vitest';

describe('type dedup guards', () => {
  it('auth-context should not declare local User interface', () => {
    const source = fs.readFileSync('src/context/auth-context.tsx', 'utf-8');
    expect(source).not.toMatch(/interface\s+User\s*\{/);
  });

  it('comment list should not declare local comment interfaces', () => {
    const source = fs.readFileSync('src/components/views/CommentList.tsx', 'utf-8');
    expect(source).not.toMatch(/interface\s+CommentUser\s*\{/);
    expect(source).not.toMatch(/interface\s+Comment\s*\{/);
  });
});
```

**Step 2: Run test to verify it fails**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/types/dedup-guard.test.ts
```

Expected: FAIL (현재 파일 내 로컬 interface 선언 존재)

**Step 3: Write minimal implementation**

`lib/types.ts`를 확장하고 auth/comment 컴포넌트에서 import 사용으로 전환한다.

```ts
// in lib/types.ts
export interface AuthConsent {
  term_id: number;
  agreed_at: string;
}

export interface AuthUser {
  id?: number;
  sub: string;
  email: string;
  name: string;
  picture: string;
  email_verified?: boolean;
  roles: string[];
  consents?: AuthConsent[];
}

export interface AuthStatusResponse {
  authenticated: boolean;
  user: AuthUser | null;
}

export interface CommentUser {
  id: number;
  name: string;
  email: string;
  picture?: string;
}

export interface Comment {
  id: number;
  user_id: number;
  user: CommentUser;
  daily_snippet_id?: number;
  weekly_snippet_id?: number;
  content: string;
  created_at: string;
  updated_at: string;
}
```

```ts
// in auth-context.tsx
import type { AuthStatusResponse, AuthUser } from '@/lib/types';
```

```ts
// in CommentList.tsx
import type { Comment } from '@/lib/types';
```

**Step 4: Run tests to verify they pass**

Run:
```bash
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run test -- src/lib/types/dedup-guard.test.ts src/lib/snippet-page/dateKeys.test.ts src/lib/snippet-page/loadSnippetPageData.test.ts
npm --prefix /Users/hexa/projects/temp/gcs-lms/apps/client run build
python -m pytest /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_features.py::test_weekly_snippets_flow /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_tokens_idempotency.py /Users/hexa/projects/temp/gcs-lms/apps/server/tests/test_snippet_editable_utils.py -q
```

Expected: PASS (클라 테스트/빌드 + 서버 타깃 테스트 통과)

**Step 5: Commit**

```bash
git add /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/types/dedup-guard.test.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/lib/types.ts /Users/hexa/projects/temp/gcs-lms/apps/client/src/context/auth-context.tsx /Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/CommentList.tsx
git commit -m "refactor(client): centralize auth and comment type definitions"
```

---

## 완료 조건 체크리스트
- [ ] weekly 라우터 인증 경로가 공통 helper 기반으로 통일됨
- [ ] `crud.py` 토큰 함수 중복 정의 제거됨
- [ ] daily/weekly 날짜/이동 로직 공통 유틸로 추출됨
- [ ] daily/weekly 로딩 흐름 공통 helper로 추출됨
- [ ] auth/comment 타입 단일 소스화 완료됨
- [ ] API 계약/DB 스키마 변경 없음이 확인됨
- [ ] 서버/클라 검증 명령 모두 통과함

---

Plan complete and saved to `docs/plans/2026-02-14-client-server-wide-dedup-refactor-implementation-plan.md`. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per task, review between tasks, fast iteration

2. Parallel Session (separate) - Open new session with executing-plans, batch execution with checkpoints

Which approach?
