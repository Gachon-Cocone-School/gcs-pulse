# Client Design System (Theme-first)

- 대상: `apps/client`
- 목적: UI 일관성 + 테마 확장성 유지

관련 문서:
- 테마 추가 절차: [`./theme-system.md`](./theme-system.md)
- 클라이언트 실행: [`../apps/client/README.md`](../apps/client/README.md)

---

## 0. 현재 운영 테마

- `gcs`
- `retro`
- `matcha-cream`
- `strawberry-choco`

---

## 1. 토큰 계층

`apps/client/src/app/globals.css` 기준

### 1) Palette token
- `--color-primary-*`, `--color-accent-*` 등 색상 스케일

### 2) Semantic token
- `--color-background`, `--color-foreground`
- `--color-card`, `--color-card-foreground`
- `--color-primary`, `--color-primary-foreground`
- `--color-secondary`, `--color-secondary-foreground`
- `--color-muted`, `--color-muted-foreground`
- `--color-accent`, `--color-accent-foreground`
- `--color-destructive`, `--color-destructive-foreground`
- `--color-border`, `--color-input`, `--color-input-background`, `--color-ring`

### 3) Theme expression token
- 폰트/라운드/그림자/로고/타이틀 등 브랜드 표현 토큰

### 4) System state token
- 선택/현재/CTA/focus/spinner/progress 등 상태 토큰 (`--sys-*`)

---

## 2. 컴포넌트 사용 규약

기준 경로: `apps/client/src/components/ui/*`

원칙:
1. 새 화면은 `ui/*` primitive 우선 사용
2. 상태 스타일(hover/active/focus/disabled)은 primitive 내부 규약 우선
3. 페이지에서 직접 커스텀할 때도 semantic/system token만 사용

대표 컴포넌트:
- `button.tsx`
- `tabs.tsx`
- `input.tsx`
- `textarea.tsx`
- `card.tsx`
- `dialog.tsx`
- `progress.tsx`

---

## 3. 상태 시각화 기준

필수로 구분되어야 하는 상태:
- **Primary CTA**
- **현재 위치(Current)** (예: 메뉴/내비게이션)
- **선택(Selected)** (예: 옵션 카드/탭)
- **Focus visible**
- **로딩(Spinner)**
- **진행률(Progress)**

모두 토큰 기반으로 처리:
- `--sys-cta-primary-*`
- `--sys-current-*`
- `--sys-selected-*`
- `--sys-focus-visible`
- `--sys-spinner-*`
- `--sys-progress-*`

---

## 4. 금지 규칙

- 컴포넌트/페이지에서 하드코딩 색상 남발 금지 (`text-white`, `bg-slate-*` 등)
- 동일 역할 컴포넌트에 상태 표현 방식 혼재 금지
- 테마 key를 문자열로 임의 분기 금지 (`APP_THEMES` 기준)

---

## 5. 신규 UI 체크리스트

- [ ] semantic token만으로 기본 색상 구성
- [ ] 선택/현재/CTA/focus 상태 구분 명확
- [ ] spinner/progress 테마 반영 확인
- [ ] `ui/*` primitive 재사용 여부 점검
- [ ] 접근성 속성(`aria-*`, `focus-visible`) 점검
- [ ] `npm --prefix apps/client run lint` 통과
