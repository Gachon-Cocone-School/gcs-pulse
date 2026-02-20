# 구현 계획: Supabase(Postgres) 마이그레이션 (작성일: 2026-02-13)

요약
- 목적: 로컬 개발 및 CI에서 Postgres(Supabase)를 사용하여 테스트/개발 환경을 통일하고, 기존 SQLite 기반 테스트를 Postgres로 전환할 수 있도록 한다.
- 접근 방식: TDD와 작은 커밋 단위를 유지하는 PR 사이즈 작업으로 진행. tests/conftest.py를 환경변수 우선으로 바꾸고, CI 워크플로와 .env.example 및 README를 업데이트.

작업 목록 (작은 단계로 분할)

1) 준비 및 환경
- 작업: 디자인 문서 검토 및 의존성 확인
- 파일: 없음
- 세부 단계:
  - requirements.txt에 asyncpg가 포함되어 있는지 확인
  - 개발자에게 Supabase 프로젝트(또는 로컬 Postgres) 접속 정보 준비 요청

2) tests/conftest.py 개선 (환경변수 우선 및 Postgres 지원)
- 작업: apps/server/tests/conftest.py 파일을 PATCH
- 파일: /Users/hexa/projects/temp/gcs-mono/apps/server/tests/conftest.py
- 세부 단계 (TDD 순서):
  - 기존 테스트가 실패하도록 의도적으로 테스트 DB URL을 환경변수로 읽도록 변경 (이미 적용된 패치)
  - 로컬 sqlite 기본 동작(파일 기반) 유지
  - Postgres일 경우 TRUNCATE 기반 cleanup 적용
  - 테스트 실행으로 동작 확인

3) CI 워크플로 추가
- 작업: GitHub Actions 워크플로 (.github/workflows/ci.yml) 추가
- 파일: /Users/hexa/projects/temp/gcs-mono/.github/workflows/ci.yml
- 세부 단계:
  - Workflow는 secrets.TEST_DATABASE_URL 및 secrets.PSQL_TEST_DATABASE_URL를 사용
  - psql이용 SQL 초기화(옵션) 및 migrate_and_seed.py 실행
  - pytest 실행

4) .env.example 및 README 업데이트
- 작업: apps/server/.env.example에 TEST_DATABASE_URL 예시 추가 및 README에 Supabase 테스트 DB 사용 설명 추가
- 파일: /Users/hexa/projects/temp/gcs-mono/apps/server/.env.example
  및 /Users/hexa/projects/temp/gcs-mono/apps/server/README.md
- 세부 단계:
  - .env.example에 TEST_DATABASE_URL 변수 추가 (이미 적용된 패치)
  - README에 CI용 환경변수 및 초기화 절차 명시

5) 개발자 체크리스트 작성
- 작업: 개발자가 로컬 개발 및 CI 준비시 따라야 할 명확한 체크리스트 제공
- 파일: docs/plans/2026-02-13-supabase-migration-implementation-plan.md (현재 문서에 포함)
- 세부 단계:
  - 로컬 개발자: TEST_DATABASE_URL unset하면 기존 sqlite 동작 유지
  - CI: 반드시 TEST_DATABASE_URL는 테스트 전용 DB, PSQL_TEST_DATABASE_URL은 psql 초기화용(선택)으로 설정

6) PR 사이즈 작업 분할 (권장)
- 작업: PR 단위로 작업을 작게 나눔
- 단계/PR 제안:
  - PR-1: tests/conftest.py 변경 + 간단한 설명, 작은 테스트로 검증
  - PR-2: .github/workflows/ci.yml 추가 (초기화 스크립트 포함)
  - PR-3: .env.example 및 README 변경
  - PR-4: CI 보완 (artifacts, matrix, caching 등), 문서 보강

테스트 기반 실행 계획 (TDD)
- 로컬: pytest 실행 (기본 sqlite) -> 변경된 conftest로 인해 동일하게 작동
- Postgres: export TEST_DATABASE_URL="postgresql+asyncpg://..." 후 pytest 실행
- CI: secrets에 TEST_DATABASE_URL 세팅 후 PR 생성 -> Actions가 DB 초기화 및 pytest 실행

Developer checklist (개발자용)
- [ ] requirements.txt에 asyncpg 포함 확인
- [ ] Supabase 또는 Postgres 접속 정보 확보
- [ ] 로컬에서 TEST_DATABASE_URL을 비워두면 sqlite로 동작하는지 확인
- [ ] Postgres로 테스트하려면 TEST_DATABASE_URL 환경변수 설정 후 pytest 실행
- [ ] CI secrets: TEST_DATABASE_URL, PSQL_TEST_DATABASE_URL (옵션) 등록
- [ ] PR은 작고 자주: conftest 변경 후 바로 테스트, CI 워크플로는 별 PR

PR-sized tasks (권장 분할)
- PR-1: 변경: /Users/hexa/projects/temp/gcs-mono/apps/server/tests/conftest.py
  - 설명: 환경변수 기반 TEST_DATABASE_URL 지원 (sqlite fallback 유지), Postgres TRUNCATE cleanup
  - 테스트: 로컬 pytest 통과

- PR-2: 추가: /Users/hexa/projects/temp/gcs-mono/.github/workflows/ci.yml
  - 설명: CI에서 TEST_DATABASE_URL을 사용하여 DB 초기화 및 pytest 실행
  - 테스트: Actions에서 workflow가 실행되고 pytest가 통과

- PR-3: 변경: /Users/hexa/projects/temp/gcs-mono/apps/server/.env.example 및 README.md
  - 설명: Supabase 예시 및 TEST_DATABASE_URL 문서화
  - 테스트: 문서 검토

- PR-4: 개선: CI 보강 및 문서 최종화
  - 설명: artifact 업로드, matrix, 캐싱, 더 강력한 초기화/rollback 스크립트 추가

수행에 필요한 파일 패치

1) apps/server/tests/conftest.py (전체 수정본)
- 파일 경로: /Users/hexa/projects/temp/gcs-mono/apps/server/tests/conftest.py
- 본문: (레포에 적용된 전체 파일 내용을 아래에 포함)


2) GitHub Actions CI 예시
- 파일 경로: /Users/hexa/projects/temp/gcs-mono/.github/workflows/ci.yml
- 본문: (레포에 추가된 전체 파일 내용을 아래에 포함)


3) .env.example 변경
- 파일 경로: /Users/hexa/projects/temp/gcs-mono/apps/server/.env.example
- 변경: TEST_DATABASE_URL 변수 추가 (이미 적용됨)


수행 순서 (권장)
1. PR-1 준비: conftest.py 변경 및 단위/통합 테스트 실행
2. 작은 커밋으로 PR-1 생성, 리뷰 요청
3. PR-2 준비: CI workflow 추가 (비밀변수 세팅 안내 포함)
4. PR-2 생성 및 병합 후 Actions 실행 확인
5. PR-3 문서 개선 PR 생성
6. PR-4 고도화 및 모니터링

문의 및 리스크
- 원격 DB 사용 시 테스트가 느려질 수 있음. CI에서는 전용 테스트 DB를 사용하는 것이 중요함.
- 절대 프로덕션 DB를 TEST_DATABASE_URL로 사용하지 않도록 주의.

저장 위치:
- /Users/hexa/projects/temp/gcs-mono/docs/plans/2026-02-13-supabase-migration-implementation-plan.md

참고: 이미 디자인 문서(/Users/hexa/projects/temp/gcs-mono/docs/plans/2026-02-13-supabase-migration-design.md)를 작성해두었습니다. 다음 단계로 PR 패치와 커밋을 원하시면 알려주세요.