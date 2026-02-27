# 백엔드 보안 감사 요약 (코드 정합화 업데이트)

- 최신 업데이트: 2026-02-23
- 대상 범위: `apps/server` (FastAPI)
- 역할: **백엔드 관점 요약 문서**
- 기준 문서: 상세 상태/우선순위/체크리스트는 `security-report-2026-02-21.md`를 단일 소스로 참조

---

## 1) 요약

이 문서는 백엔드 보안 상태를 요약합니다. 이전 버전의 “완료” 단정 표현 중 코드와 불일치하는 항목을 최신 코드 기준으로 조정했습니다.

- RBAC 관련 데이터 모델은 존재하나, 앱 전역 강제(enforcement) 완료로 단정할 수 없음
- CSRF는 세션 보안 속성 일부는 적용되어 있으나, 토큰 검증 체계는 미도입
- Rate limit은 일부 라우트에 적용되었지만 모든 write/high-cost 경로를 포괄하지 않음

---

## 2) 핵심 항목 상태 (백엔드)

| 카테고리 | 상태 | 코드 근거 |
| :--- | :--- | :--- |
| **RBAC (접근 제어)** | ⚠️ **부분 적용** | 모델 존재: `apps/server/app/models.py:71-80`; 전역 enforcement 미확인: `apps/server/app/main.py:83-95`, `apps/server/app/dependencies.py:11-57` |
| **Rate Limiting** | ⚠️ **부분 적용** | 적용 예: `apps/server/app/routers/comments.py:21,106,126`, `apps/server/app/routers/daily_snippets.py:212,233,337,366`; 미적용 예: `apps/server/app/routers/tokens.py:24,42`, `apps/server/app/routers/teams.py:48,82,111,138,161`, `apps/server/app/routers/users.py:34`, `apps/server/app/routers/mcp.py:121` |
| **CSRF & Session** | ⚠️ **부분 적용** | 세션/쿠키 설정: `apps/server/app/main.py:67-72`; 로그아웃 POST 전환: `apps/server/app/routers/auth.py:75-78`; CSRF 토큰 검증 부재(관련 dependency): `apps/server/app/dependencies.py:12-17` |
| **CORS** | ⚠️ **리스크 잔존** | `allow_credentials=True` + wildcard: `apps/server/app/main.py:75-80` |
| **운영 비밀키 관리** | ✅ **강화됨** | 운영 `SECRET_KEY` fail-fast: `apps/server/app/main.py:53-60,66` |
| **예외/로그 정보노출** | ⚠️ **잔존** | 예외 원문 반환: `apps/server/app/main.py:47`; DB URL 출력: `apps/server/app/main.py:27` |
| **인증 없는 AI 라우트 노출** | ℹ️ **현재 N/A(미노출)** | 라우트 정의는 있으나 미마운트: `apps/server/app/routers/ai.py:9,23`, `apps/server/app/main.py:83-95` |

---

## 3) 보완 메모

### 3.1 RBAC
- `route_permissions`/`role_assignment_rules` 데이터 구조는 존재합니다.
- 다만 현재 앱 라우터 등록부(`include_router`)와 공통 dependency에서 전역 권한 강제 코드가 확인되지 않아, “전역 Default Deny 완료”로 표현하면 과장됩니다.

### 3.2 CSRF
- 세션 쿠키 보안 속성(`same_site`, `https_only`)은 유효합니다.
- 그러나 상태변경 요청에 대해 CSRF 토큰 검증 흐름이 코드상 확인되지 않아 “완료”로 볼 수 없습니다.

### 3.3 Rate Limit
- 스니펫/댓글/일부 인증 라우트엔 limiter가 적용되어 있습니다.
- 토큰/팀/사용자 일부 변경/MCP 메시지 등은 미적용 경로가 존재합니다.

---

## 4) 권장 후속 조치 (백엔드 관점)

1. CSRF 토큰 검증 도입 및 상태변경 API 일괄 적용
2. CORS `allow_methods`/`allow_headers` 최소권한 allowlist 적용
3. 서버 예외/로그 민감정보 노출 제거 (`str(exc)`, DB URL 출력)
4. RBAC 전역 enforcement 전략 확정 후 코드/문서 동시 갱신
5. 미적용 write/high-cost API rate limit 확대

---

## 5) 문서 운영 원칙

- 본 문서는 **백엔드 요약본**입니다.
- 상세 finding 분류(`Fixed / Still Open / Regressed / N/A`), 우선순위(P0/P1/P2), 재점검 체크리스트의 기준값은 반드시 아래 메인 보고서를 따릅니다.
  - `security-report-2026-02-21.md`
