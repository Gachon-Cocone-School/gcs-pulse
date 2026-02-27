# 성능 감사 보고서 (Performance Audit Report)

- 최신 업데이트: 2026-02-27
- 대상 범위: `apps/server` (FastAPI)
- 역할: 백엔드 성능 병목/개선 우선순위 요약

관련 문서:

- 백엔드 개요: [`../apps/server/README.md`](../apps/server/README.md)
- 데이터베이스 구조: [`./database.md`](./database.md)
- 보안 감사: [`./security_audit.md`](./security_audit.md)

## 1) 개요

현재 구조는 소규모 트래픽에서 안정적으로 동작하나, 인증/권한 의존성과 목록 API의 누적 조회 구조 때문에 요청당 DB 왕복 수가 빠르게 증가합니다.

이번 업데이트는 기존 수치(기준값) + 코드 경로 분석을 합쳐, 병목 우선순위를 명확히 정리합니다.
또한 보안 강화 라운드에서 확정된 core route rate limit 적용 범위(`tokens`/`teams`/`users PATCH`/`mcp`)와 권한 메타 정합성 기준(`route_permissions`/`role_assignment_rules`)을 운영 관점에 반영합니다.

## 2) 기준 지표와 코드 관찰

### 2.1 기존 기준 지표(유지)

| 구분 | 관찰값(기존 기준) | 비고 |
| :--- | :---: | :--- |
| 단일 DB 쿼리 (`SELECT 1`) | 약 33ms | 네트워크 왕복 시간 영향 |
| 권한/사용자 조회 누적 | 약 80~100ms | 보호 라우트 기준 |
| 초기화(첫 연결+첫 쿼리) | 약 360ms | 콜드 스타트 체감 |

> 위 수치는 기존 감사 기준값이며, 환경/DB 위치에 따라 달라질 수 있습니다.

### 2.2 코드 경로 기준 요청당 DB 왕복(추정)

- 현재 기준에서 `tokens`/`teams`/`users PATCH`/`mcp`는 rate limit 적용 대상이며, 트래픽 급증 시 해당 경로를 우선 모니터링합니다.
- `route_permissions`/`role_assignment_rules`는 런타임 강제보다 메타 동기화 기준으로 관리하므로, 성능 점검 시에는 인증/의존성 체인과 별도 축으로 해석합니다.

| 경로 | 요청당 DB 왕복(추정) | 비고 |
| :--- | :---: | :--- |
| 세션 보호 라우트 (`get_active_user`) | `3 + 라우트 본문 쿼리` | 사용자 조회 + consents 로딩 + required terms 조회 |
| Bearer 보호 라우트 (`/mcp/*` 등) | `4 + 라우트 본문 쿼리` | 토큰 조회 + 유저 조회 + `last_used_at` update/refresh |
| `POST /consents` | `4~6` | 기존 동의 존재 여부/신규 저장(INSERT+refresh)에 따라 변동 |
| `GET /daily-snippets` (`limit=N`) | 세션 `5 + N`, Bearer `7 + N` | viewer 조회 + count/page/comments 집계 + per-item owner 조회 |
| `GET /weekly-snippets` (`limit=N`) | 세션 `4 + N`, Bearer `6 + N` | viewer 조회 + count/page 집계 + per-item owner 조회 |

- `N`은 응답 `items` 개수입니다.
- 실제 왕복 수는 분기(예: snippet_id 지정, 빈 결과, ORM 로딩 전략, 예외)에 따라 달라질 수 있습니다.

## 3) 상세 분석

### 3.1 인증/권한 핫패스

- `get_active_user`는 아래를 매 요청 수행합니다.
  1) `users` 조회(이메일 기준) + `consents` 로딩
  2) `terms`에서 필수/활성 약관 ID 조회
  3) 누락 약관 검사
- 인증 성공 기준 `get_active_user` 자체에서 **최소 3회 왕복**이 발생합니다.
- 이 의존성은 `/users`, `/teams`, `/auth/tokens`, `/leaderboards`, `/achievements` 등 다수 라우트에서 공통 사용됩니다.
- `email` 조회는 `lower(email)` 패턴을 사용하고 있어 DB/콜레이션 조건에 따라 일반 인덱스 활용이 제한될 수 있습니다.

### 3.1.1 `POST /consents` 경로

- 약관 동의 경로는 인증 이후 다음 순서로 조회/저장을 수행합니다.
  1) 사용자 조회
  2) 약관 존재 조회
  3) 기존 동의 조회
  4) (미동의 시) 동의 INSERT + refresh
- 경로 분기에 따라 요청당 DB 왕복은 **4~6회** 범위입니다.

### 3.2 Bearer 인증 경로의 read+write 누적

- `/mcp/sse`, `/mcp/messages`는 이번 라운드에서 core route rate limit 적용 대상으로 확정되었습니다.
- `/auth/tokens` 역시 세션+CSRF 경로에서 rate limit 적용 대상으로 유지되므로, 토큰 발급/회수 폭주 시 DB write 부담을 함께 점검해야 합니다.

- Bearer 경로는 인증 단계에서 토큰 조회 → 유저 조회 이후 `touch_api_token_last_used_at`로 write(커밋/리프레시)를 수행합니다.
- 즉, 읽기 요청 성격의 엔드포인트라도 인증 과정에서 write 비용이 섞여 지연이 커질 수 있습니다.

### 3.3 목록 API의 누적 쿼리 패턴

- `daily_snippets` 목록은 `count + page 조회 + 댓글 집계`를 수행하고, 이후 editable 계산에서 항목별 owner 조회가 반복됩니다.
- `weekly_snippets` 목록도 `count + page 조회` 후 동일한 owner 조회 반복이 있습니다.
- 결과적으로 page size(`limit`)가 커질수록 DB 왕복이 선형 증가(N+1)합니다.
- 검색 조건 `ilike('%...%')`는 일반 B-Tree 인덱스와 궁합이 낮아 full scan 성향이 나타날 수 있습니다.

### 3.3.1 page-data 경로 증폭

- page-data 응답은 내부적으로 현재/이전/다음 구간 조회를 각각 수행하는 구조입니다.
- 특히 daily 경로는 내부 목록 조회 1회마다 `count + page + comments 집계`가 동반되어, page-data 단건 요청에서도 DB 호출이 빠르게 늘어납니다.

### 3.4 DB 레이어 설정 상태

- SQLAlchemy async 엔진/세션은 사용 중입니다.
- 다만 엔진 생성 시 `pool_pre_ping`, `pool_recycle`, `pool_size`, `max_overflow` 등 풀 튜닝 파라미터는 명시하지 않고 dialect 기본값을 사용합니다.
- 주요 인덱스(`users.email`, `daily_snippets.user_id/date`, `weekly_snippets.user_id/week`, `api_tokens.token_hash` 등)는 존재합니다.

## 4) 권장 개선안

### 단기

1. **측정 자동화 우선**
   - 핵심 API별 요청당 DB 쿼리 수/DB 시간(ms) 스냅샷을 정기 수집합니다.
2. **인증 핫패스 경량화**
   - `get_active_user`의 필수 약관 조회 비용을 줄이기 위해 캐시/사전조회 전략을 검토합니다.
3. **page-data/목록 API N+1 축소**
   - editable 계산용 owner 조회를 일괄 조회 방식으로 전환해 per-item 조회를 줄입니다.
4. **Bearer write 빈도 제어**
   - `last_used_at` 갱신 조건(예: 최소 간격) 도입을 검토해 read 경로 write 빈도를 낮춥니다.
5. **인덱스/검색 전략 점검**
   - `lower(email)` 및 `ilike('%q%')` 패턴에 맞는 인덱스 전략(함수/전문검색 계열)을 검토합니다.

### 중장기

1. **분산 캐시(예: Redis) 도입 검토**
   - 다중 인스턴스 환경에서 인증/정책성 조회 캐시 일관성을 확보합니다.
2. **네트워크 지연 완화**
   - DB 배치/토폴로지 개선으로 RTT 민감 구간을 줄입니다.
3. **읽기 경로 최적화 구조화**
   - 리더보드/목록성 API를 중심으로 조회 전용 패턴(사전 집계/읽기 모델)을 검토합니다.

## 5) 운영 체크리스트

- [ ] `/auth/me`, `/leaderboards`, `/achievements/me`, `/daily-snippets`, `/weekly-snippets`의 p50/p95 응답시간 모니터링
- [ ] core route rate limit 대상(`tokens`/`teams`/`users PATCH`/`mcp`)의 429 비율/응답시간/DB 시간 동시 추적
- [ ] 위 엔드포인트의 요청당 DB 쿼리 수 및 총 DB 시간(ms) 수집
- [ ] `get_active_user` 단계별 시간(사용자/consents/terms) 분해 지표 수집
- [ ] `/consents` 경로의 분기별(기존 동의/신규 저장) 쿼리 수·지연시간 수집
- [ ] `/daily-snippets/page-data`, `/weekly-snippets/page-data` 요청당 쿼리 수/총 DB 시간 추적
- [ ] `/mcp/sse`, `/mcp/messages`에서 Bearer 인증 read/write 비율 및 `last_used_at` 갱신 비용 추적
- [ ] `daily/weekly` 목록에서 `limit`(10/30/50) 변화에 따른 쿼리 수/응답시간 증가율 추적
- [ ] 검색(`q`, `%ilike%`) 사용 시/미사용 시 실행시간 비교
- [ ] 콜드스타트(첫 연결+첫 쿼리) vs 웜쿼리(`SELECT 1`) 분리 모니터링
- [ ] 배치(`run_daily_achievement_grants.py`) 실행 시간 추적
- [ ] 권한 메타(`route_permissions`/`role_assignment_rules`) 동기화 실행 시점과 성능 지표 변동을 분리 기록

교차 문서:

- 보안 감사: [`./security_audit.md`](./security_audit.md)
- DB 운영 기준: [`./database.md`](./database.md)
- 서버 운영 문서: [`../apps/server/README.md`](../apps/server/README.md)

## 6) 결론

현재 성능 병목은 **네트워크 지연 + 인증 핫패스 누적 조회 + 목록 API의 N+1 패턴**에 집중되어 있습니다.

우선순위는 **(1) 측정 자동화**, **(2) 인증/목록 핫패스 쿼리 축소**, **(3) 캐시/인덱스 전략 보강** 순으로 두는 것이 효과적입니다.
