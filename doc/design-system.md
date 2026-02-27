# Client Design System

이 문서는 현재 코드 기준의 UI 규약을 정리합니다.
(기준 파일: `apps/client/src/app/globals.css`, `apps/client/src/components/ui/*`)

관련 문서: [QA / E2E 테스트 문서화 컨벤션](./qa-testing-convention.md)

## 1) Design Tokens

### Core semantic tokens

아래 토큰을 기본으로 사용합니다.

- `background` / `foreground`
- `card` / `card-foreground`
- `primary` / `primary-foreground`
- `secondary` / `secondary-foreground`
- `muted` / `muted-foreground`
- `accent` / `accent-foreground`
- `destructive` / `destructive-foreground`
- `border` / `input` / `input-background`
- `ring`

실제 정의 위치: `apps/client/src/app/globals.css`

### Palette (base)

- Rose (Primary): `--color-rose-*`
- Violet (Accent): `--color-violet-*`
- Slate (Neutral): `--color-slate-*`
- Coral (Destructive): `--color-coral-*`

Semantic token은 위 팔레트를 참조해서 구성합니다.

## 2) Shape / Elevation / Focus 규약

- 기본 컨트롤 반경: `rounded-md`
  - Button, Input, Textarea, Tabs trigger
- 컨테이너 반경: `rounded-xl`
  - Card, Dialog content
- 보더: `border-border` 사용
- 기본 그림자: `shadow-sm`
- Focus ring: `focus-visible:ring-[3px]` + `focus-visible:ring-ring/50`

## 3) Primitive 상태 규약

### Button (`apps/client/src/components/ui/button.tsx`)

- 상태: hover / focus-visible / disabled / destructive 통일
- variant는 semantic token 기반:
  - `default`, `outline`, `secondary`, `ghost`, `link`, `destructive`
- 현재 구현 특이사항: `togglable` prop 지원 (`aria-pressed` + Chevron up/down 토글)

### Input / Textarea (`apps/client/src/components/ui/input.tsx`, `apps/client/src/components/ui/textarea.tsx`)

- `border-input`, `bg-input-background`, `text-foreground` 사용
- 공통 focus ring 규약 사용
- 에러 상태는 `aria-invalid` + destructive ring/border

### Card (`apps/client/src/components/ui/card.tsx`)

- `bg-card`, `text-card-foreground`, `border-border`, `shadow-sm`
- export:
  - `Card`, `CardHeader`, `CardTitle`, `CardDescription`, `CardContent`, `CardFooter`

### Alert (`apps/client/src/components/ui/alert.tsx`)

- 기본: card 기반 시각 언어
- destructive: `border-destructive/30`, `text-destructive`
- export:
  - `Alert`, `AlertDescription`

### Tabs (`apps/client/src/components/ui/tabs.tsx`)

- Tabs list: `rounded-lg`, `border-border`, `bg-muted`
- Trigger: active 시 `bg-card`, `text-foreground`, `shadow-sm`
- focus ring 규약 일관 적용

### Dialog (`apps/client/src/components/ui/dialog.tsx`)

- Overlay: `bg-slate-900/45` + 약한 blur
- Content: `rounded-xl`, `border-border`, `shadow-sm`
- export:
  - `Dialog`, `DialogTrigger`, `DialogContent`, `DialogHeader`, `DialogFooter`, `DialogTitle`, `DialogDescription`

## 4) Page-level 규약

### Navigation

- 기준 파일: `apps/client/src/components/Navigation.tsx`
- inline style 금지, utility class 기반
- 과도한 z-index 금지
- 현재 레이어 스케일:
  - Nav: `z-40`
  - Dropdown / Dialog: `z-50`
  - 로컬 floating UI: `z-10`

### Login

- `Card` + `Button` 중심으로 구성
- 하드코딩 radius/shadow/hex 최소화
- 배경은 `bg-mesh` 사용 가능 (semantic token 기반)

### SnippetForm

- 기준 파일: `apps/client/src/components/views/SnippetForm.tsx`
- 편집/미리보기 전환은 `Tabs` 사용
- 본문 입력은 `Textarea` 재사용
- 편집 영역/미리보기 영역 보더/반경/간격 일관 유지
- `정리하기` 결과는 즉시 본문 반영이 아니라 Dialog에서 검토 후 `적용하기`로 저장

### PageHeader

- 기준 파일: `apps/client/src/components/PageHeader.tsx`
- 타이틀: `text-foreground`
- 설명: `text-muted-foreground`
- 페이지 액션 버튼은 primitive(Button) 우선

## 5) 구현 체크리스트 (신규 화면 공통)

1. 하드코딩 hex/inline style 대신 semantic token 클래스 사용
2. primitive 우회 마크업 대신 `ui/*` 컴포넌트 우선 사용
3. focus/hover/disabled 상태가 기존 primitive와 동일한지 확인
4. z-index는 기존 스케일(`10/40/50`) 내에서 해결
5. 최종적으로 `npm run lint`, `npm run build` 통과 확인
