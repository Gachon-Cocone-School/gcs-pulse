# Card Content Spacing Fix Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

I'm using the writing-plans skill to create the implementation plan.

**Goal:** 팀 피드 및 회고 카드에서 "AI Analysis" 블록에 적절한 여백(padding/margin)이 적용되도록, 해당 블록을 CardContent 내부에 넣어 design-system의 카드 레이아웃 규칙을 따르도록 수정합니다.

**Architecture:** 프론트엔드 컴포넌트(React) 수정. TeamSnippetCard에서 expanded 상태의 AI Analysis 블록이 CardContent로 감싸지지 않아 여백이 없으므로, 해당 블록을 CardContent로 감싸거나 CardContent의 슬롯을 재사용하도록 변경합니다. 필요 시 components/ui/card.tsx의 CardContent 구현을 확인/보완합니다.

**Tech Stack:** Next.js 16 (App Router), React 18, TypeScript, Tailwind CSS

---

### Task 1: 현황 확인 (읽기)

**Files:**
- Read: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/ui/card.tsx`
- Read: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetCard.tsx`
- Read: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/app/daily-snippets/page.tsx`

**Step 1: Read files to confirm where AI Analysis JSX is rendered and CardContent implementation**
- 명령(로컬):
  - sed -n '1,240p' /Users/hexa/projects/temp/gcs-mono/apps/client/src/components/ui/card.tsx
  - sed -n '1,240p' /Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetCard.tsx
  - sed -n '1,240p' /Users/hexa/projects/temp/gcs-mono/apps/client/src/app/daily-snippets/page.tsx

Expected: TeamSnippetCard의 isExpanded 블록에 AI Analysis JSX가 있고, 현재 그 블록이 CardContent 밖(또는 CardContent 안이지만 스타일 누락)인지 확인됩니다.

**Step 2: Commit**
- 진단 단계는 커밋 필요 없음.

---

### Task 2: TeamSnippetCard — AI Analysis를 CardContent로 감싸기

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/views/TeamSnippetCard.tsx`

**Step 1: Write the failing test (manual / visual)**
- 브라우저에서 팀 피드 또는 daily snippets 페이지 열기
- 카드에서 '상세 보기'를 눌렀을 때 AI Analysis 블록과 상단/좌우 여백이 전혀 없는 것을 확인(현재 상태가 실패)

**Step 2: Run to verify it fails**
- 동작 재현: dev 서버에서 페이지 열어 시각 확인. 실패가 재현되는 것을 확인.

**Step 3: Minimal implementation**
- 변경 내용(정확한 코드 조각): TeamSnippetCard에서 현재 isExpanded 블록의 AI Analysis 부분을 CardContent 컴포넌트로 감쌉니다. 예시 패치(부분 교체):

기존(요약):

{isExpanded && (
  <div className="mt-6 pt-6 border-t border-slate-100 space-y-6">
    <div className="space-y-2">
      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Analysis</h4>
      <SnippetAnalysisReport feedback={feedback} />
    </div>
  </div>
)}

변경 후(정확히 적용할 코드):

<CardContent className="p-4 pt-6">
  <div className="space-y-2">
    <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider">AI Analysis</h4>
    <SnippetAnalysisReport feedback={feedback} />
  </div>
</CardContent>

- 설명: 기존의 경계(div.mt-6... 등은 유지하되, 내부 AI Analysis 블록을 CardContent로 감싸서 카드의 콘텐츠 슬롯 규칙(prose/padding 등)을 따르게 합니다. 구체적으로는 CardContent 안에 pt-6(위쪽 패딩)과 p-4(좌우 패딩)을 주어 적절한 여백을 적용합니다.

**Step 4: Run to verify it passes**
- dev 서버에서 페이지를 새로고침하고, 카드의 '상세 보기'를 눌러 AI Analysis 블록이 CardContent의 padding을 따라 여백이 생겼는지 확인.
- Expected: AI Analysis의 좌우/상단 여백이 정상적으로 적용되어 읽기 쉬워짐.

**Step 5: Commit**
- 변경 파일 추가 및 커밋:

```bash
git add apps/client/src/components/views/TeamSnippetCard.tsx
git commit -m "fix(client): wrap expanded AI Analysis in CardContent for proper spacing"
```

커밋 메시지 끝에 Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com> 추가 권장(팀 정책).

---

### Task 3: CardContent 구현 확인/보완 (옵션)

**Files:**
- Modify (if needed): `/Users/hexa/projects/temp/gcs-mono/apps/client/src/components/ui/card.tsx`

**Step 1: Read CardContent implementation**
- 확인할 내용: CardContent가 children을 래핑할 때 기본 padding/padding-top, 마지막 자식에 대한 [&:last-child] 규칙 등이 적절히 설정되어 있는지 확인.

**Step 2: If missing, add minimal padding defaults**
- 예시 변경(append to CardContent className):
  - 기본: className="p-4"
  - 또는 style override로 `.card-content { padding: 1rem; }`

**Step 3: Commit (only if you changed card.tsx)**
- 메시지:

```bash
git add apps/client/src/components/ui/card.tsx
git commit -m "fix(client): ensure CardContent provides default padding for card slots"
```

---

### Task 4: Build & lint 확인

**Step 1: Build client**
- Run: `npm --prefix apps/client run build`
- Expected: 빌드 성공

**Step 2: Lint**
- Run: `npx turbo run lint`
- Note: monorepo lint may require server Python lint dependencies; if lint fails due to server flake8 missing, report and do not modify server lint scripts.

**Step 3: Commit any follow-up fixes if required**
- Commit messages should be precise and minimal.

---

### Task 5: QA 및 문서화

**Manual checks:**
- [ ] 팀 피드 및 daily-snippets 페이지에서 카드의 '상세 보기'를 눌러 AI Analysis 주변 여백이 적절한지 확인
- [ ] 모바일/데스크탑에서 레이아웃 깨짐 없음
- [ ] CardContent의 스타일이 다른 카드 구성에도 영향을 주지 않는지 빠르게 확인(특히 다른 뷰에서 CardContent가 쓰이는 곳)

**If everything OK:**
- Commit 메시지 예시(마무리):
  - docs: note change in design-system section about card content usage

---

Plan saved to `docs/plans/2026-02-10-card-content-spacing-fix.md`.

Execution options:
1) Subagent-Driven (this session) — I will implement these tasks now, with per-task commits and two-stage reviews.
2) Parallel Session (separate) — open a new session to execute the plan.

어떤 방식으로 진행할까요? (1 또는 2 선택해주세요)