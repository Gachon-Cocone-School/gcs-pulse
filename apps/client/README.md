# GCS Pulse Client

GCS Pulse의 Next.js(App Router) 프론트엔드 애플리케이션입니다.

- 스니펫 작성/조회(일간/주간)
- 업적/리더보드 조회
- 팀/개인 설정, API 토큰 관리
- Playwright E2E 테스트

상위 개요는 루트 문서([`README.md`](../../README.md))를 참고하세요.

## Prerequisites

- Node.js 20+
- npm 10+

## 환경 변수

주요 변수:

- `NEXT_PUBLIC_API_URL` (기본값: `https://api-dev.1000.school`)
- `NEXT_PUBLIC_E2E_TEST=true` (E2E 실행 시)
- `E2E_BASE_URL`, `E2E_API_URL` (Playwright 실행 시 선택)

## Quick Start

```bash
cd apps/client
npm ci
npm run dev
```

기본 로컬 주소: `http://127.0.0.1:3000`

## 주요 명령어

| 명령어 | 설명 |
| :--- | :--- |
| `npm run dev` | 개발 서버 실행 |
| `npm run build` | 프로덕션 빌드 |
| `npm run start -- --hostname 127.0.0.1 --port 3000` | 빌드 결과 실행 |
| `npm run lint` | ESLint 실행 |
| `npm run test:e2e:high` | High 태그 E2E 실행 |
| `npm run test:e2e` | 전체 E2E 실행 |

## E2E 테스트 워크플로

```bash
# 예시: backend(local) + frontend(local) 기동 후
cd apps/client
NEXT_PUBLIC_E2E_TEST=true npm run test:e2e:high
```

- Playwright 설정: [`playwright.config.ts`](./playwright.config.ts)
- 테스트 위치: [`tests/e2e`](./tests/e2e)

## 디렉터리 구조

```text
apps/client
├── src/
│   ├── app/                 # App Router 페이지
│   ├── components/          # UI/뷰 컴포넌트
│   ├── context/             # 인증 컨텍스트
│   ├── guidelines/          # 내부 가이드 소스
│   └── lib/                 # API/유틸리티
├── tests/e2e/               # Playwright E2E 스펙
├── playwright.config.ts
└── next.config.mjs
```

## 디자인/보안 관련 설정

- 보안 헤더(CSP 포함): [`next.config.mjs`](./next.config.mjs)
- 전역 레이아웃/스크립트 로딩: [`src/app/layout.tsx`](./src/app/layout.tsx)
- 디자인 시스템 문서: [`../../doc/design-system.md`](../../doc/design-system.md)

## 관련 문서

- 루트 개요: [`../../README.md`](../../README.md)
- QA 리포트 산출물 경로: `apps/client/docs/qa-artifacts/<date>/`
