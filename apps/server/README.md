# GCS Auth Service

이 프로젝트는 Google OAuth 2.0을 기반으로 하는 안전한 인증, 세밀한 역할 기반 접근 제어(RBAC), 그리고 유연한 약관 동의 관리를 제공하는 백엔드 서비스입니다.

## 🚀 주요 기능

- **Google OAuth 2.0 인증**: 안전하고 간편한 소셜 로그인 및 세션 관리.
- **역할 기반 접근 제어 (RBAC)**:
  - **Default DISALLOW 정책**: 명시적으로 허용되지 않은 모든 경로는 기본적으로 차단됩니다.
  - **라우트별 동적 권한**: 데이터베이스를 통해 실시간으로 API 엔드포인트별 접근 권한(역할)을 관리합니다.
- **자동 역할 할당 규칙**:
  - 이메일 패턴(예: `@gachon.ac.kr`) 또는 특정 이메일 리스트를 기반으로 로그인 시 역할을 자동으로 부여합니다.
- **약관 동의 관리 (Terms of Service)**: 필수/선택 약관 관리 및 사용자 동의 이력 저장.
- **강력한 보안 기능**:
  - **Rate Limiting**: `slowapi`를 이용한 요청 속도 제한.
  - **CORS & CSRF**: 신뢰할 수 있는 출처 제한 및 안전한 쿠키 설정(`SameSite`, `Secure`, `HttpOnly`).
  - **SQL Injection 방지**: SQLAlchemy ORM을 통한 데이터 보안.

## 🛠️ 시작하기 (Getting Started)

### 사전 요구 사항 (Prerequisites)

- Python 3.11 이상
- PostgreSQL 데이터베이스

### 설치 및 실행

1.  **가상 환경 생성 및 활성화**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Windows: venv\Scripts\activate
    ```

2.  **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

3.  **환경 변수 설정 (`.env`)**
    ```env
    DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/dbname
    GOOGLE_CLIENT_ID=your_google_id
    GOOGLE_CLIENT_SECRET=your_google_secret
    SECRET_KEY=your_random_secret_key
    ```

4.  **데이터베이스 초기화 및 데이터 시딩**
    ```bash
    # 테이블 생성 및 초기 라우트 권한 설정
    python3 scripts/migrate_and_seed.py
    # 역할 자동 할당 규칙 설정
    python3 scripts/migrate_role_rules.py
    ```

5.  **서버 실행**
    ```bash
    uvicorn app.main:app --reload
    ```

## 🔒 보안 감사 현황

| 보안 항목 | 상태 | 비고 |
| :--- | :---: | :--- |
| **RBAC** | ✅ 구현됨 | Default DISALLOW 및 동적 권한 관리 적용 |
| **Rate Limiting** | ✅ 구현됨 | 주요 엔드포인트 속도 제한 적용 |
| **SQL Injection** | ✅ 보호됨 | SQLAlchemy ORM 전면 사용 |
| **CSRF & Session**| ✅ 완화됨 | `SameSite=Lax`, `Secure` 쿠키 적용 |
| **E2E Testing** | ✅ 검증됨 | 전체 인증/권한 흐름 자동 테스트 완료 |

## 📂 프로젝트 구조

```
gcs-auth/
├── app/
│   ├── core/           # 설정 및 보안 설정
│   ├── routers/        # API 엔드포인트 (Auth, Admin, Terms)
│   ├── crud.py         # DB CRUD 및 역할 할당 로직
│   ├── database.py     # DB 연결 및 세션 관리
│   ├── dependencies.py # 권한 검사 및 사용자 인증 의존성
│   ├── models.py       # SQL 모델 (User, RoleRule, RoutePermission)
│   └── schemas.py      # Pydantic 데이터 형상 정의
├── scripts/            # 마이그레이션 및 데이터 시딩 스크립트
├── tests/              # E2E 및 RBAC 통합 테스트
├── docs/               # 플레이북 및 보안 가이드라인
├── README.md           # 프로젝트 개요
└── walkthrough.md      # 상세 검증 가이드
```

---
详细한 검증 방법은 `walkthrough.md`를 참고하세요.
