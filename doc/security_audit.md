# 백엔드 보안 감사 요약

- 최신 업데이트: 2026-02-27
- 대상 범위: `apps/server` (FastAPI)
- 역할: 보안 상태를 코드 기준으로 요약한 문서

관련 문서:

- 백엔드 실행/환경: [`../apps/server/README.md`](../apps/server/README.md)
- DB 구조: [`./database.md`](./database.md)
- 성능 감사: [`./performance_audit.md`](./performance_audit.md)

## 1) 요약

현재 백엔드는 세션 기반 인증, CSRF 검증, Bearer 인증 경로 분리, production 환경 `SECRET_KEY` fail-fast를 구현하고 있습니다.
이번 라운드에서는 core route rate limit 적용 대상을 `tokens`/`teams`/`users PATCH`/`mcp`까지 확장했고, `/auth/logout` special rule 메서드 정합성(`GET → POST`)도 반영했습니다.
`route_permissions`/`role_assignment_rules`는 현재 런타임 강제보다는 메타 동기화 기준으로 관리합니다.

## 2) 핵심 항목 상태

| 카테고리 | 상태 | 근거 파일 |
| :--- | :--- | :--- |
| 인증/세션 | ✅ 적용 | `apps/server/app/main.py`, `apps/server/app/routers/auth.py` |
| CSRF 검증 | ✅ 적용(세션 기반 write 요청), Bearer 요청 예외 처리 | `apps/server/app/dependencies.py`, `apps/server/app/routers/*` |
| Bearer API 인증 | ✅ 적용(`/mcp/*`) | `apps/server/app/routers/mcp.py`, `apps/server/app/routers/snippet_access.py` |
| Rate Limiting | ✅ 핵심 경로 적용 범위 확장(`tokens`/`teams`/`users PATCH`/`mcp`) | `apps/server/app/routers/*`, `apps/server/app/limiter.py` |
| CORS 정책 | ⚠️ 운영 환경 점검 필요 | `apps/server/app/main.py`, `apps/server/app/core/config.py` |
| Secret Key 보호 | ✅ production fail-fast | `apps/server/app/main.py`, `apps/server/app/core/config.py` |
| 라우트 권한 메타 동기화 | ⚠️ 메타 동기화 중심(`special_rules` 메서드 정합성 반영) | `apps/server/scripts/migrate_and_seed.py` |

## 3) 상세 메모

### 3.1 CSRF 및 인증 경로 분리

- `verify_csrf`는 안전 메서드(`GET/HEAD/OPTIONS/TRACE`)는 통과시키고, 그 외 메서드는 세션 토큰과 `X-CSRF-Token` 헤더 일치 여부를 검증합니다.
- Bearer Authorization 헤더가 있는 요청은 `verify_csrf`에서 예외 처리됩니다.
- CSRF 의존성은 `auth`, `terms`, `comments`, `daily_snippets`, `weekly_snippets`, `tokens`, `teams`, `users` 라우터에 적용되어 있습니다.
- `/mcp`(HTTP)는 CSRF 의존성을 두지 않고 Bearer 토큰 검증(`get_bearer_auth_or_401`)을 사용합니다.
- `/auth/tokens`는 Bearer 전용 API가 아니라 세션 사용자(`get_active_user`) + CSRF 검증 경로입니다.

### 3.2 Rate Limit 적용 범위

- 적용 예시(코드 확인):
  - `auth`: `/auth/google/login`, `/auth/me`
  - `terms`: `/terms`, `/consents`
  - `comments`: 생성/수정/삭제
  - `daily_snippets`: 생성/organize/feedback/수정/삭제
  - `weekly_snippets`: 생성/organize/feedback/수정/삭제
- 미적용/부분 적용 예시(코드 확인):
  - `users`: 개인 리그 `GET` (`PATCH`는 적용)
  - `achievements`, `leaderboards`
  - `auth` 일부: `/auth/google/callback`, `/auth/csrf`, `/auth/logout`
- 현재 limiter는 `Limiter(key_func=get_remote_address)`로 선언되어 있으며 라우트 데코레이터 적용 범위에 따라 실효가 결정됩니다.
- 이번 라운드 기준 core route인 `tokens`/`teams`/`users PATCH`/`mcp`는 rate limit 적용 대상으로 정합화되었습니다.

### 3.3 CORS / Host / 세션 쿠키

- CORS는 `CORS_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS` 환경값으로 설정되며 `allow_credentials=True`입니다.
- 기본 `CORS_ORIGINS`는 localhost 계열 + 특정 사설망 주소를 포함하므로 운영 배포 시 최소 allowlist 유지가 필요합니다.
- `TrustedHostMiddleware`는 `ALLOWED_HOSTS` 기반으로 동작합니다.

### 3.4 Secret Key 및 production guard

- `ENVIRONMENT=production`일 때 `SECRET_KEY`가 비어 있거나 기본값(`your-secret-key`)이면 애플리케이션 시작 시 예외로 중단됩니다.
- 세션 쿠키는 production에서 `https_only=True`, `same_site="lax"`로 설정됩니다.

### 3.5 라우트 권한 메타 동기화

- `migrate_and_seed.py`는 `app.routes`를 순회해 `route_permissions`를 동기화하고, `role_assignment_rules`를 시드합니다.
- `special_rules`는 실제 인증 라우트 메서드와 동일하게 `("/auth/logout", "POST")`로 정합화되어 있습니다.
- 현재 코드 기준으로 `route_permissions`/`role_assignment_rules`는 메타 동기화 관점에서 관리되며, 요청 처리 시 런타임 강제 경로는 별도 정책 확정이 필요합니다.

## 4) 권장 후속 조치

1. 라우트별 Rate limit 적용 매트릭스 유지(특히 `users GET`, `leaderboards`, `achievements`, `auth` 일부)
2. 인증 방식 문서화 분리: 세션+CSRF 경로와 Bearer 경로를 엔드포인트 단위로 명시
3. 운영 배포 체크리스트에 `SECRET_KEY`, `CORS_ORIGINS`, `ALLOWED_HOSTS` 검증 절차 고정
4. `route_permissions`/`role_assignment_rules`를 메타 동기화 기준으로 유지하고 런타임 강제 정책은 별도 결정
5. 보안 회귀 테스트(`apps/server/tests/test_csrf_dependency.py`, 인증/약관/토큰 관련 테스트) 주기 실행

## 5) 점검 체크리스트

- [ ] `ENVIRONMENT=production`에서 `SECRET_KEY`가 기본값(`your-secret-key`)/공백이 아닌지 확인
- [ ] 신규/변경된 세션 기반 write API(POST/PUT/PATCH/DELETE)에 `Depends(verify_csrf)` 적용 여부 확인
- [ ] 세션 기반 write API 클라이언트가 `/auth/csrf`로 발급받은 `X-CSRF-Token`을 전송하는지 확인
- [ ] Bearer 기반 API(`/mcp`)에 `get_bearer_auth_or_401`(또는 래퍼 의존성) 적용 여부 확인
- [ ] `/auth/tokens`(세션+CSRF)와 `/mcp`(Bearer)의 인증 모델이 혼동 없이 분리 문서화되어 있는지 확인
- [ ] 신규 엔드포인트마다 `@limiter.limit` 적용 여부를 의도적으로 결정하고 문서에 기록 (`tokens`/`teams`/`users PATCH`/`mcp` 기준 유지)
- [ ] 라우트/권한 변경 시 `migrate_and_seed.py` 기반 `route_permissions`/`role_assignment_rules` 메타 동기화 절차 포함 여부 확인
- [ ] `/auth/logout` special rule 메서드가 `POST`로 유지되는지 점검

## 6) 배포 전 1분 점검 체크리스트 (2026-02 업데이트)

### 6.1 환경 변수/운영 설정 (20초)

- [ ] `ENVIRONMENT=production`에서 `SECRET_KEY`가 기본값(`your-secret-key`) 또는 공백이 아닌지 확인
- [ ] 신규 rate limit 키가 모두 설정되었는지 확인
  - [ ] `TOKENS_LIST_LIMIT`
  - [ ] `TOKENS_WRITE_LIMIT`
  - [ ] `TEAMS_WRITE_LIMIT`
  - [ ] `USERS_LEAGUE_UPDATE_LIMIT`
  - [ ] `MCP_HTTP_STREAM_LIMIT`
  - [ ] `MCP_HTTP_MESSAGES_LIMIT`
- [ ] `ALLOWED_HOSTS`, `CORS_ORIGINS`가 운영 도메인 기준 최소 allowlist로 설정되어 있는지 확인

### 6.2 보안 정책 정합성 (20초)

- [ ] `/auth/logout` special rule 메서드가 `POST`로 반영/유지되는지 확인
- [ ] core route rate limit 적용 상태 확인
  - [ ] `GET /auth/tokens` -> `TOKENS_LIST_LIMIT`
  - [ ] `POST|DELETE /auth/tokens` -> `TOKENS_WRITE_LIMIT`
  - [ ] `POST|PATCH /teams*` write 경로 -> `TEAMS_WRITE_LIMIT` (`GET /teams/me` 제외)
  - [ ] `PATCH /users/me/league` -> `USERS_LEAGUE_UPDATE_LIMIT`
  - [ ] `GET /mcp` -> `MCP_HTTP_STREAM_LIMIT`, `POST|DELETE /mcp` -> `MCP_HTTP_MESSAGES_LIMIT`
- [ ] `route_permissions`/`role_assignment_rules`가 이번 라운드 정책대로 메타 정합성 중심으로 관리되는지 확인

### 6.3 배포 직전 스모크 검증 (20초)

- [ ] 핵심 보안/회귀 테스트 재실행
  - [ ] `tests/test_rate_limit_regression.py`
  - [ ] `tests/test_seed_integrity_smoke.py`
  - [ ] `tests/test_auth_terms_tokens_endpoints.py`
  - [ ] `tests/test_teams_users_comments_endpoints.py`
  - [ ] `tests/test_mcp_auth.py`
  - [ ] `tests/test_mcp_http_flow.py`
- [ ] 배포 직후 모니터링 항목 확인
  - [ ] 429 비율 급증 여부
  - [ ] `/mcp/*` 오류율
  - [ ] auth/tokens 실패율