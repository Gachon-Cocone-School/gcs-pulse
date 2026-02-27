# 백엔드 보안 감사 요약

- 최신 업데이트: 2026-02-27
- 대상 범위: `apps/server` (FastAPI)
- 역할: 보안 상태를 코드 기준으로 요약한 문서

관련 문서:

- 백엔드 실행/환경: [`../apps/server/README.md`](../apps/server/README.md)
- DB 구조: [`./database.md`](./database.md)
- 성능 감사: [`./performance_audit.md`](./performance_audit.md)

## 1) 요약

현재 백엔드는 세션/CSRF/Rate limit/RBAC 관련 기반을 갖추고 있으나,
일부 항목은 라우트별 적용 범위 차이가 있어 “부분 적용” 상태입니다.

## 2) 핵심 항목 상태

| 카테고리 | 상태 | 근거 파일 |
| :--- | :--- | :--- |
| 인증/세션 | ✅ 적용 | `apps/server/app/routers/auth.py`, `apps/server/app/main.py` |
| CSRF 검증 | ✅ 적용(세션 기반 write 요청) | `apps/server/app/dependencies.py`, 라우터별 `Depends(verify_csrf)` |
| Rate Limiting | ⚠️ 부분 적용 | `apps/server/app/routers/*` (`@limiter.limit` 적용 범위 상이) |
| CORS 정책 | ⚠️ 운영 환경 점검 필요 | `apps/server/app/main.py`, `apps/server/app/core/config.py` |
| Secret Key 보호 | ✅ production fail-fast | `apps/server/app/main.py` |
| 라우트 권한 메타 동기화 | ✅ 스크립트 제공 | `apps/server/scripts/migrate_and_seed.py` |

## 3) 상세 메모

### 3.1 CSRF

- `verify_csrf`는 안전하지 않은 메서드(`POST/PUT/PATCH/DELETE` 등)에 대해 세션 토큰과 `X-CSRF-Token` 헤더를 비교합니다.
- Bearer 인증 요청은 CSRF 검증을 생략하도록 설계되어 있습니다.

### 3.2 Rate Limit

- 인증/약관/스니펫/댓글 중심으로 limiter가 적용되어 있습니다.
- 일부 엔드포인트는 적용되지 않았을 수 있으므로 운영 정책 기준 재점검이 필요합니다.

### 3.3 CORS

- CORS 값은 환경변수(`CORS_ORIGINS`, `CORS_ALLOW_METHODS`, `CORS_ALLOW_HEADERS`) 기반입니다.
- 운영 배포 시 실제 origin allowlist 최소화가 필요합니다.

## 4) 권장 후속 조치

1. 라우트별 Rate limit 커버리지 점검표 유지
2. 운영 CORS allowlist 정기 검토
3. 보안 회귀 테스트(`apps/server/tests`) 주기적 실행
4. 문서/코드 동시 업데이트(README + 감사 문서)

## 5) 점검 체크리스트

- [ ] `ENVIRONMENT=production`에서 `SECRET_KEY` 설정 확인
- [ ] CSRF가 필요한 세션 기반 write API 점검
- [ ] Bearer 기반 API 토큰 플로우 점검(`/auth/tokens`, `/mcp/*`)
- [ ] 신규 엔드포인트 추가 시 rate limit/보안 의존성 반영 여부 확인
