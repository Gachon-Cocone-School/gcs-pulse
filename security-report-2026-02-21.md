# GCS-MONO 서버/클라이언트 보안 점검 보고서

- 최초 점검일: 2026-02-21
- 최신 업데이트: 2026-02-23
- 대상: `apps/server` (FastAPI), `apps/client` (Next.js)
- 방식: 정적 코드 분석 + 의존성 취약점 스캔
  - Client: `npm audit --omit=dev` (`apps/client`) → **found 0 vulnerabilities**
  - Server: `apps/server/venv/bin/pip-audit -r requirements.txt` → **No known vulnerabilities found**
- 상태 분류: `Fixed / Still Open / Regressed / N/A`
- 한계: 동적 침투 테스트(런타임 공격, 인프라/WAF, 네트워크 ACL)는 본 범위 밖

---

## 1) Executive Summary

### 전체 요약 (최신 코드 기준)
- **Fixed 4건 / Still Open 9건 / Regressed 0건 / N/A 1건**
- 직전 보고서 대비 확인된 주요 개선:
  1. Next 의존성 취약점 해소(스캔 기준)
  2. 클라이언트 CSP/보안 헤더 적용
  3. 로그아웃 엔드포인트 `GET -> POST` 전환
  4. 운영 환경 `SECRET_KEY` fail-fast 적용

### 즉시 우선 조치(요약)
1. CSRF 토큰 검증 체계 도입 및 상태변경 API 전면 적용
2. 서버 CORS(`credentials=True` + wildcard) 최소권한화
3. 서버 예외/로그 민감정보 노출 제거(`str(exc)`, DB URL 출력)

---

## 2) 상세 Findings

## 2.1 상태표 (증빙 고정)

| ID | 항목 | 심각도 | 상태 | 근거 (`file_path:line`) |
|---|---|---|---|---|
| H-01 | Next.js 취약점 이슈 | High | **Fixed** | `apps/client/package.json:40` |
| H-02 | 운영 `SECRET_KEY` 기본값 방지 | High | **Fixed** | `apps/server/app/main.py:53-60`, `apps/server/app/main.py:66`, `apps/server/app/core/config.py:11` |
| M-01 | 예외 원문 응답 노출 잔존 | Medium | **Still Open** | `apps/server/app/main.py:47` |
| M-02 | Raw HTML 렌더 경로 사용(`useRehypeRaw`) | Medium | **Still Open** | `apps/client/src/components/views/MarkdownRenderer.tsx:20`, `apps/client/src/components/views/SnippetForm.tsx:213-217` |
| M-03a | 로그아웃 상태변경 메서드 | Medium | **Fixed** | `apps/server/app/routers/auth.py:75-78`, `apps/client/src/context/auth-context.tsx:31` |
| M-03b | CSRF 토큰 검증 부재 | Medium | **Still Open** | `apps/server/app/main.py:67-72`, `apps/server/app/dependencies.py:12-17`, `apps/client/src/lib/api.ts:88-92` |
| M-04a | 클라이언트 보안 헤더/CSP | Medium | **Fixed** | `apps/client/next.config.mjs:4-51` |
| M-04b | 서버 보안 헤더 미적용 | Medium | **Still Open** | `apps/server/app/main.py:62-81` |
| M-05 | 일부 write/high-cost API rate limit 미적용 | Medium | **Still Open** | `apps/server/app/routers/tokens.py:24,42`, `apps/server/app/routers/teams.py:48,82,111,138,161`, `apps/server/app/routers/users.py:34`, `apps/server/app/routers/mcp.py:121` |
| M-06 | CORS wildcard + credentials 조합 | Medium | **Still Open** | `apps/server/app/main.py:75-80` |
| M-07 | RBAC 모델은 있으나 전역 enforcement 미확인 | Medium | **Still Open** | `apps/server/app/models.py:71-80`, `apps/server/app/main.py:83-95`, `apps/server/app/dependencies.py:11-57` |
| L-01 | 시작 로그에 DB URL 출력 | Low | **Still Open** | `apps/server/app/main.py:27` |
| L-02 | 개발 환경 외부 스크립트 로드(SRI 없음) | Low | **Still Open** | `apps/client/src/app/layout.tsx:33-42` |
| L-03 | 인증 없는 AI 라우트 코드 존재(미마운트) | Low | **N/A** | `apps/server/app/routers/ai.py:9,23`, `apps/server/app/main.py:83-95` |

## 2.2 Fixed

### H-01. Next.js 취약점 이슈
- **상태:** Fixed
- **근거:** `apps/client/package.json:40` (`next: ^16.1.6`)
- **검증:** `npm audit --omit=dev` 결과 `found 0 vulnerabilities`

### H-02. 운영 `SECRET_KEY` 기본값 방지
- **상태:** Fixed
- **근거:**
  - 운영에서 기본값/빈값이면 예외 발생: `apps/server/app/main.py:53-60`
  - 미들웨어 적용 전 검증 호출: `apps/server/app/main.py:66`
  - 기본값 정의는 존재하나 운영 시 fail-fast로 차단: `apps/server/app/core/config.py:11`

### M-03a. 로그아웃 상태변경 메서드 개선
- **상태:** Fixed
- **근거:**
  - 서버 로그아웃이 `POST`: `apps/server/app/routers/auth.py:75-78`
  - 클라이언트도 `POST /auth/logout` 호출: `apps/client/src/context/auth-context.tsx:31`

### M-04a. 클라이언트 보안 헤더/CSP 적용
- **상태:** Fixed
- **근거:**
  - CSP 및 주요 보안 헤더 정의/적용: `apps/client/next.config.mjs:4-51`

## 2.3 Still Open

### M-01. 예외 원문 응답 노출 잔존
- **근거:** `apps/server/app/main.py:47` (`{"detail": str(exc)}`)
- **리스크:** 내부 예외 문자열 노출로 정보수집 단서 제공 가능

### M-03b. CSRF 토큰 검증 부재
- **근거:**
  - 세션 쿠키 기반 인증: `apps/server/app/main.py:67-72`
  - 인증 의존성은 세션 사용자 확인 위주: `apps/server/app/dependencies.py:12-17`
  - 클라이언트는 `credentials: 'include'` 사용: `apps/client/src/lib/api.ts:88-92`
- **리스크:** 상태 변경 요청에 대한 명시적 CSRF 토큰 검증 부재

### M-04b. 서버 보안 헤더 미적용
- **근거:** `apps/server/app/main.py:62-81` (TrustedHost/Session/CORS만 구성, 보안 헤더 설정 부재)
- **리스크:** XSS/클릭재킹/스니핑 대응력 저하

### M-05. 일부 write/high-cost API rate limit 미적용
- **근거(미적용 예):**
  - 토큰 생성/삭제: `apps/server/app/routers/tokens.py:24,42`
  - 팀 생성/가입/이탈/수정: `apps/server/app/routers/teams.py:48,82,111,138,161`
  - 사용자 리그 수정: `apps/server/app/routers/users.py:34`
  - MCP 메시지 POST: `apps/server/app/routers/mcp.py:121`
- **참고(적용 예):**
  - 스니펫/댓글 일부 쓰기 라우트는 limiter 적용됨 (`daily_snippets.py`, `weekly_snippets.py`, `comments.py`)

### M-06. CORS wildcard + credentials 조합
- **근거:** `apps/server/app/main.py:75-80`
  - `allow_credentials=True`
  - `allow_methods=["*"]`
  - `allow_headers=["*"]`
- **리스크:** origin 운영 통제가 약해질 경우 공격면 확대

### M-07. RBAC 전역 enforcement 미확인
- **근거:**
  - RBAC 테이블 모델은 존재: `apps/server/app/models.py:71-80`
  - 앱 전역 include_router에서 RBAC 전역 dependency 미확인: `apps/server/app/main.py:83-95`
  - 공통 dependency 파일에 RBAC enforcement 함수 미확인: `apps/server/app/dependencies.py:11-57`
- **리스크:** 문서상 기대와 실제 런타임 권한 통제 수준 불일치 가능

### L-01. 시작 로그에 DB URL 출력
- **근거:** `apps/server/app/main.py:27`
- **리스크:** 로그 경유 민감정보 노출 가능

### L-02. 개발 환경 외부 스크립트 로드(SRI 없음)
- **근거:** `apps/client/src/app/layout.tsx:33-42`
- **리스크:** 공급망/개발환경 공격면 증가

### M-02. Raw HTML 렌더 경로 사용(`useRehypeRaw`)
- **근거:**
  - Raw HTML 파싱 플러그인 활성 경로: `apps/client/src/components/views/MarkdownRenderer.tsx:20`
  - 실제 사용 지점: `apps/client/src/components/views/SnippetForm.tsx:213-217`
- **리스크:** 현재 `rehype-sanitize`가 같이 적용되더라도, raw HTML 허용 경로 자체는 별도 정책 검증 필요

## 2.4 N/A

### L-03. 인증 없는 AI 라우트 코드 존재(미마운트)
- **상태:** N/A (현재 런타임 노출 없음)
- **근거:**
  - 라우트 정의: `apps/server/app/routers/ai.py:9,23`
  - 앱 include 목록에는 미포함: `apps/server/app/main.py:83-95`

## 2.5 Regressed

- 이번 점검 범위에서 **Regressed 항목 없음**.

---

## 3) Positive Findings (유지 권장)

1. API 토큰 원문 미저장(해시 저장)
   - 근거: `apps/server/app/crud.py:296-321`
2. 세션 쿠키 기본 보안 속성 적용
   - 근거: `apps/server/app/main.py:67-72`
3. 의존성 스캔 결과(현재 시점) 치명 취약점 미탐지
   - Client: `npm audit --omit=dev` 결과 0건
   - Server: `apps/server/venv/bin/pip-audit -r requirements.txt` 결과 0건

---

## 4) 우선순위 조치 계획 (권장)

### P0 (즉시)
1. CSRF 토큰(또는 double-submit cookie) 도입 및 상태변경 API 전면 검증
2. 서버 예외/로그 민감정보 노출 제거 (`apps/server/app/main.py:47`, `apps/server/app/main.py:27`)
3. CORS 최소권한화 (`allow_methods`, `allow_headers` 명시 allowlist)

### P1 (단기)
1. RBAC 전역 enforcement 설계/적용 및 문서 동기화
2. 서버 보안 헤더(HSTS, XFO, XCTO, Referrer-Policy, CSP) 적용
3. rate limit 미적용 write/high-cost 엔드포인트 보강 (`tokens/teams/users/mcp`)

### P2 (중기)
1. `useRehypeRaw` 경로 정책 재검토(허용 범위 축소/스키마 강화)
2. 개발 환경 외부 스크립트 로딩 축소(고정 버전/SRI 또는 제거)
3. 문서-코드 정합성 자동 점검(릴리즈 체크리스트화)

---

## 5) 재점검 체크리스트

### 이번 업데이트에서 완료
- [x] 상태 분류를 `Fixed / Still Open / Regressed / N/A`로 통일
- [x] 핵심 finding별 코드 근거를 `file_path:line`으로 재고정
- [x] Client 의존성 스캔 재확인 (`npm audit --omit=dev`)
- [x] Server 의존성 스캔 재확인 (`apps/server/venv/bin/pip-audit -r requirements.txt`)
- [x] `security_audit.md`와 상충되는 완료 문구 정리 계획 반영

### 후속 작업에서 확인 필요
- [ ] CSRF 토큰 검증 도입 후 상태변경 API 회귀 점검
- [ ] CORS allowlist 축소 후 프론트 연동 회귀 점검
- [ ] 서버 보안 헤더 적용 후 실제 응답 헤더 확인
- [ ] RBAC 전역 enforcement 적용 후 권한 테스트(허용/거부) 검증
- [ ] 미적용 write/high-cost API rate limit 적용 후 임계치/오탐 점검
- [ ] raw HTML 렌더 정책 변경 후 XSS 회귀 테스트

---

## 부록) 주요 근거 파일

- 서버
  - `apps/server/app/main.py`
  - `apps/server/app/core/config.py`
  - `apps/server/app/dependencies.py`
  - `apps/server/app/models.py`
  - `apps/server/app/routers/auth.py`
  - `apps/server/app/routers/tokens.py`
  - `apps/server/app/routers/teams.py`
  - `apps/server/app/routers/users.py`
  - `apps/server/app/routers/mcp.py`
- 클라이언트
  - `apps/client/package.json`
  - `apps/client/next.config.mjs`
  - `apps/client/src/lib/api.ts`
  - `apps/client/src/context/auth-context.tsx`
  - `apps/client/src/components/views/MarkdownRenderer.tsx`
  - `apps/client/src/components/views/SnippetForm.tsx`
  - `apps/client/src/app/layout.tsx`
