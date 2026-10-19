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
- (선택) `AB_PRACTICE_UPLOAD_DIR`: A/B 실습 이미지 저장 디렉터리. 기본값은 `apps/server/data/ab-practice`이며 운영에서는 지속 저장되는 경로를 지정합니다.
- (선택) Copilot 연동 변수: `GITHUB_*`, `COPILOT_*`
- (선택) TypeSafe JEV: `TYPESAFE_API_KEY`, `TYPESAFE_MODEL`,
  `TYPESAFE_PLAYBOOK_CONFIDENCE_THRESHOLD`, `TYPESAFE_PLAYBOOK_EVIDENCE_THRESHOLD`

### A/B 실습 등록 권한

- 세션 교수는 등록 화면에서 직접 A/B 테스트 항목을 추가하고 모든 항목을 수정·삭제할 수 있습니다.
- QR 주소에 접근할 수 있는 로그인 사용자는 누구나 항목을 등록할 수 있습니다.
- QR 등록자는 본인이 올린 항목만 수정·삭제할 수 있습니다. 등록 종료 후에는 변경할 수 없지만, 관리자가 등록을 다시 개시하면 이어서 수정·삭제할 수 있습니다.
- 투표는 로그인 없이 참여할 수 있으며, 처음 접속할 때 입력한 이름과 세션별 일련번호로 현황을 표시합니다.
- 브라우저에 익명 참여 토큰을 저장해 같은 브라우저에서는 기존 참여와 진행 상태를 이어갑니다. 브라우저/기기 변경이나 저장 정보 삭제 시에는 새 참여자로 기록될 수 있습니다.
- `migrate_and_seed.py`는 ORM 모델에 등록된 A/B 실습 테이블을 포함해 누락된 테이블을 생성합니다. 이 스크립트는 기존의 앱 전체 마이그레이션과 시드 작업도 수행합니다.
- Supabase에 A/B 실습 테이블만 수동 생성하려면 [`scripts/0003_create_ab_practice_tables.sql`](./scripts/0003_create_ab_practice_tables.sql)을 SQL Editor에서 실행합니다. 이 스크립트는 A/B 실습 테이블과 인덱스만 생성합니다.

### 스니펫 AI 평가

스니펫 피드백은 역할을 분리합니다.

- TypeSafe System One(JEV)는 5개 채점 축과 Playbook 관계를 구조화된 점수·확률로 판단합니다. 서버가 축별 배점을 합산해 `total_score`를 계산합니다.
- Copilot은 멘토 코멘트, 다음 행동 등 자연어 피드백을 작성합니다.
- Playbook은 `revise`/`extend` 판단의 신뢰도와 직접 근거 확률이 모두 기본 `0.80` 이상일 때만 자동 반영됩니다. 그 밖의 경우 기존 Playbook을 유지하며, 검토 대기열은 만들지 않습니다.
- TypeSafe 호출 실패 또는 API 키 미설정 시에는 JEV 보강과 Playbook 자동 변경을 건너뛰고 Copilot 피드백을 그대로 제공합니다.

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
5 9 * * * /opt/gcs-pulse/apps/server/venv/bin/python /opt/gcs-pulse/apps/server/scripts/run_daily_achievement_grants.py >> /var/log/gcs/daily_achievement_grants.log 2>&1
```

## DB 백업/복원

백업/복원 스크립트는 `apps/server/scripts/`에 위치합니다.

- 백업: `scripts/db_backup.py`
- 복원: `scripts/db_restore.py`
- 기본 백업 경로: `apps/server/backups/db`
- 백업/복원 범위: `public` 스키마만 대상 (`auth` 등 Supabase 관리 스키마 제외)

백업 실행 예시:

```bash
cd apps/server
PYTHONPATH=. python scripts/db_backup.py

# 경로 오버라이드
PYTHONPATH=. python scripts/db_backup.py --backup-dir /opt/gcs-pulse/backups/db
```

복원 실행 예시:

```bash
cd apps/server

# 1) 대상 백업 검증만 수행
PYTHONPATH=. python scripts/db_restore.py --backup-id 20260311T020000Z-production --dry-run

# 2) 검증용 임시 DB 선복원 (public 덮어쓰기)
PYTHONPATH=. python scripts/db_restore.py \
  --backup-id 20260311T020000Z-production \
  --verify-db-url "postgresql://user:pass@127.0.0.1:5433/gcs_verify" \
  --overwrite-public \
  --timeout-seconds 180

# 3) 실제 대상 DB 복원 (명시적 --execute 필요)
PYTHONPATH=. python scripts/db_restore.py \
  --backup-id 20260311T020000Z-production \
  --overwrite-public \
  --timeout-seconds 180 \
  --execute
```

cron 예시(일 1회 백업):

```cron
CRON_TZ=Asia/Seoul
10 3 * * * cd /opt/gcs-pulse/apps/server && PYTHONPATH=. /opt/gcs-pulse/apps/server/venv/bin/python scripts/db_backup.py >> /var/log/gcs/db_backup.log 2>&1
```

운영 권장 절차는 `dry-run -> verify-db-url 선복원 -> --overwrite-public + --execute` 순서입니다.

복원 옵션 참고:

- `--overwrite-public`: 복원 전 `DROP SCHEMA IF EXISTS public CASCADE` 수행 후 dump 적용
- `--timeout-seconds`: psql 실행 타임아웃(기본 180초)
- `--terminate-blocking-sessions`: `--overwrite-public`과 함께 사용할 수 있으며, 복원 방해 세션을 종료 시도
  - 단, Supabase 같은 managed DB에서는 superuser 세션 종료 권한이 없어 실패할 수 있으므로 필요 시에만 사용

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
