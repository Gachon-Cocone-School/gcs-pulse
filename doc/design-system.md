# Client Design System

- 최신 업데이트: 2026-02-27
- 대상 범위: `apps/client`
- 역할: 프론트엔드 UI 규약/컴포넌트 사용 기준 정리

관련 문서:

- 클라이언트 실행/테스트: [`../apps/client/README.md`](../apps/client/README.md)
- 루트 개요: [`../README.md`](../README.md)

## 1) 토큰 기준

기본 토큰은 `apps/client/src/app/globals.css` 기준으로 사용합니다.

### Semantic token

- `background` / `foreground`
- `card` / `card-foreground`
- `primary` / `primary-foreground`
- `secondary` / `secondary-foreground`
- `muted` / `muted-foreground`
- `accent` / `accent-foreground`
- `destructive` / `destructive-foreground`
- `border` / `input` / `input-background`
- `ring`

### Base palette

- Rose: `--color-rose-*`
- Violet: `--color-violet-*`
- Slate: `--color-slate-*`
- Coral: `--color-coral-*`

## 2) 공통 스타일 규약

- 기본 컨트롤 radius: `rounded-md`
- 컨테이너 radius: `rounded-xl`
- 보더: `border-border`
- 기본 그림자: `shadow-sm`
- Focus ring: `focus-visible:ring-[3px]` + `focus-visible:ring-ring/50`

## 3) UI Primitive 사용 규칙

기준 경로: `apps/client/src/components/ui/*`

- Button: `button.tsx`
  - variant: `default`, `outline`, `secondary`, `ghost`, `link`, `destructive`
- Input: `input.tsx`
- Textarea: `textarea.tsx`
- Card: `card.tsx`
- Alert: `alert.tsx`
- Tabs: `tabs.tsx`
- Dialog: `dialog.tsx`

원칙:

1. 새 화면에서 가능하면 `ui/*` 컴포넌트를 우선 사용
2. 하드코딩 색상/inline style 최소화
3. hover/focus/disabled 상태를 primitive 규약과 일치

## 4) 페이지 레벨 규약

- Navigation: `src/components/Navigation.tsx`
- PageHeader: `src/components/PageHeader.tsx`
- SnippetForm: `src/components/views/SnippetForm.tsx`

레이어 기준:

- 로컬 floating UI: `z-10`
- Navigation: `z-40`
- Dropdown/Dialog: `z-50`

## 5) 신규 화면 체크리스트

- [ ] semantic token 기반 클래스 사용
- [ ] `ui/*` primitive 재사용 여부 확인
- [ ] 접근성 상태(`focus-visible`, `aria-*`) 점검
- [ ] 기존 z-index 스케일 내 해결
- [ ] `npm --workspace apps/client run lint`
- [ ] `npm --workspace apps/client run build`

## 6) 문서 운영 원칙

- 이 문서는 **UI 규약 요약본**입니다.
- 구현 상세는 실제 컴포넌트 소스(`apps/client/src/components`)를 기준으로 검증합니다.
- README/운영 문서 변경 시 본 문서의 용어/경로도 함께 동기화합니다.
