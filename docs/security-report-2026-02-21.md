# GCS-MONO 서버/클라이언트 보안 점검 보고서

- 점검일: 2026-02-21
- 대상: `apps/server` (FastAPI), `apps/client` (Next.js)
- 방식: 정적 코드 분석 + 의존성 취약점 스캔
  - Client: `npm audit --omit=dev`
  - Server: `pip-audit`
- 한계: 동적 침투 테스트(실행 중 런타임 공격/인프라 WAF/네트워크 ACL)는 본 범위 밖

---

## 1) Executive Summary

### 전체 요약
- **High 2건**, **Medium 6건**, **Low 4건**, **Info 3건**
- 즉시 우선 조치 필요:
  1. `next` 버전 취약점 패치 (DoS 포함)
  2. `SECRET_KEY` 기본값 사용 방지(운영 강제)
  3. 예외 메시지 원문 노출 제거

### 핵심 위험
- 의존성(Next.js) 고위험 취약점 존재
- 세션 키 기본값 오사용 시 세션 위조 위험
- 일부 API 응답에서 내부 예외 문자열 노출
- 클라이언트 마크다운 렌더링 경로에서 raw HTML 허용(`rehypeRaw`) 사용

---

## 2) 상세 Findings

## High

### H-01. Next.js 취약 버전 사용 (직접 의존성)
- **심각도:** High
- **근거:** `apps/client/package.json:40` (`"next": "^16.0.7"`)
- **스캔 결과:** `npm audit --omit=dev`에서 `next` 고위험/중위험 advisories 다수 탐지
  - 예: DoS 관련 GHSA (`GHSA-mwv6-3258-q52c`, `GHSA-h25m-26qc-wcjf` 등)
- **위험성:** 공개된 취약점 악용 시 서비스 가용성 저하(DoS), 정보 노출 가능성 증가
- **권고:**
  1. Next.js를 취약점 fix 범위 이상으로 즉시 업그레이드
  2. 업그레이드 후 빌드/회귀 테스트 + SSR/RSC 경로 점검

### H-02. 세션 서명키 기본값 존재 (`SECRET_KEY`)
- **심각도:** High (환경 오구성 시)
- **근거:**
  - `apps/server/app/core/config.py:11` (`SECRET_KEY = "your-secret-key"`)
  - `apps/server/app/main.py:56-61` (`SessionMiddleware(secret_key=settings.SECRET_KEY)`)
- **위험성:** 운영에서 기본값 사용 시 세션 위조 가능성 증가(인증 우회/권한 탈취로 확장 가능)
- **권고:**
  1. 운영 부팅 시 `SECRET_KEY` 미설정/기본값이면 프로세스 시작 실패(fail-fast)
  2. 비밀관리 시스템(Secret Manager/Vault)에서만 주입
  3. 키 회전 정책 수립

---

## Medium

### M-01. 내부 예외 원문을 클라이언트에 반환 (정보노출)
- **심각도:** Medium
- **근거:**
  - `apps/server/app/routers/auth.py:67-68` (`{"error": str(e)}`)
  - `apps/server/app/routers/snippet_utils.py:165`, `:200` (`detail=f"...{str(e)}"`)
  - `apps/server/app/routers/ai.py:25` (`detail=str(e)`) *(현재 미마운트 코드)*
- **위험성:** 내부 구현/외부 API 오류/인프라 단서가 노출되어 공격 표면 분석에 악용 가능
- **권고:**
  1. 사용자 응답은 일반화된 메시지로 통일
  2. 상세 스택/원문은 서버 로그(SIEM)로만 보존
  3. 에러 코드 체계(예: `ERR_AI_UPSTREAM`) 도입

### M-02. 마크다운 렌더링에서 raw HTML 허용 (`rehypeRaw`) 경로 존재
- **심각도:** Medium
- **근거:**
  - `apps/client/src/components/views/MarkdownRenderer.tsx:5,19,22`
  - `apps/client/src/components/views/SnippetForm.tsx:213-217` (`useRehypeRaw` 활성화)
- **위험성:** 신뢰되지 않은 입력이 해당 렌더러 경로로 들어오면 XSS 가능성 존재
- **권고:**
  1. 기본 정책을 sanitize-first로 변경 (`rehype-sanitize`)
  2. `rehypeRaw`는 엄격히 통제된 관리자/내부 데이터에만 제한
  3. CSP와 함께 이중 방어
- **오탐/맥락:** 현재는 주로 본인 작성 컨텐츠 미리보기 경로로 보이나, 재사용 시 위험 확대 가능

### M-03. CSRF 방어 약함 + 상태변경 로그아웃이 GET
- **심각도:** Medium
- **근거:**
  - 서버 로그아웃: `apps/server/app/routers/auth.py:71-74` (`GET /auth/logout`)
  - 클라이언트 호출: `apps/client/src/context/auth-context.tsx:31`
  - 세션 기반 인증: `apps/server/app/dependencies.py:13-17`
- **위험성:** 사용자 의도 없는 로그아웃 유도(CSRF) 가능성
- **권고:**
  1. 로그아웃을 `POST`로 변경
  2. CSRF 토큰(또는 double-submit cookie) 도입
  3. 민감 상태변경 API 전체에 CSRF 정책 일관 적용

### M-04. 보안 헤더/CSP 정책 부재
- **심각도:** Medium
- **근거:**
  - `apps/client/next.config.mjs:1-4` (헤더 설정 없음)
  - 서버에서도 HSTS/XFO/CSP/Referrer-Policy 적용 코드 부재 (`apps/server/app/main.py`)
- **위험성:** XSS/클릭재킹/컨텐츠 스니핑 대응력 저하
- **권고:**
  1. `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy` 적용
  2. 운영에서 `Strict-Transport-Security` 적용

### M-05. 쓰기/고비용 API에 rate limit 부재
- **심각도:** Medium
- **근거:**
  - limiter 적용은 일부 엔드포인트만 존재 (`apps/server/app/routers/auth.py:26,78`, `apps/server/app/routers/terms.py:18,24`)
  - 댓글/스니펫 작성·수정·AI organize 경로에는 limiter 데코레이터 미확인
- **위험성:** 스팸, 자원 고갈, 외부 AI 호출 비용 폭증 가능
- **권고:**
  1. 댓글/스니펫 쓰기/organize 엔드포인트에 사용자·IP 기반 제한 추가
  2. burst + sustained(예: `10/min`, `200/day`) 이중 정책

### M-06. Credential 포함 CORS에서 메서드/헤더 와일드카드 사용
- **심각도:** Medium
- **근거:** `apps/server/app/main.py:67-69`
  - `allow_credentials=True`
  - `allow_methods=["*"]`
  - `allow_headers=["*"]`
- **위험성:** 허용 origin 관리가 느슨해질 경우 공격면 확대
- **권고:**
  1. 메서드/헤더 allowlist 최소화
  2. 운영 환경별 origin 분리 및 엄격 검증

---

## Low

### L-01. 시작 로그에 DB URL 출력
- **심각도:** Low (로그 접근권한에 따라 상향 가능)
- **근거:** `apps/server/app/main.py:26-28`
- **위험성:** 로그 경유 민감정보 노출 가능
- **권고:** 민감값 마스킹 또는 출력 제거

### L-02. 개발 환경에서 외부 스크립트 직접 로드 (SRI 없음)
- **심각도:** Low
- **근거:** `apps/client/src/app/layout.tsx:23-32` (`//unpkg.com/...`)
- **위험성:** 공급망 리스크(특히 사내망/개발기기 공격 시)
- **권고:**
  1. 가능하면 로컬 번들/고정 버전 사용
  2. 필요 시 SRI + 엄격 CSP

### L-03. 문서/구현 불일치 (RBAC 전역 강제 주장 vs 실제 미적용)
- **심각도:** Low (거버넌스 리스크)
- **근거:**
  - RBAC/route permission 모델 존재: `apps/server/app/models.py:68-89`
  - 시드 스크립트 규칙 존재: `apps/server/scripts/migrate_and_seed.py:118-175`
  - 런타임 전역 enforcement 코드 미확인 (`app.main` 라우터 include에는 해당 dependency 부재)
- **위험성:** 운영자 오판(보안 체계가 적용된 것으로 착각)
- **권고:** 실제 적용 상태와 문서 동기화, 미적용 기능은 명시적으로 비활성 표기

### L-04. 인증 없는 AI 프록시 라우트 코드 존재(현재 미마운트)
- **심각도:** Low (현재 비활성)
- **근거:** `apps/server/app/routers/ai.py:19-26`, 미포함 `apps/server/app/main.py:73-79`
- **위험성:** 향후 실수로 include 시 무단 사용/비용 유발 위험
- **권고:**
  1. 라우트 파일에 명시적 주석/가드 추가
  2. include 시 반드시 인증·권한·rate limit 강제

---

## 3) Positive Findings (잘된 점)

1. **토큰 저장 안전성 양호**
   - 원문 토큰 DB 미저장, SHA-256 해시 저장
   - 근거: `apps/server/app/crud.py:296-321`

2. **세션 쿠키 기본 보안 속성 일부 적용**
   - `same_site="lax"`, production에서 `https_only=True`
   - 근거: `apps/server/app/main.py:56-61`

3. **ORM 사용 중심으로 SQLi 위험 낮음**
   - 주요 쿼리는 SQLAlchemy ORM 사용
   - 근거: `apps/server/app/crud.py` 전반

4. **서버 Python 의존성 스캔 결과 취약점 미탐지**
   - `pip-audit` 결과: known vulnerabilities 없음

---

## 4) 우선순위 조치 계획 (권장)

### P0 (즉시)
1. Next.js 버전 업데이트 및 재검증
2. `SECRET_KEY` 기본값 차단(fail-fast)
3. 예외 원문 노출 제거(표준 오류응답화)

### P1 (단기)
1. CSRF 방어 체계 도입 + `GET /auth/logout` -> `POST`
2. markdown raw HTML 렌더링 경로 sanitize 정책 적용
3. 댓글/스니펫/AI organize rate limit 적용

### P2 (중기)
1. 보안 헤더/CSP 전면 도입
2. RBAC 문서-구현 정합성 회복
3. 운영 로그 민감정보 마스킹 표준화

---

## 5) 재점검 체크리스트

- [ ] `next` 패치 버전 반영 후 `npm audit --omit=dev` 재실행
- [ ] 서버 에러 응답에서 내부 예외 문자열 제거 확인
- [ ] 로그아웃 메서드 변경 및 CSRF 검증
- [ ] markdown 렌더링 sanitize 정책 적용 검증
- [ ] 쓰기/AI 경로 rate limit 동작 검증
- [ ] CSP/보안 헤더 실제 응답 헤더 확인

---

## 부록) 근거 파일 목록

- 서버
  - `apps/server/app/main.py`
  - `apps/server/app/core/config.py`
  - `apps/server/app/dependencies.py`
  - `apps/server/app/routers/auth.py`
  - `apps/server/app/routers/terms.py`
  - `apps/server/app/routers/snippet_utils.py`
  - `apps/server/app/routers/daily_snippets.py`
  - `apps/server/app/routers/weekly_snippets.py`
  - `apps/server/app/routers/comments.py`
  - `apps/server/app/routers/ai.py`
  - `apps/server/app/crud.py`
  - `apps/server/app/models.py`
  - `apps/server/scripts/migrate_and_seed.py`

- 클라이언트
  - `apps/client/package.json`
  - `apps/client/next.config.mjs`
  - `apps/client/src/lib/api.ts`
  - `apps/client/src/context/auth-context.tsx`
  - `apps/client/src/components/views/MarkdownRenderer.tsx`
  - `apps/client/src/components/views/SnippetForm.tsx`
  - `apps/client/src/components/views/SnippetPreview.tsx`
  - `apps/client/src/app/layout.tsx`
