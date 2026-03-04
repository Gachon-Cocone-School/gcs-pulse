# GCS Pulse Server

GCS Pulse의 FastAPI 백엔드 애플리케이션입니다.

- 인증: Google OAuth + 세션 기반 인증
- 권한: `get_active_user` 기반 보호 라우트 접근 제어
- 데이터: SQLAlchemy Async + 환경별 DB URL 선택
- 부가 기능: API 토큰, 팀/리그, 스니펫/댓글, 업적, MCP(HTTP)

상위 개요는 루트 문서([`README.md`](../../README.md))를 참고하세요.

## 런타임 / Prerequisites

- Python 3.11+ 권장 (최소 3.10)
- `venv` 사용 권장
- PostgreSQL 또는 SQLite(`aiosqlite`) 지원

## 환경 변수

기본 템플릿: [`apps/server/.env.example`](./.env.example)

핵심 변수:

- `ENVIRONMENT`: `development` | `test` | `production`
- `DEV_DATABASE_URL`, `TEST_DATABASE_URL`, `DATABASE_URL`
- `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `SECRET_KEY`
- `CORS_ORIGINS`, `ALLOWED_HOSTS`
- (선택) Copilot 연동 변수: `GITHUB_*`, `COPILOT_*`

DB 선택 규칙(코드 기준):

- `ENVIRONMENT=production` → `DATABASE_URL`
- `ENVIRONMENT=test` + `TEST_DATABASE_URL` 존재 → `TEST_DATABASE_URL`
- 그 외 → `DEV_DATABASE_URL`

## Quick Start

```bash
cd apps/server
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
PYTHONPATH=. python scripts/migrate_and_seed.py
PYTHONPATH=. python -m uvicorn app.main:app --reload
```

기본 로컬 주소: `http://127.0.0.1:8000`

## 주요 명령어

| 명령어 | 설명 |
| :--- | :--- |
| `PYTHONPATH=. python -m uvicorn app.main:app --reload` | 개발 서버 실행 |
| `PYTHONPATH=. python scripts/migrate_and_seed.py` | 스키마/시드/라우트 권한 동기화 |
| `ENVIRONMENT=test TEST_DATABASE_URL=sqlite+aiosqlite:///./test_ci.db pytest` | 서버 테스트 실행 |
| `python scripts/run_daily_achievement_grants.py --dry-run` | 업적 배치 점검 |
| `python scripts/run_daily_achievement_grants.py --target-date YYYY-MM-DD` | 특정 일자 업적 배치 |

## 보안 경계 / 운영 체크리스트

- 인증 경계:
  - 세션+CSRF: `/auth/*`, `/terms`, `/consents`, `/teams`, `/users`, `/auth/tokens`
  - Bearer: `/mcp`
- Rate limit 핵심 적용 대상(이번 라운드): `tokens`/`teams`/`users PATCH`/`mcp`
- 권한 메타 기준: `route_permissions`/`role_assignment_rules`는 `scripts/migrate_and_seed.py`로 메타 동기화 중심 관리
- `/auth/logout` special rule 메서드 정합성: `POST /auth/logout`

운영 체크리스트:

- [ ] `ENVIRONMENT=production`에서 `SECRET_KEY`가 기본값/공백이 아닌지 확인
- [ ] `CORS_ORIGINS`, `ALLOWED_HOSTS`를 운영 allowlist로 최소화
- [ ] 라우트/권한 변경 시 `PYTHONPATH=. python scripts/migrate_and_seed.py` 실행으로 메타 동기화
- [ ] 신규/변경 라우트의 `@limiter.limit` 적용 여부를 명시적으로 결정

교차 문서:

- 보안 감사: [`../../doc/security_audit.md`](../../doc/security_audit.md)
- DB 운영 기준: [`../../doc/database.md`](../../doc/database.md)
- 성능 감사: [`../../doc/performance_audit.md`](../../doc/performance_audit.md)

## API/기능 개요

주요 라우터(prefix):

- 인증/세션: `/auth/*`, `/terms`, `/consents`
- 토큰: `/auth/tokens`
- 팀/유저: `/teams`, `/users`
- 스니펫: `/daily-snippets`, `/weekly-snippets`, `/comments`
- 리더보드/업적: `/leaderboards`, `/achievements`
- MCP(HTTP): `/mcp` (`GET|POST|DELETE`)

참고: `app/routers/ai.py`는 현재 `app.main`에 include되지 않아 외부 노출되지 않습니다.

## 일일 업적 배치 운영 (Cron + CLI)

수동 실행:

```bash
cd apps/server
# 평가만 수행 (DB 반영 없음)
python scripts/run_daily_achievement_grants.py --dry-run

# 기본 대상일(비즈니스 기준 전일)로 실제 반영
python scripts/run_daily_achievement_grants.py

# 특정 대상일 지정 실행
python scripts/run_daily_achievement_grants.py --target-date 2026-02-24
```

Ubuntu cron 예시:

```cron
CRON_TZ=Asia/Seoul
5 0 * * * /opt/gcs-pulse/apps/server/venv/bin/python /opt/gcs-pulse/apps/server/scripts/run_daily_achievement_grants.py >> /var/log/gcs/daily_achievement_grants.log 2>&1
```

## MCP 연결 가이드 (HTTP)

MCP 사용자용 설정 가이드는 루트 문서로 통합되었습니다.

- 사용자 매뉴얼: [`../../docs/mcp-user-manual.md`](../../docs/mcp-user-manual.md)
- MCP HTTP 엔드포인트: `https://api.1000.school/mcp`
- 인증: `Authorization: Bearer <API_TOKEN>`
- 제공 capability:
  - Tools: `daily_snippets_page_data`, `daily_snippets_get`, `daily_snippets_list`, `daily_snippets_create`, `daily_snippets_organize`, `daily_snippets_feedback`, `daily_snippets_update`, `daily_snippets_delete`, `weekly_snippets_page_data`, `weekly_snippets_get`, `weekly_snippets_list`, `weekly_snippets_create`, `weekly_snippets_organize`, `weekly_snippets_feedback`, `weekly_snippets_update`, `weekly_snippets_delete`
  - Resources: `gcs://me/profile`, `gcs://me/achievements`

토큰은 로그인 세션으로 `/auth/tokens`에서 발급할 수 있으며,
`/auth/tokens`는 CSRF 검증이 적용됩니다.

## 테스트/CI 참고

- CI Python 버전: 3.11 (`.github/workflows/server-test.yml`)
- 테스트 파일: [`apps/server/tests`](./tests)

## 관련 문서

- 루트 개요: [`../../README.md`](../../README.md)
- 보안 감사: [`../../doc/security_audit.md`](../../doc/security_audit.md)
- 성능 감사: [`../../doc/performance_audit.md`](../../doc/performance_audit.md)
- DB 문서: [`../../doc/database.md`](../../doc/database.md)
