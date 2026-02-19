# QA 테스트 결과 (Snippet High) — 2026-02-19

## 1) 테스트 목적
Daily/Weekly Snippet의 핵심 고위험 시나리오(@high)를 자동화 검증하고, 결과를 체크리스트 ID 기준으로 추적 가능하게 기록합니다.

## 2) 실행 범위
- 대상 스펙
  - `apps/client/tests/e2e/snippets/daily.high.spec.ts`
  - `apps/client/tests/e2e/snippets/weekly.high.spec.ts`
- 포함 항목
  - Daily/Weekly 기본 작성/수정/재조회
  - 과거 항목 readOnly UI + 저장 차단(403)
  - 컷오프 경계 전후 편집 가능 여부 전환

## 3) 실행 명령
```bash
npm --prefix "/Users/namjookim/projects/gcs-mono/apps/client" run test:e2e:high
```

## 4) 실행 결과 요약
- 결과: **6 passed (7.9s)**

| 체크리스트 ID | 시나리오 | 결과 | 스크린샷 |
|---|---|---|---|
| CHK-DAILY-001 | Daily 기본 작성/수정/재조회 일치 | PASS | `./qa-artifacts/2026-02-19/chk-daily-001.png` |
| CHK-DAILY-002 | 과거 Daily readOnly + 저장 시 403 | PASS | `./qa-artifacts/2026-02-19/chk-daily-002.png` |
| CHK-DAILY-003 | 08:59/09:00 컷오프 전후 편집 가능 날짜 전환 | PASS | `./qa-artifacts/2026-02-19/chk-daily-003.png` |
| CHK-WEEKLY-001 | Weekly 기본 작성/수정/재조회 일치 | PASS | `./qa-artifacts/2026-02-19/chk-weekly-001.png` |
| CHK-WEEKLY-002 | 과거 Weekly readOnly + 저장 시 403 | PASS | `./qa-artifacts/2026-02-19/chk-weekly-002.png` |
| CHK-WEEKLY-003 | 월요일 09:00 전후 편집 가능 주차 전환 | PASS | `./qa-artifacts/2026-02-19/chk-weekly-003.png` |

## 5) 증빙 스크린샷

### CHK-DAILY-001
![CHK-DAILY-001](./qa-artifacts/2026-02-19/chk-daily-001.png)

### CHK-DAILY-002
![CHK-DAILY-002](./qa-artifacts/2026-02-19/chk-daily-002.png)

### CHK-DAILY-003
![CHK-DAILY-003](./qa-artifacts/2026-02-19/chk-daily-003.png)

### CHK-WEEKLY-001
![CHK-WEEKLY-001](./qa-artifacts/2026-02-19/chk-weekly-001.png)

### CHK-WEEKLY-002
![CHK-WEEKLY-002](./qa-artifacts/2026-02-19/chk-weekly-002.png)

### CHK-WEEKLY-003
![CHK-WEEKLY-003](./qa-artifacts/2026-02-19/chk-weekly-003.png)

## 6) 비고
- 본 문서는 High 우선순위 시나리오만 기록합니다.
- 체크리스트 ID를 테스트 제목에 포함해 실패 시 즉시 역추적 가능하게 유지합니다.
