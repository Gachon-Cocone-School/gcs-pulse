# gcs-pulse-cli

Stateful CLI harness for GCS Pulse backend.

## Install

```bash
pip install -e .
```

## Run

```bash
gcs-pulse-cli --server-url http://127.0.0.1:8000 --api-token <TOKEN>
```

기본 실행(무인자)은 REPL로 진입합니다.

## 빠른 시작

```bash
# 1) 인증 확인
gcs-pulse-cli --json --server-url http://127.0.0.1:8000 --api-token <TOKEN> auth status

# 2) 프로젝트 세션 저장
gcs-pulse-cli --server-url http://127.0.0.1:8000 --api-token <TOKEN> --project . project new

# 3) 이후에는 --project로 재사용
gcs-pulse-cli --json --project . achievements me
gcs-pulse-cli --json --project . comments list --daily-snippet-id 1
gcs-pulse-cli --json --project . users search --q kim --limit 5
```

## 주요 명령 예시

```bash
# 인증
gcs-pulse-cli --json --api-token <TOKEN> auth status

# Daily/Weekly snippets
gcs-pulse-cli --json --api-token <TOKEN> daily list --limit 5
gcs-pulse-cli --json --api-token <TOKEN> weekly get 123

# Achievements
gcs-pulse-cli --json --api-token <TOKEN> achievements me
gcs-pulse-cli --json --api-token <TOKEN> achievements recent --limit 10

# Comments
gcs-pulse-cli --json --api-token <TOKEN> comments list --daily-snippet-id 1
gcs-pulse-cli --json --api-token <TOKEN> comments create "좋은 정리예요" --comment-type GENERAL --daily-snippet-id 1
gcs-pulse-cli --json --api-token <TOKEN> comments update 10 "코멘트 수정"
gcs-pulse-cli --json --api-token <TOKEN> comments delete 10

# User search (교수 권한 필요)
gcs-pulse-cli --json --api-token <TOKEN> users search --q kim --limit 5
```
