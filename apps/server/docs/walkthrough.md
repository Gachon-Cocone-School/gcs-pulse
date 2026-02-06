# 통합 검증 가이드 - RBAC 및 역할 자동 할당 시스템

이 가이드는 `gcs-auth` 프로젝트에 구현된 역할 기반 접근 제어(RBAC) 및 자동 역할 할당 시스템을 검증하는 방법을 설명합니다.

## 1. 사전 요구 사항

- PostgreSQL 데이터베이스 실행 중
- `.env` 파일에 `DATABASE_URL`, `SECRET_KEY`, Google OAuth 설정 완료
- 최신 의존성 설치 (`pip install -r requirements.txt`)

## 2. 데이터베이스 마이그레이션 및 데이터 초기화

시스템 작동을 위해 필요한 테이블을 생성하고 초기 권한/규칙 데이터를 설정해야 합니다.

```bash
# 1. 기본 테이블 생성 및 초기 권한 시딩 (Public/Admin 라우트)
python3 scripts/migrate_and_seed.py

# 2. 역할 자동 할당 규칙 테이블 생성 및 예시 규칙 시딩
python3 scripts/migrate_role_rules.py
```

## 3. 완전 자동 검증 (E2E 테스트)

모든 권한 로직과 로그인 흐름을 한 번에 검증하려면 E2E 테스트 스크립트를 실행하세요.

```bash
python3 tests/test_e2e.py
```

**테스트 내용:**

- 공개 라우트(`/docs`) 접근 확인
- OAuth 콜백 시 이메일 패턴/리스트에 따른 **자동 역할 부여** 확인
- 역할별 서비스 접근 제한(**RBAC**) 집행 확인
- 등록되지 않은 경로 차단(**Default DISALLOW**) 확인

---

## 4. 단계별 수동 검증 (Swagger UI)

[http://localhost:8000/docs](http://localhost:8000/docs)에서 직접 API를 테스트할 수 있습니다.

### A. 역할 자동 할당 규칙 관리 (Admin 전용)

1. **규칙 조회**: `GET /admin/role-rules`
   - 시딩된 `@gachon.ac.kr` 패턴 규칙과 관리자 이메일 리스트 규칙이 나오는지 확인합니다.
2. **규칙 추가**: `POST /admin/role-rules`
   ```json
   {
     "rule_type": "email_pattern",
     "rule_value": { "pattern": "%@staff.example.com" },
     "assigned_role": "staff",
     "priority": 5,
     "is_active": true
   }
   ```

### B. 라우트 권한 관리 (Admin 전용)

1. **권한 목록**: `GET /admin/permissions`
   - 현재 등록된 모든 API 경로와 허용된 역할 리스트를 확인합니다.
2. **권한 수정**: `PUT /admin/permissions/{id}`
   - 특정 경로(예: `/protected`)에 접근 가능한 역할을 변경해 볼 수 있습니다.

### C. 로그인 및 역할 확인

1. **Google 로그인**: `/auth/google/login` 진행
2. **정보 조회**: `GET /auth/me`
   - 응답의 `user.roles` 배열에 본인의 이메일 조건에 맞는 역할이 포함되어 있는지 확인합니다.
   - 예: 가천대 이메일인 경우 `["user", "가천대학교"]`

### D. 접근 제어(RBAC) 확인

1. **미인가 접근**: `admin` 역할이 없는 계정으로 로그인한 상태에서 `GET /admin/permissions` 호출 시 `403 Forbidden`이 발생하는지 확인합니다.
2. **Default Deny**: `route_permissions` 테이블에 등록되지 않은 임의의 경로 접근 시 `403 Forbidden ("No permission rule found")`이 발생하는지 확인합니다.

## 5. 주요 파일 위치

- **권한 검사 의존성**: `app/dependencies.py` (`check_route_permissions`)
- **역할 할당 로직**: `app/crud.py` (`apply_role_rules`)
- **관리자 라우터**: `app/routers/admin.py`
- **검증 테스트**: `tests/test_e2e.py`, `tests/verify_rbac.py`
