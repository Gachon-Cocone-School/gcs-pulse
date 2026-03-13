# TEST PLAN

## 1) 테스트 인벤토리
- `test_core.py`: 약 18~24 케이스
- `test_full_e2e.py`: 약 8~12 시나리오

## 2) 모듈별 unit 테스트 범위
- `core/session.py`: 직렬화/역직렬화
- `core/project.py`: 세션 파일 생성/저장/상태 로딩
- `utils/output.py`: 성공/실패 JSON 스키마
- `utils/gcs_pulse_backend.py`: 요청 구성, 에러 정규화
- `core/snippets.py`, `core/comments.py`, `core/achievements.py`, `core/users.py`: 경로/인자 매핑

## 3) E2E 워크플로우 시나리오
- auth status/verify
- achievements me/recent
- comments list/create/update/delete
- users search
- daily/weekly list/get/create/update/delete + organize/feedback
- 설치된 CLI subprocess 실행(`_resolve_cli("gcs-pulse-cli")`)
- `CLI_ANYTHING_FORCE_INSTALLED=1` 강제 모드

## 4) 산출물 검증 항목
- `--json` 스키마 일관성 (`ok`, `command`, `data`, `meta` / `error`)
- comments/achievements/users search 응답 스키마 및 실패 시 에러 스키마 일관성
- project 세션 파일(`.gcs-pulse-session.json`) 생성/갱신

## 5) 실행 로그

### 2026-03-13 1차 실행
```text
PYTHONPATH=/Users/namjookim/projects/clily/gcs-pulse/agent-harness python3 -m pytest src/gcs_pulse/tests/test_core.py -v --tb=no
결과: 10 passed
```

```text
PYTHONPATH=/Users/namjookim/projects/clily/gcs-pulse/agent-harness python3 -m pytest src/gcs_pulse/tests/test_full_e2e.py -v --tb=no
결과: 2 passed, 9 skipped
비고: GCS_PULSE_SERVER_URL / GCS_PULSE_API_TOKEN 미설정으로 real-backend E2E는 skip
```

```text
PYTHONPATH=/Users/namjookim/projects/clily/gcs-pulse/agent-harness python3 -m pytest src/gcs_pulse/tests/ -v --tb=no
결과: 12 passed, 9 skipped
```

```text
PATH=/Users/namjookim/Library/Python/3.9/bin:$PATH CLI_ANYTHING_FORCE_INSTALLED=1 PYTHONPATH=/Users/namjookim/projects/clily/gcs-pulse/agent-harness python3 -m pytest src/gcs_pulse/tests/ -v -s
결과: 12 passed, 9 skipped
```

```text
PYTHONPATH=/Users/namjookim/projects/clily/gcs-pulse/agent-harness python3 -m pytest src/gcs_pulse/tests/ -v --tb=no
결과: 12 passed, 9 skipped
```

## 6) 설치 검증 로그
```text
pip3 install -e /Users/namjookim/projects/clily/gcs-pulse/agent-harness
결과: 성공
```

```text
PATH=/Users/namjookim/Library/Python/3.9/bin:$PATH which gcs-pulse-cli
결과: /Users/namjookim/Library/Python/3.9/bin/gcs-pulse-cli
```

```text
PATH=/Users/namjookim/Library/Python/3.9/bin:$PATH gcs-pulse-cli --help
결과: 명령군(achievements/auth/comments/daily/project/users/weekly) 정상 출력
```
