# 팀 피드 UX 수정 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 팀 피드에서 항상 1컬럼으로 표시하고, 팀 피드에는 "Organized Content"/AI 분석을 기본으로 숨기되(혹은 토글로 확인 가능), 그리고 현재 사용자의 스니펫은 팀 피드에 보이지 않도록 정확히 필터링하여 버그를 수정한다.

**Architecture:** 프론트엔드(Next.js)에서 TeamSnippetFeed와 TeamSnippetCard를 수정한다. 문제의 원인은(1) TeamSnippetCard에서 상세 섹션(organized/AI analysis)을 렌더링하지 않음, (2) 현재 사용자의 식별자 비교 로직이 불완전하여 본인 글이 필터링되지 않음이다. 해결책은 상세 섹션을 isExpanded 토글로 복원하고, 사용자 비교를 더 튼튼하게 하여 여러 id 필드를 비교하도록 한다.

**Tech Stack:** Next.js 16 (App Router), React 18, TypeScript, Tailwind CSS

---

### Task 1: 재현 및 진단 (로컬)

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetFeed.tsx`

**Step 1: 재현 시나리오 문서화(수동 테스트)**
```text
1. npx turbo run dev 로 dev 서버 실행
2. 브라우저에서 daily-snippets 또는 weekly-snippets 페이지 열기
3. 팀 탭 선택
4. 본인 계정으로 로그인된 상태에서 본인 글이 보이는지 확인
5. 카드의 상세 보기(상세 보기 버튼)를 눌러도 AI 분석(점수/리포트)이 보이지 않는지 확인
```

**Step 2: 디버깅 로그 추가 (임시)**
- 변경: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetFeed.tsx`
- 목적: API 응답의 snippet.user 필드 형태와 클라이언트 auth user 형태를 비교

추가할 코드 (fetchTeamSnippets 내부 try 블록에서 res를 받은 직후):
```ts
console.log('[DEBUG] team snippets count', res.items?.length);
console.log('[DEBUG] first snippet user shape', res.items?.[0]?.user);
console.log('[DEBUG] auth user', user);
```

**Step 3: 실행해서 로그 확인**
Run: npx turbo run dev
Expected: 콘솔(브라우저 devtools 또는 터미널)에 snippet.user의 구조(예: { id, google_sub, name, picture } 혹은 { sub, name, picture })와 auth user 구조가 출력되어야 함.

**Step 4: Commit (임시 로그 추가)**
```bash
git add apps/client/src/components/views/TeamSnippetFeed.tsx
git commit -m "chore(debug): log team snippet and auth user shapes for diagnosing team feed filtering"
```

---

### Task 2: 상세(Organized Content / AI Analysis) 섹션 복원

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetCard.tsx:63-77` (CardContent 영역 아래)

**Step 1: Write the failing test (manual / functional)**
```text
1. 현재 코드에서 카드의 상세 보기 버튼 클릭 시(상세 보기 토글) organized/AI analysis가 보이지 않는 것을 재현.
2. 이 상황이 실패 조건(failing test)의 증거가 됨.
```

**Step 2: Run to verify it fails**
Run: 브라우저에서 팀 피드 카드의 상세 보기 버튼 클릭
Expected: 현재는 상세 내용(Organized Content, AI Analysis)이 보이지 않음 — 이것이 ‘FAIL’ 상황(우리가 수정해야 하는 증상).

**Step 3: Minimal implementation**
- 복원할 JSX (CardContent 안에 isExpanded 조건부 렌더링 추가). 예시:
```tsx
{isExpanded && (
  <div className="mt-6 pt-6 border-t border-slate-100 space-y-6">
    {snippet.structured && (
      <div className="space-y-2">
        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">Organized Content</h4>
        <div className="text-slate-800 text-sm bg-slate-50 p-4 rounded-lg border border-slate-100 whitespace-pre-wrap">
          {snippet.structured}
        </div>
      </div>
    )}

    <div className="space-y-2">
      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Analysis</h4>
      <SnippetAnalysisReport feedback={feedback} />
    </div>
  </div>
)}
```
- 위치: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetCard.tsx`의 CardContent 직후.

**Step 4: Run to verify it passes**
Run: dev server, 브라우저에서 팀 피드의 카드 상세 보기 클릭
Expected: 상세 보기 클릭 시 Organized Content(있으면)와 AI Analysis(리포트)가 보임.

**Step 5: Commit**
```bash
git add apps/client/src/components/views/TeamSnippetCard.tsx
git commit -m "fix(client): restore organized content and AI analysis rendering when card expanded"
```

---

### Task 3: 본인 스니펫 필터링 로직 강화

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetFeed.tsx`

**Step 1: Write a failing check (manual)**
```text
1. 현재 코드에서 본인 스니펫이 보이는 상태를 재현(예: 로그에서 확인 또는 UI에서 확인).
2. 이 상태가 실패 조건.
```

**Step 2: Implement robust comparison helper**
- 추가할 헬퍼 함수 (TeamSnippetFeed 파일 상단 또는 파일 내부):
```ts
function isSameUser(snippetUser: any, authUser: any) {
  if (!authUser || !snippetUser) return false;
  // Compare by multiple possible identifier fields
  const authIds = new Set([authUser.sub, authUser.google_sub, authUser.id, authUser?.email]);
  const snippetIds = [snippetUser.sub, snippetUser.google_sub, snippetUser.id, snippetUser?.email];
  return snippetIds.some((id) => id && authIds.has(id));
}
```
- 필터에 적용:
```ts
const visibleSnippets = snippets.filter((s) => !isSameUser(s.user, user));
```

**Step 3: Run to verify**
Run dev server, 로그인된 계정으로 팀 탭 열기
Expected: 본인 스니펫이 더 이상 팀 피드에 보이지 않음.

**Step 4: Commit**
```bash
git add apps/client/src/components/views/TeamSnippetFeed.tsx
git commit -m "fix(client): robustly filter out current user's snippets in team feed by comparing multiple id fields"
```

---

### Task 4: API/데이터 불일치 확인 및 보정

**Files to inspect (read-only diagnostics):**
- `/Users/hexa/projects/temp/gcs-mono/apps/server/app/models.py`
- `/Users/hexa/projects/temp/gcs-mono/apps/server/app/routers/daily_snippets.py`

**Step 1: Confirm API가 반환하는 snippet.user의 식별자 필드 이름 확인**
- 목표: snippet.user가 { id, google_sub, name, ... } 형태인지, 또는 { sub, name } 형태인지 확인
- 방법: 이미 Task 1에서 로그로 확인하거나, server 쪽의 CRUD/serializers를 확인

**Step 2: 필요 시 프론트에서 지원하도록 추가 보정**
- 만약 API가 google_sub를 사용한다면 isSameUser에서 google_sub 비교를 반드시 포함해야 함(위 헬퍼에 반영됨).

**Step 3: Commit (서버 변경 필요 시)**
- 서버에서 반환 형식을 변경할 경우 별도 계획 필요. 우선 프론트에서 방어적으로 비교하도록 함.

---

### Task 5: 수동/QA 확인 항목

**Files to check visually:**
- `/Users/hexa/projects/temp/gcs-mono/apps/client/src/app/daily-snippets/page.tsx`
- `/Users/hexa/projects/temp/gcs-mono/apps/client/src/app/weekly-snippets/page.tsx`

**Checklist (수동 테스트)**
- [ ] 로그인된 계정으로 접속한 상태에서 팀 탭을 열면 본인 스니펫이 보이지 않는다.
- [ ] 팀 피드 카드에서 '상세 보기' 버튼을 누르면 Organized Content(정리된 콘텐츠)와 AI Analysis(점수/리포트)가 보인다.
- [ ] 마크다운 본문은 프로시 스타일로 안전하게 렌더링된다.
- [ ] 모바일/데스크톱에서 1컬럼으로 보인다.

---

### Task 6: 커밋/PR 준비

**Commit 메시지 가이드** (각 단계별로 커밋 권장)
- chore(debug): log team snippet and auth user shapes for diagnosing team feed filtering
- fix(client): restore organized content and AI analysis rendering when card expanded
- fix(client): robustly filter out current user's snippets in team feed by comparing multiple id fields

**PR 바디(예시)**
```
## Summary
- 팀 피드에서 항상 1컬럼으로 고정
- 팀 피드에서 본인 스니펫을 숨기도록 필터링 강화
- 팀 피드 카드의 상세 보기에서 Organized Content 및 AI Analysis 복원

## Test plan
- 수동 체크리스트(위 참조)

🤖 Generated with [Claude Code]
```

---

Plan 작성 완료: `docs/plans/2026-02-10-team-feed-ux-fix.md`

두 가지 실행 옵션:

1. Subagent-Driven (이 세션에서 바로 구현 진행) - 각 Task를 순차적으로 수행하고, 변경마다 검토 및 커밋합니다. REQUIRED SUB-SKILL: superpowers:subagent-driven-development

2. Parallel Session (별도 세션에서 일괄 실행) - 계획을 저장하고 별도 세션/워크트리에 작업을 맡깁니다. REQUIRED SUB-SKILL: superpowers:executing-plans

어떤 실행 방식을 원하시나요? (1 또는 2 중 선택해주세요)
