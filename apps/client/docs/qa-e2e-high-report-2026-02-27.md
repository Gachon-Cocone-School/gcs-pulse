# E2E High QA Report (2026-02-27)

## 1) 실행 목적/범위
- 목적: `@high` E2E 체크리스트 전체(업적/설정/데일리 스니펫/위클리 스니펫/약관)의 안정성 검증
- 범위: `apps/client/tests/e2e/**/*high.spec.ts`
- 실행 환경:
  - Frontend: Next.js dev **webpack 모드** (`next dev --webpack`)
  - Backend: `uvicorn app.main:app --host 127.0.0.1 --port 8000`
  - Browser: Playwright Chromium (1 worker)

## 2) 실행 명령
```bash
# targeted 재검증 (기존 실패 3건)
npm --prefix "/Users/namjookim/projects/gcs-pulse/apps/client" run test:e2e -- --grep "CHK-SETTINGS-001|CHK-DAILY-004|CHK-WEEKLY-004"

# full high 실행
npm --prefix "/Users/namjookim/projects/gcs-pulse/apps/client" run test:e2e:high

# screenshot 산출 포함 full high 재실행
E2E_SCREENSHOT_MODE=on npm --prefix "/Users/namjookim/projects/gcs-pulse/apps/client" run test:e2e:high
```

## 3) PASS/FAIL 요약 표

### 전체 요약
| 항목 | 결과 |
|---|---|
| 총 케이스 | 24 |
| 실행됨 | 20 |
| PASS | 20 |
| FAIL | 0 |
| SKIP | 4 (업적 시드 조건 미충족 시 스킵 로직) |

### 체크리스트 상세
| Checklist ID | 결과 | 비고 |
|---|---|---|
| CHK-ACH-001 | SKIP | CI seed 업적 데이터 조건 미충족 시 스킵 |
| CHK-ACH-002 | SKIP | CI seed 업적 데이터 조건 미충족 시 스킵 |
| CHK-ACH-003 | SKIP | CI seed 업적 데이터 조건 미충족 시 스킵 |
| CHK-ACH-004 | SKIP | CI seed 업적 데이터 조건 미충족 시 스킵 |
| CHK-SETTINGS-001 | PASS | 팀 생성/리그저장/이름변경/탈퇴 정상 |
| CHK-SETTINGS-002 | PASS | 팀 미소속 개인 리그 저장 정상 |
| CHK-SETTINGS-003 | PASS | 팀 소속 시 개인 리그 변경 차단 정상 |
| CHK-SETTINGS-004 | PASS | 초대코드/복사 버튼 노출 정상 |
| CHK-DAILY-001 | PASS | Daily 작성/수정/재조회 일치 정상 |
| CHK-DAILY-002 | PASS | 과거 Daily readOnly + API 403 정상 |
| CHK-DAILY-003 | PASS | 08:59/09:00 컷오프 전환 정상 |
| CHK-DAILY-004 | PASS | 설정 발급 API key Daily API 사용 정상 |
| CHK-DAILY-005 | PASS | organize 적용 후 본문 반영 정상 |
| CHK-DAILY-006 | PASS | feedback API 성공 응답 정상 |
| CHK-WEEKLY-001 | PASS | Weekly 작성/수정/재조회 일치 정상 |
| CHK-WEEKLY-002 | PASS | 과거 Weekly readOnly + API 403 정상 |
| CHK-WEEKLY-003 | PASS | 월요일 09:00 전환 정상 |
| CHK-WEEKLY-004 | PASS | 설정 발급 API key Weekly API 사용 정상 |
| CHK-WEEKLY-005 | PASS | organize 적용 후 본문 반영 정상 |
| CHK-WEEKLY-006 | PASS | feedback API 성공 응답 정상 |
| CHK-TERMS-001 | PASS | 이용약관 기본 UI 정상 |
| CHK-TERMS-002 | PASS | 필수 미동의 시 제출 비활성 정상 |
| CHK-TERMS-003 | PASS | /terms API 대비 렌더링 일치 정상 |
| CHK-TERMS-004 | PASS | /terms, /consents API 응답 정상 |

## 4) 시나리오별 스크린샷(상대 경로)

- CHK-ACH-001: `./qa-artifacts/2026-02-27/CHK-ACH-001.png`
- CHK-ACH-002: `./qa-artifacts/2026-02-27/CHK-ACH-002.png`
- CHK-ACH-003: `./qa-artifacts/2026-02-27/CHK-ACH-003.png`
- CHK-ACH-004: `./qa-artifacts/2026-02-27/CHK-ACH-004.png`
- CHK-SETTINGS-001: `./qa-artifacts/2026-02-27/CHK-SETTINGS-001.png`
- CHK-SETTINGS-002: `./qa-artifacts/2026-02-27/CHK-SETTINGS-002.png`
- CHK-SETTINGS-003: `./qa-artifacts/2026-02-27/CHK-SETTINGS-003.png`
- CHK-SETTINGS-004: `./qa-artifacts/2026-02-27/CHK-SETTINGS-004.png`
- CHK-DAILY-001: `./qa-artifacts/2026-02-27/CHK-DAILY-001.png`
- CHK-DAILY-002: `./qa-artifacts/2026-02-27/CHK-DAILY-002.png`
- CHK-DAILY-003: `./qa-artifacts/2026-02-27/CHK-DAILY-003.png`
- CHK-DAILY-004: `./qa-artifacts/2026-02-27/CHK-DAILY-004.png`
- CHK-DAILY-005: `./qa-artifacts/2026-02-27/CHK-DAILY-005.png`
- CHK-DAILY-006: `./qa-artifacts/2026-02-27/CHK-DAILY-006.png`
- CHK-WEEKLY-001: `./qa-artifacts/2026-02-27/CHK-WEEKLY-001.png`
- CHK-WEEKLY-002: `./qa-artifacts/2026-02-27/CHK-WEEKLY-002.png`
- CHK-WEEKLY-003: `./qa-artifacts/2026-02-27/CHK-WEEKLY-003.png`
- CHK-WEEKLY-004: `./qa-artifacts/2026-02-27/CHK-WEEKLY-004.png`
- CHK-WEEKLY-005: `./qa-artifacts/2026-02-27/CHK-WEEKLY-005.png`
- CHK-WEEKLY-006: `./qa-artifacts/2026-02-27/CHK-WEEKLY-006.png`
- CHK-TERMS-001: `./qa-artifacts/2026-02-27/CHK-TERMS-001.png`
- CHK-TERMS-002: `./qa-artifacts/2026-02-27/CHK-TERMS-002.png`
- CHK-TERMS-003: `./qa-artifacts/2026-02-27/CHK-TERMS-003.png`
- CHK-TERMS-004: `./qa-artifacts/2026-02-27/CHK-TERMS-004.png`

## 5) 안정화 조치 메모
- 기존 실패 원인 중 핵심은 Next dev에서의 Turbopack 불안정 경로였고, 실행 환경을 `next dev --webpack`으로 고정했을 때 `CHK-SETTINGS-001`, `CHK-DAILY-004`, `CHK-WEEKLY-004`가 재현되지 않음.
- 추가로 snippet fixture 종료 시 `page.unrouteAll({ behavior: 'ignoreErrors' })`를 보장해 `/notifications/sse` 장기 연결로 인한 route callback 종료 race를 제거함.

## 6) 산출물 경로
- QA 문서: `apps/client/docs/qa-e2e-high-report-2026-02-27.md`
- 스크린샷 모음: `apps/client/docs/qa-artifacts/2026-02-27/`
- Playwright HTML 리포트 스냅샷: `apps/client/docs/qa-artifacts/2026-02-27/playwright-report/index.html`
