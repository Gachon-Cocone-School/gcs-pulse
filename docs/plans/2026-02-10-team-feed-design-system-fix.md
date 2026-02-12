# Team Feed Design System 적용 문제 수정 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 팀 피드(TeamSnippetFeed / TeamSnippetCard) 화면에 프로젝트의 design-system(프로즈 스타일, 토큰, 컴포넌트 규칙)이 정확히 적용되도록 수정한다. 구체적으로는 팀 피드의 마크다운 본문과 카드 스타일이 design-system.md에 정의된 'prose' 스타일과 디자인 토큰을 사용하도록 통일하고, 전역 스타일(globals.css / tailwind 설정)에 누락된 항목이 있으면 보완한다.

**Architecture:** 프론트엔드(Next.js) 코드와 스타일(config)을 점검하고, 팀 피드 컴포넌트들이 공용 마크다운/프로즈 렌더러(SnippetPreview)와 디자인 토큰을 사용하도록 변경한다. 또한 필요 시 apps/client/src/styles/globals.css 및 Tailwind 설정을 확인/수정한다.

**Tech Stack:** Next.js 16, React 18, Tailwind CSS, ReactMarkdown (remark-gfm, rehype-sanitize)

---

### Task 1: 디자인 시스템 문서/스타일 존재 여부 확인

**Files:**
- Read: `/Users/hexa/projects/temp/gcs-lms/apps/client/docs/design-system.md` (문서가 없으면 생성 권장)
- Read: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/styles/globals.css`
- Read: `/Users/hexa/projects/temp/gcs-lms/tailwind.config.js` (또는 앱 내부 설정 파일)

**Step 1: 파일을 읽어서 design-system 토큰(예: .prose, 색상 변수, utility 클래스)이 정의되어 있는지 확인**
Run: (로컬에서)
```
# 루트에서
ls -la apps/client/docs || true
sed -n '1,240p' apps/client/src/styles/globals.css
sed -n '1,240p' tailwind.config.js
```
Expected: globals.css에 .prose 관련 오버라이드와 design tokens(예: --color-primary) 또는 tailwind.config.js의 theme.extend.prose 설정이 보인다.

**Step 2: Commit (읽기/진단은 커밋 불필요)**

---

### Task 2: 팀 피드가 공용 마크다운 렌더러(SnippetPreview)를 사용하도록 변경

**Files:**
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/TeamSnippetCard.tsx:66-76`
- Test: N/A (manual/visual)

**Step 1: Write the failing test (manual)**
```
1. 현재 팀 피드 카드에서는 마크다운이 design-system의 prose 스타일을 따르지 않음(글꼴/여백/코드블록 스타일 불일치).
2. 이 증상이 재현됨을 확인한다.
```

**Step 2: Run to verify it fails**
Run: dev 서버에서 팀 탭 열기, 마크다운 포함된 스니펫 확인
Expected: 현재 스타일이 design-system과 다름(증거 스크린샷 또는 DOM 검사)

**Step 3: Minimal implementation**
- Replace inline ReactMarkdown usage in TeamSnippetCard with the existing SnippetPreview component which already applies prose styles.

Exact edit (replace the markdown rendering block in TeamSnippetCard):
```tsx
// Replace current ReactMarkdown block with:
import SnippetPreview from '@/components/views/SnippetPreview';

// inside CardContent
<SnippetPreview content={snippet.content} />
```
- File: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/TeamSnippetCard.tsx`

**Step 4: Run to verify it passes**
Run: `npx turbo run dev` then open 팀 탭 → 카드의 본문이 design-system(prose) 스타일을 따르는지 확인.
Expected: 마크다운 본문이 apps/client/src/components/views/SnippetPreview.tsx의 prose 스타일로 렌더링됨.

**Step 5: Commit**
```
git add apps/client/src/components/views/TeamSnippetCard.tsx
git commit -m "fix(client): make team feed cards use SnippetPreview (prose design)"
```

---

### Task 3: SnippetPreview / prose 스타일 확인 및 보완

**Files:**
- Read/Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/SnippetPreview.tsx`
- Modify: `/Users/hexa/projects/temp/gcs-lms/apps/client/src/styles/globals.css` (if needed)

**Step 1: Check SnippetPreview currently applies prose and rehype-sanitize**
- Read file; expected it to contain:
```tsx
<div className="prose max-w-none dark:prose-invert p-0 m-0">
  <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeSanitize]}>...</ReactMarkdown>
</div>
```
If missing, modify SnippetPreview to match above.

**Step 2: Ensure globals.css contains prose overrides from design system**
- If design tokens are defined in apps/client/docs/design-system.md, ensure global CSS maps tokens to .prose styles (e.g., headings, code blocks, blockquote styles).
- If missing, add minimal overrides to globals.css (examples provided below).

Minimal globals.css additions (append if missing):
```css
/* design system prose tweaks */
.prose {
  --tw-prose-body: themeColor(var(--color-text));
  max-width: none;
}
.prose pre { background-color: var(--color-code-bg); padding: 1rem; border-radius: .5rem; }
```
(Use existing design tokens if available in project.)

**Step 3: Commit**
```
git add apps/client/src/components/views/SnippetPreview.tsx apps/client/src/styles/globals.css
git commit -m "chore(client): ensure SnippetPreview and globals.css apply design-system prose styles"
```

---

### Task 4: Tailwind / prose plugin 설정 확인

**Files:**
- Read/Modify: `/Users/hexa/projects/temp/gcs-lms/tailwind.config.js` (또는 apps/client/tailwind.config.js if present)

**Step 1: Verify @tailwindcss/typography 플러그인 사용 여부**
Run: open tailwind.config.js and check for:
```js
plugins: [require('@tailwindcss/typography'), ...]
```
If missing, add plugin and run `npm install -D @tailwindcss/typography` in apps/client (or root) as needed.

**Step 2: Commit (if modified)**
```
# if you modified tailwind config
git add tailwind.config.js
git commit -m "chore(client): enable @tailwindcss/typography plugin for prose styles"
```

---

### Task 5: Visual QA & build check

**Files to visually check:**
- `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/daily-snippets/page.tsx`
- `/Users/hexa/projects/temp/gcs-lms/apps/client/src/app/weekly-snippets/page.tsx`
- `/Users/hexa/projects/temp/gcs-lms/apps/client/src/components/views/TeamSnippetCard.tsx`

**Step 1: Run build / lint**
Run:
```
npm --prefix apps/client run build
npx turbo run lint
```
Expected: 빌드 실패가 없어야 하며, CSS 변경이 적용된 상태에서 디자인이 개선되어야 함.

**Step 2: Manual QA checklist**
- [ ] 팀 피드의 본문이 prose 스타일을 따름(헤더, 목록, 코드블록 스타일 확인)
- [ ] 카드 여백/테두리/폰트가 design-system 문서와 일치
- [ ] 모바일에서 1컬럼 레이아웃 유지

**Step 3: Commit any follow-ups**
```
# 예: 스타일 미세조정
git add <files>
git commit -m "fix(client): tweak prose styles for team feed per design system"
```

---

### Task 6: 문서화

**Files:**
- Create/Update: `/Users/hexa/projects/temp/gcs-lms/apps/client/docs/design-system.md`

**Step 1: If document missing or 불완전하면 작성/보완**
- Include color tokens, typography, component examples (Button, Card, Badge) and prose rules for markdown rendering.

**Step 2: Commit**
```
git add apps/client/docs/design-system.md
git commit -m "docs(client): add/update design-system.md (prose and component tokens)"
```

---

Plan complete and saved to `docs/plans/2026-02-10-team-feed-design-system-fix.md`.

실행 옵션:
1) Subagent-Driven (이 세션에서 바로 구현) - 각 Task를 순차적으로 수행하고 검토합니다. REQUIRED: superpowers:subagent-driven-development
2) Parallel Session (별도) - 새 세션에서 일괄 실행합니다. REQUIRED: superpowers:executing-plans

어떤 방식으로 진행할까요? (1 또는 2 중 선택해주세요)