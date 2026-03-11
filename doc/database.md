# Database

- 최신 업데이트: 2026-03-09
- 대상 범위: `apps/server`
- 역할: 서버 DB 구조/운영 기준 요약

관련 문서:

- 서버 실행/환경: [`../apps/server/README.md`](../apps/server/README.md)
- 루트 개요: [`../README.md`](../README.md)

## 1) 환경별 DB 선택 규칙

코드 기준(`apps/server/app/database.py`):

- `ENVIRONMENT=production` → `DATABASE_URL`
- `ENVIRONMENT=test` + `TEST_DATABASE_URL` 존재 → `TEST_DATABASE_URL`
- 그 외(`development` 등) → `DEV_DATABASE_URL`

기본 예시는 SQLite URL이지만, Postgres(`postgresql+asyncpg://...`)도 지원합니다.

## 2) 스키마 관리 방식

주요 소스:

- 모델 정의: `apps/server/app/models.py`
- 마이그레이션/시드 스크립트: `apps/server/scripts/migrate_and_seed.py`
- 초기 SQL 참고: `apps/server/scripts/init_db.sql`

일반 동기화 명령:

```bash
cd apps/server
PYTHONPATH=. python scripts/migrate_and_seed.py
```

## 3) 서비스 테이블 목록

현재 모델 기준 17개 테이블:

1. `users`
2. `terms`
3. `consents`
4. `route_permissions`
5. `role_assignment_rules`
6. `teams`
7. `peer_evaluation_sessions`
8. `peer_evaluation_session_members`
9. `peer_evaluation_submissions`
10. `daily_snippets`
11. `weekly_snippets`
12. `api_tokens`
13. `comments`
14. `notifications`
15. `notification_settings`
16. `achievement_definitions`
17. `achievement_grants`

정확한 컬럼/제약은 `apps/server/app/models.py`를 단일 기준으로 확인하세요.

## 4) 운영 관점 체크포인트

- 마이그레이션/시드 실행 전 환경변수(`ENVIRONMENT`, DB URL) 확인
- 테스트 환경에서는 `TEST_DATABASE_URL` 분리 권장
- 신규 라우트 추가 시 `migrate_and_seed.py`를 통한 `route_permissions`/`role_assignment_rules` 메타 동기화 여부 확인
- 동료평가 도메인(`peer_evaluation_sessions`, `peer_evaluation_session_members`, `peer_evaluation_submissions`)은 마이그레이션 시드로 DDL 보강되며, `peer_evaluation_sessions`는 `title`, `professor_user_id`, `is_open`, `access_token`, timestamp 컬럼 중심으로 운영됨(기존 `project_name` 제거)
- 교수/학생 플로우 API 권한 메타도 함께 동기화됨
- `/auth/logout` special rule 메서드가 `POST` 기준으로 유지되는지 점검
- core route rate limit 적용 대상(`tokens`/`teams`/`users PATCH`/`mcp`) 변경 시 보안/성능 문서와 교차 갱신

## 5) 교차 문서

- 서버 실행/환경: [`../apps/server/README.md`](../apps/server/README.md)
- 보안 감사: [`./security_audit.md`](./security_audit.md)
- 성능 감사: [`./performance_audit.md`](./performance_audit.md)

## 6) 운영 백업/복원

### 백업 산출물 구조

기본 경로: `apps/server/backups/db`

- `<backup_id>.sql`: plain SQL dump (`pg_dump` 산출물, `public` 스키마만 포함)
- `<backup_id>.meta.json`: 백업 메타데이터
- `index.jsonl`: 백업 메타 append-only 인덱스

`meta.json` MVP 필드:

- `backup_id`
- `created_at_utc`
- `environment`
- `sql_file`
- `size_bytes`
- `sha256`
- `db_host`
- `db_name`
- `pg_dump_version`

### backup_id 규칙

- 포맷: `YYYYMMDDTHHMMSSZ-<environment>`
- 예시: `20260311T020000Z-production`

### 복원 표준 절차

1. `--dry-run`으로 백업 식별/파일 존재/checksum 검증
2. `--verify-db-url`로 임시 검증 DB 선복원
3. `--execute`로 실제 대상 DB 복원

예시:

```bash
cd apps/server

# dry-run
PYTHONPATH=. python scripts/db_restore.py --backup-id 20260311T020000Z-production --dry-run

# verify DB 선복원
PYTHONPATH=. python scripts/db_restore.py \
  --backup-id 20260311T020000Z-production \
  --verify-db-url "postgresql://user:pass@127.0.0.1:5433/gcs_verify"

# 실제 복원
PYTHONPATH=. python scripts/db_restore.py \
  --backup-id 20260311T020000Z-production \
  --execute
```

주의사항:

- `--execute`가 없으면 대상 DB 실복원은 수행되지 않습니다.
- checksum 불일치 시 즉시 중단됩니다.
- 운영 DB 적용 전 검증 DB 선복원을 권장합니다.

## 7) 참고

테이블 상세 설명(컬럼/인덱스/연관 관계)이 필요하면 이 문서를 확장하되,
코드(`models.py`)와 불일치가 생기지 않도록 함께 갱신합니다.
