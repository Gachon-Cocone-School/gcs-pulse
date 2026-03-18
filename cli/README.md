# gcs-pulse-cli

GCS Pulse 백엔드를 터미널에서 조작하는 CLI입니다.

서버 주소는 세션 파일에 저장된 값을 따르며, 기본값은 `https://api.1000.school`입니다.
설정은 `~/.gcs-pulse-cli/.gcs-pulse-session.json`에 자동으로 저장됩니다.

## 요구사항

- Python 3.9+
- GCS Pulse API 토큰 (교수/어드민 권한)

## 설치

```bash
cd cli
pip3 install -e .
```

> **PATH 문제 시**: `echo 'export PATH="$HOME/Library/Python/3.9/bin:$PATH"' >> ~/.zshrc && source ~/.zshrc`

## 빠른 시작

```bash
# 최초 1회: API 토큰 설정
gcs-pulse-cli setup

# 이후는 플래그 없이 바로 사용
gcs-pulse-cli --json auth status
```

## 토큰 갱신

```bash
gcs-pulse-cli setup --api-token <NEW_TOKEN>
```

---

## 전체 명령어

### setup

```bash
# 최초 설정 (프롬프트로 토큰 입력)
gcs-pulse-cli setup

# 토큰 직접 전달
gcs-pulse-cli setup --api-token <TOKEN>
```

---

### auth

```bash
# 현재 인증 상태 및 사용자 정보 확인
gcs-pulse-cli --json auth status

# 인증 + MCP 프로필 통합 확인
gcs-pulse-cli --json auth verify
```

---

### daily (일일 스니펫)

```bash
# 목록 조회
gcs-pulse-cli --json daily list
gcs-pulse-cli --json daily list --limit 10 --offset 0 --order desc --scope own

# 단건 조회
gcs-pulse-cli --json daily get <ID>

# 작성
gcs-pulse-cli --json daily create "오늘 한 일"

# 수정
gcs-pulse-cli --json daily update <ID> "수정된 내용"

# 삭제
gcs-pulse-cli --json daily delete <ID>

# AI 정리 (빈 내용이면 템플릿 반환)
gcs-pulse-cli --json daily organize
gcs-pulse-cli --json daily organize "오늘 한 일 내용"

# AI 피드백
gcs-pulse-cli --json daily feedback
```

---

### weekly (주간 스니펫)

```bash
# 목록 조회
gcs-pulse-cli --json weekly list
gcs-pulse-cli --json weekly list --limit 10 --offset 0 --order desc --scope own

# 단건 조회
gcs-pulse-cli --json weekly get <ID>

# 작성
gcs-pulse-cli --json weekly create "이번 주 한 일"

# 수정
gcs-pulse-cli --json weekly update <ID> "수정된 내용"

# 삭제
gcs-pulse-cli --json weekly delete <ID>

# AI 정리
gcs-pulse-cli --json weekly organize
gcs-pulse-cli --json weekly organize "이번 주 한 일 내용"

# AI 피드백
gcs-pulse-cli --json weekly feedback
```

---

### comments (코멘트)

`--comment-type` 값: `peer` (동료 코멘트) | `professor` (교수 코멘트)

```bash
# 목록 조회
gcs-pulse-cli --json comments list --daily-snippet-id <ID>
gcs-pulse-cli --json comments list --weekly-snippet-id <ID>

# 멘션 가능한 사용자 목록 조회 (@이름 작성 전 확인용)
gcs-pulse-cli --json comments mentionable-users --daily-snippet-id <ID>
gcs-pulse-cli --json comments mentionable-users --weekly-snippet-id <ID>

# 작성 (content에 @이름 형식으로 멘션 가능)
gcs-pulse-cli --json comments create "내용" --comment-type peer --daily-snippet-id <ID>
gcs-pulse-cli --json comments create "@홍길동 확인 부탁드립니다" --comment-type peer --daily-snippet-id <ID>
gcs-pulse-cli --json comments create "내용" --comment-type professor --weekly-snippet-id <ID>

# 수정
gcs-pulse-cli --json comments update <COMMENT_ID> "수정된 내용"

# 삭제
gcs-pulse-cli --json comments delete <COMMENT_ID>
```

> **@멘션**: `mentionable-users`로 이름을 먼저 확인한 뒤 `@이름`을 content에 포함하면 해당 사용자에게 알림이 전송됩니다. 같은 이름이 여럿이면 알림이 전송되지 않으므로 정확한 이름을 사용하세요.

---

### users (사용자/팀 리스트)

```bash
# 학생 목록
gcs-pulse-cli --json users list --limit 100 --offset 0

# 학생 검색
gcs-pulse-cli --json users search --q "검색어" --limit 20

# 팀 목록
gcs-pulse-cli --json users teams --limit 100 --offset 0
```

---

### achievements (성취)

```bash
# 내 성취 목록
gcs-pulse-cli --json achievements me

# 최근 성취 목록
gcs-pulse-cli --json achievements recent --limit 10
```

---

### notifications (알림)

```bash
# 알림 목록 조회
gcs-pulse-cli --json notifications list
gcs-pulse-cli --json notifications list --limit 20 --offset 0

# 읽지 않은 알림 수 조회
gcs-pulse-cli --json notifications unread-count

# 개별 알림 읽음 처리
gcs-pulse-cli --json notifications read <NOTIFICATION_ID>

# 전체 알림 읽음 처리
gcs-pulse-cli --json notifications read-all

# 알림 설정 조회
gcs-pulse-cli --json notifications settings

# 알림 설정 수정
gcs-pulse-cli --json notifications settings-update --notify-post-author true
gcs-pulse-cli --json notifications settings-update --notify-mentions false
gcs-pulse-cli --json notifications settings-update --notify-participants false
```

---

### meeting-rooms (회의실)

```bash
# 회의실 목록
gcs-pulse-cli --json meeting-rooms list

# 특정 날짜 예약 현황
gcs-pulse-cli --json meeting-rooms reservations --room-id <ID> --date 2026-03-20

# 예약
gcs-pulse-cli --json meeting-rooms reserve \
  --room-id <ID> \
  --start-at 2026-03-20T09:00:00+09:00 \
  --end-at 2026-03-20T10:00:00+09:00 \
  --purpose "회의 목적"

# 예약 취소
gcs-pulse-cli --json meeting-rooms cancel <RESERVATION_ID>
```

---

## 출력 형식

`--json` 플래그 사용 시:

```json
{ "ok": true,  "command": "...", "data": { ... }, "meta": { "server_url": "..." } }
{ "ok": false, "command": "...", "error": { "code": "...", "message": "..." } }
```

자동화·파이프라인 작업에는 `--json` 사용을 권장합니다.

---

## 문제 해결

| 증상 | 해결 |
|------|------|
| `command not found` | PATH에 `~/Library/Python/3.9/bin` 추가 |
| `401 Not authenticated` | `gcs-pulse-cli setup` 으로 토큰 재설정 |
| `403 Forbidden` | 토큰 권한(교수/어드민) 확인 |
| 연결 타임아웃 | 네트워크 상태 확인 |
