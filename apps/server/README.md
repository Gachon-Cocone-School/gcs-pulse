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

## 🤖 MCP 서버 연결 가이드 (Cursor 등)

이 서버는 **MCP(Model Context Protocol) over SSE**를 지원합니다.
MCP 클라이언트는 기존 API 토큰(Bearer)으로 인증해 연결할 수 있습니다.

### 1) API 토큰 준비

MCP 연결에는 `Authorization: Bearer <API_TOKEN>` 헤더가 필요합니다.
토큰은 `/auth/tokens` 엔드포인트(로그인 세션 필요)로 발급합니다.

예시 요청:
```bash
curl -X POST http://localhost:8000/auth/tokens \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: my-mcp-token" \
  -b "<로그인 세션 쿠키>" \
  -d '{"description":"Cursor MCP"}'
```

응답의 `token` 값은 **한 번만 노출**되므로 안전하게 보관하세요.

### 2) MCP 엔드포인트

- SSE 연결: `GET /mcp/sse`
- 메시지 전송: `POST /mcp/messages?session_id=...`

두 엔드포인트 모두 Bearer 인증이 필수입니다.

### 3) Cursor 등 MCP 클라이언트에 연결

클라이언트 설정에서 다음 값을 사용하세요.

- Transport: **SSE**
- SSE URL: `http://localhost:8000/mcp/sse`
- Header: `Authorization: Bearer <API_TOKEN>`

> 클라이언트 버전에 따라 항목명은 다를 수 있지만,
> 핵심은 **SSE URL + Authorization 헤더**를 정확히 넣는 것입니다.

### 4) 연결 점검 (수동 테스트)

1. SSE 연결 확인
```bash
curl -N http://localhost:8000/mcp/sse \
  -H "Accept: text/event-stream" \
  -H "Authorization: Bearer <API_TOKEN>"
```

정상이라면 `event: session` 이벤트로 `session_id`를 받습니다.

2. 메시지 전송 확인
```bash
curl -X POST "http://localhost:8000/mcp/messages?session_id=<SESSION_ID>" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_TOKEN>" \
  -d '{"jsonrpc":"2.0","id":1,"method":"ping"}'
```

### 5) 인증/권한 동작

- 토큰 누락/오류/유효하지 않은 토큰: `401`
- 다른 사용자의 `session_id`로 메시지 전송 시도: `403`

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
