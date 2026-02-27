# QA / E2E 테스트 문서화 컨벤션

이 문서는 현재 프로젝트의 QA 결과 정리 및 E2E 테스트 문서화 기준을 정의합니다.

## 1) 적용 범위

- `apps/client/tests/e2e/**` 기반 시나리오
- 특히 `@high` 태그 시나리오 중심의 회귀 확인
- PR 본문/릴리즈 노트에 첨부되는 QA 결과 문서

## 2) 기본 실행 원칙

1. 우선 `@high` 시나리오를 먼저 실행한다.
2. 필요한 경우 전체 E2E(`test:e2e`)를 추가 실행한다.
3. 결과 문서는 체크리스트 ID 단위로 정리한다.

기본 명령:

```bash
npm --workspace apps/client run test:e2e:high
```

전체 E2E:

```bash
npm --workspace apps/client run test:e2e
```

## 3) 문서/아티팩트 저장 위치

- QA 리포트: `apps/client/docs/`
- 스크린샷(고정 참조본): `apps/client/docs/qa-artifacts/<YYYY-MM-DD>/`

권장 파일명:

- 리포트: `qa-report-<YYYY-MM-DD>.md`
- 기능별 리포트: `qa-<feature>-<YYYY-MM-DD>.md`

예시:

- `apps/client/docs/qa-report-2026-02-27.md`
- `apps/client/docs/qa-artifacts/2026-02-27/CHK-DAILY-001-home.png`

## 4) 리포트 필수 구성 (반드시 포함)

리포트에는 아래 4가지를 반드시 포함한다.

1. 실행 목적/범위
2. 실행 명령
3. PASS/FAIL 요약 표
4. 시나리오별 스크린샷 (상대 경로)

### 4-1) 권장 템플릿

```md
## 목적/범위
- ...

## 실행 명령
- `npm --workspace apps/client run test:e2e:high`

## 결과 요약
| ID | 시나리오 | 결과 | 비고 |
|---|---|---|---|
| CHK-DAILY-001 | 오늘 스니펫 작성 | PASS | - |
| CHK-WEEKLY-002 | 주간 스니펫 수정 | FAIL | 저장 버튼 비활성 이슈 |

## 스크린샷
- CHK-DAILY-001: `./qa-artifacts/2026-02-27/CHK-DAILY-001-home.png`
- CHK-WEEKLY-002: `./qa-artifacts/2026-02-27/CHK-WEEKLY-002-error.png`
```

## 5) 체크리스트 ID 규칙

형식:

- `CHK-<DOMAIN>-<NNN>`

예시:

- `CHK-DAILY-001`
- `CHK-WEEKLY-002`
- `CHK-TERMS-001`
- `CHK-SETTINGS-003`
- `CHK-ACHIEVE-001`

규칙:

- `<DOMAIN>`은 기능 영역을 명확히 표현
- `<NNN>`은 3자리 숫자(001부터)
- 동일 문서 내 ID 중복 금지

## 6) CI 연동 기준

GitHub Actions에서 E2E High는 `e2e-high` job으로 실행한다.

- 워크플로 파일: `.github/workflows/ci.yml`
- 실행 스크립트: `npm --workspace apps/client run test:e2e:high`
- Playwright 리포트/결과물은 artifact로 업로드한다.

CI 환경 기본값:

- `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`
- `E2E_API_URL=http://127.0.0.1:8000`
- `E2E_BASE_URL=http://127.0.0.1:3000`
- `TEST_AUTH_BYPASS_ENABLED=true`

## 7) PR 체크리스트

- [ ] `@high` 시나리오 실행 결과를 문서화했다.
- [ ] PASS/FAIL 표에 체크리스트 ID를 포함했다.
- [ ] 스크린샷을 `apps/client/docs/qa-artifacts/<date>/`에 정리했다.
- [ ] 문서 내 스크린샷 상대 경로가 실제 파일과 일치한다.
- [ ] CI `e2e-high` job 결과를 확인했다.
