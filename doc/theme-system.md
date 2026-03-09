# Theme System Guide (Client)

- 대상: `apps/client`
- 목적: **새 테마를 빠르고 안전하게 추가**하기 위한 단일 가이드

관련 코드:
- 테마 목록: `apps/client/src/lib/theme.ts`
- Provider: `apps/client/src/app/layout.tsx`
- 토큰: `apps/client/src/app/globals.css`
- 설정 UI: `apps/client/src/components/views/ThemeSettings.tsx`

---

## 1. 현재 테마 구조

현재 지원 테마:
- `gcs`
- `retro`
- `matcha-cream`
- `strawberry-choco`

핵심 원칙:
1. **테마 키 단일 소스**: `APP_THEMES` (`src/lib/theme.ts`)
2. **런타임 적용 지점 단일화**: `ThemeProvider` (`layout.tsx`)
3. **스타일은 semantic/system token으로만 적용**: `globals.css`

---

## 2. 새 테마 추가 절차 (반복 템플릿)

예시 테마 키: `strawberry-choco`

### Step 1) 테마 목록 추가
파일: `apps/client/src/lib/theme.ts`

- `APP_THEMES`에 항목 추가
  - `value: "strawberry-choco"`
  - `label`, `description`

### Step 2) ThemeProvider 자동 반영 확인
파일: `apps/client/src/app/layout.tsx`

- 현재 구조는 `themes={APP_THEME_VALUES as string[]}`이므로, `APP_THEMES` 추가 시 자동 반영됩니다.

### Step 3) 토큰 블록 추가
파일: `apps/client/src/app/globals.css`

```css
[data-theme="strawberry-choco"] {
  /* semantic color */
  --color-background: ...;
  --color-foreground: ...;
  --color-card: ...;
  --color-card-foreground: ...;
  --color-primary: ...;
  --color-primary-foreground: ...;
  --color-secondary: ...;
  --color-secondary-foreground: ...;
  --color-muted: ...;
  --color-muted-foreground: ...;
  --color-accent: ...;
  --color-accent-foreground: ...;
  --color-destructive: ...;
  --color-destructive-foreground: ...;
  --color-border: ...;
  --color-input: ...;
  --color-input-background: ...;
  --color-ring: ...;

  /* theme expression */
  --theme-font-family-body: ...;
  --theme-font-family-heading: ...;
  --theme-font-weight-heading: ...;
  --theme-card-radius: ...;
  --theme-control-radius: ...;
  --theme-card-shadow: ...;
  --theme-control-shadow: ...;
  --theme-control-hover-shadow: ...;
  --theme-button-font-weight: ...;
  --theme-button-letter-spacing: ...;
  --theme-logo-filter: ...;
  --theme-page-title-color: ...;
  --theme-hero-title-gradient: ...;
  --theme-hero-title-shadow: ...;

  /* system state */
  --sys-selected-bg: ...;
  --sys-selected-fg: ...;
  --sys-selected-border: ...;
  --sys-current-bg: ...;
  --sys-current-fg: ...;
  --sys-current-border: ...;
  --sys-cta-primary-bg: ...;
  --sys-cta-primary-fg: ...;
  --sys-cta-primary-border: ...;
  --sys-cta-primary-hover: ...;
  --sys-cta-primary-active: ...;
  --sys-focus-visible: ...;
  --sys-spinner-track: ...;
  --sys-spinner-indicator: ...;
  --sys-progress-track: ...;
  --sys-progress-indicator: ...;
}
```

### Step 4) 설정 화면 노출 확인
`ThemeSettings.tsx`는 `APP_THEMES` 기반 렌더링이므로 자동 노출됨.

### Step 5) 회귀 검증
- 수동
  - `/settings?menu=theme`에서 테마 클릭 즉시 반영
  - 새로고침 후 유지
  - 홈(버튼/탭/스피너), 설정, 스니펫, 검색 화면 확인
- 자동
  - `npm --prefix apps/client run lint`

---

## 3. 구현 규칙

1. 컴포넌트에서 색상 하드코딩 금지 (`text-foreground`, `bg-background`, `border-border` 우선)
2. 버튼/탭 선택 상태는 `--sys-*` 토큰 사용
3. 로딩 인디케이터는 `--sys-spinner-*` 토큰 사용
4. 진행률 UI는 `--sys-progress-*` 토큰 사용
5. 테마별 차별화는 최소 3축 유지
   - 폰트
   - 텍스트 컬러 계열
   - CTA/선택/로딩 시각 요소

---

## 4. 빠른 체크리스트

- [ ] `APP_THEMES`에 키 추가
- [ ] `APP_THEMES` 추가 후 `ThemeProvider themes={APP_THEME_VALUES}` 자동 반영 확인
- [ ] `globals.css`에 `[data-theme="..."]` 블록 추가
- [ ] 홈 버튼/탭/스피너에서 테마 반영 확인
- [ ] `/settings?menu=theme` 적용/유지 확인
- [ ] `npm --prefix apps/client run lint` 통과
