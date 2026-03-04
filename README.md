# GCS Pulse

[![Build Workflow](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/build.yml/badge.svg?branch=main)](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/build.yml)
[![Server Test Workflow](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/server-test.yml/badge.svg?branch=main)](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/server-test.yml)
[![Client Test Workflow](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/client-test.yml/badge.svg?branch=main)](https://github.com/namjoo-kim-gachon/gcs-pulse/actions/workflows/client-test.yml)
[![License: Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-orange.svg)](./LICENSE)

GCS Pulse는 가천 코코네 스쿨 학습 기록/협업을 위한 웹 서비스 모노레포입니다.

## 저장소 구조

- `apps/client` — Next.js 기반 프론트엔드
  - 상세: [`apps/client/README.md`](./apps/client/README.md)
- `apps/server` — FastAPI 기반 백엔드
  - 상세: [`apps/server/README.md`](./apps/server/README.md)
- `doc` — 운영/감사/설계 문서
  - 성능: [`doc/performance_audit.md`](./doc/performance_audit.md)
  - 보안: [`doc/security_audit.md`](./doc/security_audit.md)
  - 데이터베이스: [`doc/database.md`](./doc/database.md)
  - 디자인 시스템: [`doc/design-system.md`](./doc/design-system.md)
  - 업적 안내: [`doc/achievements.md`](./doc/achievements.md)
- `docs` — 사용자 가이드 문서
  - MCP 사용자 매뉴얼: [`docs/mcp-user-manual.md`](./docs/mcp-user-manual.md)

## 보안 경계 요약

- 인증 경계:
  - Client: 세션 쿠키/CSRF 토큰 전송, Bearer 토큰 보관·전달
  - Server: 인증/인가 검증, rate limit, 권한 메타 동기화 수행
  - DB: 애플리케이션 계층 경유 접근(직접 접근 제한)
- 이번 보안 강화 반영:
  1) core route rate limit 적용 대상 업데이트(`tokens`/`teams`/`users PATCH`/`mcp`)
  2) `/auth/logout` special rule 메서드 정합성(`GET → POST`)
  3) `route_permissions`/`role_assignment_rules`는 메타 정합성 중심 관리

운영 체크리스트 진입점:

- 보안 감사: [`doc/security_audit.md`](./doc/security_audit.md)
- DB 운영 기준: [`doc/database.md`](./doc/database.md)
- 성능 감사: [`doc/performance_audit.md`](./doc/performance_audit.md)
- 서버 운영 문서: [`apps/server/README.md`](./apps/server/README.md)
- MCP 사용자 매뉴얼: [`docs/mcp-user-manual.md`](./docs/mcp-user-manual.md)

## Prerequisites

- Node.js 20+
- npm 10+ (레포 `packageManager`: `npm@10.2.4`)
- Python 3.11+ (최소 3.10, 로컬/CI 기준 3.11 권장)

## Quick Start

### 1) 의존성 설치 (루트)

```bash
npm ci
```

### 2) 서버 환경 준비

```bash
cd apps/server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3) DB 마이그레이션/시드

```bash
cd apps/server
PYTHONPATH=. python scripts/migrate_and_seed.py
```

### 4) 개발 서버 실행

루트에서 클라이언트/서버 동시 실행:

```bash
npm run dev
```

개별 실행이 필요하면:

```bash
# server
cd apps/server
PYTHONPATH=. python -m uvicorn app.main:app --reload

# client (새 터미널)
npm --workspace apps/client run dev
```

## MCP 빠른 안내 (HTTP)

GCS Pulse MCP는 streamable HTTP 엔드포인트를 사용합니다.

- 서버 주소: `https://api.1000.school/mcp`
- 인증: `Authorization: Bearer <API_TOKEN>`
- 권장 클라이언트: Claude Code, Cursor, VS Code, Claude Desktop
- 제공 capability:
  - Tools: `daily_snippets_page_data`, `daily_snippets_get`, `daily_snippets_list`, `daily_snippets_create`, `daily_snippets_organize`, `daily_snippets_feedback`, `daily_snippets_update`, `daily_snippets_delete`, `weekly_snippets_page_data`, `weekly_snippets_get`, `weekly_snippets_list`, `weekly_snippets_create`, `weekly_snippets_organize`, `weekly_snippets_feedback`, `weekly_snippets_update`, `weekly_snippets_delete`
  - Resources: `gcs://me/profile`, `gcs://me/achievements`

클라이언트별 상세 설정(설정 파일 경로, JSON 예시, 문제 해결)은
[`docs/mcp-user-manual.md`](./docs/mcp-user-manual.md)에서 확인하세요.

## 주요 명령어

| 범위 | 명령어 | 설명 |
| :--- | :--- | :--- |
| 루트 | `npm run dev` | Turborepo로 앱 개발 모드 실행 |
| 루트 | `npm run build` | 워크스페이스 빌드 |
| 루트 | `npm run lint` | 워크스페이스 lint |
| server | `PYTHONPATH=. python scripts/migrate_and_seed.py` | DB 스키마/권한 시드 동기화 |
| server | `ENVIRONMENT=test TEST_DATABASE_URL=sqlite+aiosqlite:///./test_ci.db pytest` | 서버 테스트 |
| client | `npm --workspace apps/client run build` | 클라이언트 프로덕션 빌드 |
| client | `npm --workspace apps/client run test:e2e:high` | High 우선 E2E 테스트 |

## 일일 업적 배치 실행 (Cron + CLI)

```bash
# 평가만 수행 (DB 반영 없음)
python3 apps/server/scripts/run_daily_achievement_grants.py --dry-run

# 기본 대상일(비즈니스 기준 전일)로 실제 반영
python3 apps/server/scripts/run_daily_achievement_grants.py
```

Ubuntu cron 예시:

```cron
CRON_TZ=Asia/Seoul
5 0 * * * /opt/gcs-pulse/apps/server/venv/bin/python /opt/gcs-pulse/apps/server/scripts/run_daily_achievement_grants.py >> /var/log/gcs/daily_achievement_grants.log 2>&1
```

배치 상세 옵션은 [`apps/server/README.md`](./apps/server/README.md)를 참고하세요.
