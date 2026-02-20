I'm using the writing-plans skill to create the implementation plan.

# Token 생성시 `fetch` 네트워크 오류 처리 개선 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** TokenManager에서 API 호출 실패 시 브라우저 콘솔에 보이는 원시 TypeError("Failed to fetch")를 명확한 에러/토스트로 대체하고 재시도 로직과 네트워크 오류 래핑을 일관되게 처리하여 UX와 디버깅 정보를 개선한다.

**Architecture:** 프론트엔드에서 사용하는 fetch 재시도(fetchWithRetry)와 apiFetch의 네트워크 예외 처리를 명확화한다. fetchWithRetry가 네트워크(원시) 에러를 잡아 ApiError(status=0)로 변환하여 상위 로직이 일관되게 처리하도록 한다. 또한 apiFetch의 네트워크-캐치 블록 메시지를 ApiError로 바꾸어 호출부에서 에러 타입을 판별 가능하게 한다.

**Tech Stack:** TypeScript, Next.js (App Router), React, sonner(toasts)

---

### Task 1: 버그 재현 (환경 확인)

**Files:** (수정 없음)

**Step 1: 개발 서버 기동**

Run: npx turbo run dev

Expected: dev 서버가 클라이언트(Next)와 서버(FastAPI)를 실행함. Next는 보통 http://localhost:3000, 백엔드는 http://localhost:8000에서 동작.

**Step 2: 브라우저에서 토큰 생성 시도**

- Open: http://localhost:3000 (로그인 필요 시 로그인)
- Navigate to: API 액세스 토큰(TokenManager) 화면
- 클릭: 새 토큰 생성 → 설명 입력 → 생성하기

Expected: 현재 실패 상태에서는 브라우저 콘솔에 TypeError: Failed to fetch (src/lib/api.ts:18) 같은 스택이 보이고, UI에는 실패 안내 토스트가 뜰 수 있음. 이 재현은 문제의 원인을 확인(백엔드 미실행, CORS, 잘못된 API_URL)하는 데 도움이 됨.

Notes: 만약 백엔드가 내려가 있거나 CORS 정책으로 인해 fetch가 실패하는 경우, 먼저 백엔드를 기동하거나 CORS 설정을 검토해야 함. 그러나 클라이언트 쪽에서도 사용자에게 더 친절한 에러(네트워크 오류 토스트)와 일관된 예외 타입을 제공해야 함.

---

### Task 2: fetchWithRetry에서 네트워크 에러를 ApiError(status=0)로 래핑

**Files:**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/client/src/lib/api.ts:15-24

**Step 1: Write the failing test**
- (간단한 수동/단위 검증) 브라우저 콘솔에서 원래 동작(원시 TypeError 노출)을 확인합니다.

**Step 2: Run to verify it fails**
- 재현 단계(위 Task 1)를 따라 "Failed to fetch"가 콘솔에 출력되는지 확인.

**Step 3: Write minimal implementation**
Replace the fetchWithRetry implementation with the following code (완전한 코드 블록):

```ts
// /Users/hexa/projects/temp/gcs-mono/apps/client/src/lib/api.ts
// 기존 재시도 헬퍼를 더 명확한 네트워크 에러 래핑으로 교체
async function fetchWithRetry(url: string, options: RequestInit, retries = 3, backoff = 300) {
  try {
    return await fetch(url, options);
  } catch (err: any) {
    // 네이티브 fetch는 네트워크 문제 또는 CORS 문제에서 TypeError를 던집니다.
    // 여기서 ApiError(status=0)로 래핑하여 상위 로직이 일관되게 처리하도록 합니다.
    const message = err?.message || 'Network request failed';
    if (retries <= 1) {
      // 0 상태 코드를 사용해 네트워크 레벨 오류를 구분합니다.
      throw new ApiError(message, 0);
    }
    await new Promise((r) => setTimeout(r, backoff));
    return fetchWithRetry(url, options, retries - 1, backoff * 2);
  }
}
```

**Step 4: Run to verify**
- Reproduce the token create flow in the browser. Expected: fetchWithRetry가 원시 TypeError를 던지지 않고, ApiError(status=0)로 던져져 apiFetch의 catch에서 ApiError로 인식되어 재처리됩니다.

**Step 5: Commit**

```bash
git add apps/client/src/lib/api.ts
git commit -m "fix(client): wrap network fetch errors in ApiError(status=0) to improve token create error handling

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: apiFetch의 네트워크 예외 처리 일관화

**Files:**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/client/src/lib/api.ts:69-79

**Step 1: Write the failing test**
- 수동: 토큰 생성 시 콘솔/토스트가 기존과 동일하게 노출되는지 확인(현재 실패 케이스).

**Step 2: Run to verify it fails**
- Task 1 재현 단계를 다시 수행하여 기존 동작을 확인.

**Step 3: Write minimal implementation**
Replace the apiFetch catch block (lines around 69-79) with this implementation so 네트워크(ApiError with status 0)를 명확히 토스트/로깅하고 ApiError로 재던집니다:

```ts
  } catch (error) {
    if (error instanceof ApiError) {
      // 이미 ApiError로 래핑되어 있으면 그대로 다시 던집니다.
      throw error;
    }

    // 네트워크/환경 오류: ApiError(status=0)를 던져 호출부가 상태를 판별할 수 있게 합니다.
    const networkErrorMessage = 'Network request failed. Please check if the backend server is running.';
    toast.error(networkErrorMessage, {
      id: 'network-error',
    });
    console.error(`API Request Failed: ${method} ${url}`, error);

    // status=0으로 네트워크 오류를 명시
    throw new ApiError(networkErrorMessage, 0);
  }
```

**Step 4: Run to verify**
- 브라우저에서 토큰 생성 시도. Expected: 사용자에게 'Network request failed...' 토스트가 표시되고 콘솔에는 `API Request Failed: POST http://...` 로그가 찍히며, 호출부(TokenManager)에서 catch 후 적절히 처리 가능.

**Step 5: Commit**

```bash
git add apps/client/src/lib/api.ts
git commit -m "fix(client): apiFetch propagate network errors as ApiError(status=0) and show consistent toast

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: TokenManager에서 사용자 피드백 개선(선택적)

**Files:**
- Modify: /Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TokenManager.tsx:54-69

(이 작업은 선택적이지만 권장합니다: 토큰 생성 실패 시 더 친절한 메시지와 유저 재시도 버튼 제공)

**Step 1: Write failing test**
- 수동: 네트워크 실패 상태에서 "토큰 생성" 클릭 → 현재는 콘솔에만 에러가 찍힘.

**Step 2: Implement minimal UX improvement**
- TokenManager.handleCreateToken의 catch 블록에 toast.error(...) 추가.

예시 변경(간단):

```ts
    } catch (error) {
      console.error('Failed to create token', error);
      // 오류가 ApiError(status=0)인지 확인하여 사용자 메시지를 구분
      if ((error as any)?.status === 0) {
        toast.error('네트워크 오류: 백엔드가 실행 중인지 확인해 주세요');
      } else {
        toast.error('토큰 생성에 실패했습니다');
      }
    }
```

**Step 3: Run to verify**
- 브라우저에서 토큰 생성 시 네트워크 실패 일 때 적절한 에러 토스트가 표시되는지 확인.

**Step 4: Commit**

```bash
git add apps/client/src/components/views/TokenManager.tsx
git commit -m "fix(client): show user-friendly toast on token create network errors

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Manual verification checklist

1. npx turbo run dev
2. 서버(백엔드) 일부러 내린 상태에서 토큰 생성 시도 → 브라우저 토스트: 'Network request failed...' 또는 '네트워크 오류: 백엔드가 실행 중인지 확인해 주세요'가 보여야 함
3. 서버 정상 가동 상태에서 토큰 생성 시 성공 토스트와 새 토큰 표시
4. 브라우저 콘솔에 더 이상 원시 TypeError: Failed to fetch가 직접적으로 노출되지 않아야 함(대신 ApiError가 콘솔에 로깅될 수 있음)

---

### Task 6: (옵션) 단위/통합 테스트 추가

프로젝트에 테스팅 인프라(Vitest/Jest)가 이미 없다면 작업이 커집니다. 권장 방법:

- Add a small unit test for fetchWithRetry using Vitest and msw (mock fetch) or node's globalThis.fetch mock.
- 파일: apps/client/src/lib/__tests__/api.fetchWithRetry.test.ts

간단히 수동 검증이 우선이며, 자동화 테스트는 별도 작업으로 계획하는 것을 추천합니다.

---

Plan complete and saved to docs/plans/2026-02-10-token-create-fetch-retry-fix.md. Two execution options:

1. Subagent-Driven (this session) - I dispatch fresh subagent per step and implement changes interactively here. (REQUIRED SUB-SKILL: superpowers:subagent-driven-development)

2. Parallel Session (separate) - Open a new worktree and run superpowers:executing-plans in a separate session to execute the plan with checkpoints.

Which approach do you want?