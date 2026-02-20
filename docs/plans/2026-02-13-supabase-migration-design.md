# Supabase(Postgres) 마이그레이션 디자인

작성일: 2026-02-13
주제: 로컬 개발/테스트를 원격 Supabase(Postgres) 개발 DB로 전환하고, 프로덕션도 Supabase로 운영하기 위한 디자인 문서

요약
- 목표: 개발자는 로컬에 Postgres를 설치하지 않고도 원격 Supabase 개발 DB에 연결하여 개발 및 테스트를 수행한다. 프로덕션은 Supabase로 유지.
- 권장안: 별도 Supabase 프로젝트(예: gcs-mono-dev / gcs-mono-test)를 만들어 개발·테스트용 DB로 사용. CI도 동일한 테스트 DB(또는 별도 테스트 DB)를 사용하도록 구성.

성공 기준
- 앱 서버는 DATABASE_URL 환경변수로 Supabase Postgres에 정상 연결한다.
- 제공된 SQL 스크립트(init_db.sql, migrate_and_seed.py)가 Supabase DB에서 문제 없이 동작한다.
- 기존 테스트(또는 대부분의 통합 테스트)는 Postgres에서 성공적으로 통과한다.
- 로컬 개발자는 로컬 DB 설치 없이도 개발/테스트 가능하다.

제약 조건·전제
- 현재 repo 기본값은 sqlite+aiosqlite:///./gcs_lms.db. tests/conftest.py는 기본적으로 file-based sqlite(test_shared.db)를 사용.
- 마이그레이션은 Alembic 같은 표준 마이그레이션 툴이 아니라 scripts/migrate_and_seed.py 및 raw SQL 파일로 관리됨.
- requirements.txt에 asyncpg 및 aiosqlite가 모두 포함되어 있음.

대안 비교
1) 개발/테스트를 별도 Supabase 프로젝트로 전환 (권장)
   - 장점: 엔진 일관성(Postgres), Postgres 전용 SQL 확인 가능, 로컬 설정 감소
   - 단점: 원격 네트워크 의존성/지연, 보안·비용 고려

2) 로컬 Docker Postgres 사용
   - 장점: 네트워크 오버헤드 없음, CI에서도 Docker 사용 시 유사환경
   - 단점: 모든 개발자가 Docker 필요, 로컬 리소스 요구

3) 테스트는 SQLite 유지
   - 장점: 간단·빠름
   - 단점: Postgres 전용 SQL/인덱스/타입 관련 버그 미검출

권장 선택: 1번(별도 Supabase 프로젝트를 개발/테스트용으로 사용)
이유: repo에 이미 Postgres 전용 DDL/스크립트가 있고, 실환경과 동일한 DB 엔진에서 테스트하는 것이 안정성 면에서 우수함.

구체 설계 및 실행 단계
(아래 모든 명령은 로컬에서 실행할 때 절대경로를 사용하거나 프로젝트 루트에서 실행하세요.)

1) Supabase 프로젝트 생성
- Supabase에서 개발용 프로젝트(gcs-mono-dev)와 테스트용 프로젝트(gcs-mono-test)를 생성(권장).
- 각 프로젝트에서 DB 접속 정보(DB_USER, PASSWORD, HOST, DB_NAME)를 확인.

2) 환경변수 정리
- 서버 런타임
  - DATABASE_URL: postgresql+asyncpg://<USER>:<PASS>@<HOST>:5432/<DB_NAME>?sslmode=require
- 테스트
  - TEST_DATABASE_URL: postgresql+asyncpg://<USER>:<PASS>@<HOST>:5432/<TEST_DB_NAME>?sslmode=require
  - (psql용) PSQL_TEST_DATABASE_URL: postgresql://<USER>:<PASS>@<HOST>:5432/<TEST_DB_NAME>?sslmode=require
- 보안: 실제 키/비밀번호는 절대 레포에 커밋하지 말 것. CI secret/환경 변수로 관리.

3) DB 초기화(스키마 적용)
- 권장 순서(빠른 예시):
  1) psql로 init_db.sql 적용:
     psql "$PSQL_TEST_DATABASE_URL" -f /absolute/path/to/apps/server/scripts/init_db.sql
  2) 추가 마이그레이션/시드 적용:
     env TEST_DATABASE_URL="$TEST_DATABASE_URL" python3 /absolute/path/to/apps/server/scripts/migrate_and_seed.py
- psql이 없을 경우 migrate_and_seed.py만으로도 초기화 가능(스크립트가 Base.metadata.create_all()과 raw SQL을 실행함).

4) 애플리케이션 설정 및 실행
- /apps/server/.env 또는 로컬 환경에 DATABASE_URL을 설정 후 서버 시작
  - 예: export DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/dbname?sslmode=require"
  - 프로젝트 루트에서: npx turbo run dev 또는 README의 서버 시작 명령

5) 테스트 전환(핵심 변경사항)
- 파일: apps/server/tests/conftest.py
  - 변경 요약:
    - 기존 하드코딩된 TEST_DATABASE_URL = "sqlite+aiosqlite:///./test_shared.db" 를 환경변수 우선으로 대체
    - TEST_DATABASE_URL이 sqlite로 시작하면 기존 파일 기반 로직 실행
    - Postgres URL인 경우 test_engine을 생성하고 session-scoped fixture에서 Base.metadata.drop_all() 및 create_all()로 초기화
    - 테스트 종료 시 세션 범위로 cleanup(drop_all 또는 truncate)
  - 이유: 최소한의 코드 변경으로 Postgres와 SQLite 모두 지원 가능하도록 함

- CI: GitHub Actions 예시
  - secrets: TEST_DATABASE_URL, PSQL_TEST_DATABASE_URL 등록
  - steps:
    - checkout
    - python deps 설치
    - DB 초기화:
      - run: psql "$PSQL_TEST_DATABASE_URL" -f apps/server/scripts/init_db.sql
      - run: env TEST_DATABASE_URL="$TEST_DATABASE_URL" python3 apps/server/scripts/migrate_and_seed.py
    - run tests: env TEST_DATABASE_URL="$TEST_DATABASE_URL" pytest -q
  - 대안: psql이 없는 경우 migrate_and_seed.py로 초기화 대체

6) 롤백·백업
- 마이그레이션 전에 Supabase snapshot(backup) 생성 권장(특히 production). 개발/테스트 DB는 필요 시 drop 후 재생성 가능.

7) 보안·운영 주의사항
- 테스트 DB 및 CI 계정은 최소 권한만 부여
- 절대로 프로덕션 DB 접속 정보로 테스트 DB를 초기화하지 않도록 CI secret 관리 엄격히
- 원격 DB라서 네트워크 장애/레イ턴시 테스트 실패 영향이 있으므로 테스트 리트라이/타임아웃 처리 고려

변경해야 할 코드/파일(요약)
- apps/server/app/core/config.py — DATABASE_URL 기본값(그대로 두고 환경변수로 덮음)
- apps/server/tests/conftest.py — TEST_DATABASE_URL 읽기 및 Postgres 초기화/cleanup 로직 추가 (핵심)
- CI 워크플로 파일(없으면 새로 작성) — TEST DB 초기화 및 pytest 단계 추가
- README/.env.example — Supabase URL 예시 추가

검증(수용 기준)
- psql/SQLAlchemy로 접속하여 모든 테이블이 생성된 것을 확인
- 개발 환경에서 서버를 실행하여 주요 API 엔드포인트 몇 개 호출해 정상 동작 확인
- CI에서 pytest가 통과

다음 단계(제안)
1. 이 디자인을 레포에 저장(지금 수행됨)
2. writing-plans 스킬을 사용해 구현 계획(구체적 패치/PR 단위 작업 목록, tests/conftest.py의 패치 코드, CI workflow 예시 파일)을 생성
3. 사용자 승인 후 실제 코드 패치 및 커밋 생성(사용자에게 커밋/PR 생성 권한 요청)

-------------------------
저장 위치: docs/plans/2026-02-13-supabase-migration-design.md

문의: 문서를 확인하신 후 "계속"이라고 하시면 writing-plans 스킬로 세부 구현 계획을 생성하겠습니다.
