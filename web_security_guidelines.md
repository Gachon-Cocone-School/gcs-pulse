# Agentic Coding: Web Security Guidelines (v2.0)

이 문서는 웹 애플리케이션 개발 시 에이전트(AI)와 개발자가 반드시 검토하고 적용해야 할 핵심 보안 가이드라인입니다. 특히 `gcs-auth` 프로젝트에 적용된 고급 접근 제어 전략을 포함하고 있습니다.

---

## 🔒 1. 접근 제어 (Access Control & RBAC)
**목적:** 권한이 없는 사용자의 데이터 접근 및 기능 실행 방지 (OWASP Top 10 - Broken Access Control).

*   **체크리스트:**
    *   [x] **Default DISALLOW**: 모든 경로가 기본적으로 차단되어 있으며, 명시적으로 허용된 경우에만 접근 가능한가?
    *   [x] **중앙 집중식 권한 관리**: 코드 곳곳에 권한 체크가 흩어져 있지 않고, 전역 미들웨어(또는 의존성)에서 일괄 처리되는가?
    *   [x] **동적 권한 설정**: 소스 코드 수정 없이 데이터베이스 설정을 통해 실시간으로 권한을 변경할 수 있는가?
*   **구현 가이드:**
    *   FastAPI의 전역 의존성(`dependencies=[Depends(check_route_permissions)]`)을 활용하여 모든 API 호출 시 권한 테이블(`route_permissions`)을 조회함.

## 🤖 2. 자동 역할 할당 (Automated Role Assignment)
**목적:** 신원을 바탕으로 사용자에게 적절한 권한을 안전하고 자동으로 부여.

*   **체크리스트:**
    *   [x] 사용자의 이메일이 신뢰할 수 있는 공급자(예: Google)에 의해 검증되었는가?
    *   [x] 역할 부여 규칙이 패턴(Regex/Like) 및 화이트리스트로 관리되고 있는가?
    *   [x] 여러 규칙에 해당하는 경우 역할이 적절히 누적(Merge)되는가?
*   **구현 가이드:**
    *   OAuth 콜백 시점에 `apply_role_rules` 로직을 실행하여 이메일 도메인 또는 특정 리스트와 대조.

## 🧪 3. 보안 흐름 검증 (Security Verification)
**목적:** 복잡한 인증/인가 로직이 예상대로 작동하는지 지속적으로 확인.

*   **체크리스트:**
    *   [x] **OAuth 시뮬레이션**: 로그인 및 콜백 흐름을 테스트로 재현할 수 있는가?
    *   [x] **권한 위반 테스트**: 인가되지 않은 사용자의 접근이 정확히 `403 Forbidden`으로 차단되는가?
    *   [x] **Default Deny 테스트**: 설정되지 않은 경로에 대한 접근이 거부되는가?
*   **구현 가이드:**
    *   `tests/test_e2e.py`와 같은 통합 테스트 스크립트를 작성하여 배포 전 보안 체크 수행.

## 🛡️ 4. 기존 핵심 보안 체크리스트

### 4.1 요청 속도 제한 (Rate Limiting)
*   [x] 로그인, 약관 동의 등 민감한 엔드포인트에 `slowapi` 등의 제한이 있는가?

### 4.2 CORS & CSRF
*   [x] `allow_origins`가 구체적으로 한정되어 있는가?
*   [x] 쿠키 옵션이 보안적으로 안전한가? (`SameSite=Lax`, `HttpOnly`, `Secure`)

### 4.3 인젝션 방지 (Injection Prevention)
*   [x] 모든 DB 쿼리에 ORM(SQLAlchemy)을 사용하여 파라미터화된 쿼리를 수행하는가?

### 4.4 인프라 보안
*   [x] `TrustedHostMiddleware`를 사용하여 Host 헤더 변조를 방어하고 있는가?
*   [x] (권고) 배포 환경에서 WAF 및 DB 보안 그룹 설정을 검토했는가?

---
*Last Updated: 2025-12-31 by Agentic Coding Assistant*
