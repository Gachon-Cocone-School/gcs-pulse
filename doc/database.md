# Database

- 최신 업데이트: 2026-02-27
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

현재 모델 기준 12개 테이블:

1. `users`
2. `terms`
3. `consents`
4. `route_permissions`
5. `role_assignment_rules`
6. `teams`
7. `daily_snippets`
8. `weekly_snippets`
9. `api_tokens`
10. `comments`
11. `achievement_definitions`
12. `achievement_grants`

정확한 컬럼/제약은 `apps/server/app/models.py`를 단일 기준으로 확인하세요.

## 4) 운영 관점 체크포인트

- 마이그레이션/시드 실행 전 환경변수(`ENVIRONMENT`, DB URL) 확인
- 테스트 환경에서는 `TEST_DATABASE_URL` 분리 권장
- 신규 라우트 추가 시 `migrate_and_seed.py`를 통한 `route_permissions`/`role_assignment_rules` 메타 동기화 여부 확인
- `/auth/logout` special rule 메서드가 `POST` 기준으로 유지되는지 점검
- core route rate limit 적용 대상(`tokens`/`teams`/`users PATCH`/`mcp`) 변경 시 보안/성능 문서와 교차 갱신

## 5) 교차 문서

- 서버 실행/환경: [`../apps/server/README.md`](../apps/server/README.md)
- 보안 감사: [`./security_audit.md`](./security_audit.md)
- 성능 감사: [`./performance_audit.md`](./performance_audit.md)

## 6) 참고

테이블 상세 설명(컬럼/인덱스/연관 관계)이 필요하면 이 문서를 확장하되,
코드(`models.py`)와 불일치가 생기지 않도록 함께 갱신합니다.
