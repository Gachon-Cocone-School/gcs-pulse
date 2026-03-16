# GCS Pulse MCP 사용자 매뉴얼 (HTTP)

> 이 문서는 GCS Pulse의 MCP 연결 안내 최신본이며, 기존 SSE 안내를 대체합니다.

## 1) 개요

GCS Pulse MCP 서버는 **streamable HTTP** 방식으로 제공됩니다.

- MCP HTTP URL: `https://api.1000.school/mcp`
- 인증 방식: `Authorization: Bearer <API_TOKEN>`
- 권장 클라이언트: Claude Code, Cursor, VS Code, Claude Desktop

MCP 서버 엔드포인트는 단일 경로로 동작합니다.

- 연결/초기화/요청: `GET|POST|DELETE /mcp`

현재 서버는 아래 capability를 제공합니다.

- Tools
  - Daily snippets
    - `daily_snippets_page_data`
    - `daily_snippets_get`
    - `daily_snippets_list`
    - `daily_snippets_create`
    - `daily_snippets_organize`
    - `daily_snippets_feedback`
    - `daily_snippets_update`
    - `daily_snippets_delete`
  - Weekly snippets
    - `weekly_snippets_page_data`
    - `weekly_snippets_get`
    - `weekly_snippets_list`
    - `weekly_snippets_create`
    - `weekly_snippets_organize`
    - `weekly_snippets_feedback`
    - `weekly_snippets_update`
    - `weekly_snippets_delete`
  - Comments
    - `comments_list`
    - `comments_create`
    - `comments_update`
    - `comments_delete`
  - Notifications
    - `notifications_list`
    - `notifications_unread_count`
    - `notifications_read`
    - `notifications_read_all`
    - `notifications_get_settings`
    - `notifications_update_settings`
  - Meeting rooms
    - `meeting_rooms_list`
    - `meeting_rooms_reservations`
    - `meeting_rooms_reserve`
    - `meeting_rooms_cancel`
  - Achievements
    - `achievements_me`
    - `achievements_recent`
  - Users (교수/어드민 권한 필요)
    - `users_list`
    - `users_search`
    - `users_teams`
- Resources
  - `gcs://me/profile`: 내 프로필 요약
  - `gcs://me/achievements`: 내 업적 요약

### Tool ↔ API 엔드포인트 매핑

| Tool | 대응 API |
| :--- | :--- |
| `daily_snippets_page_data` | `GET /daily-snippets/page-data` |
| `daily_snippets_get` | `GET /daily-snippets/{snippet_id}` |
| `daily_snippets_list` | `GET /daily-snippets` |
| `daily_snippets_create` | `POST /daily-snippets` |
| `daily_snippets_organize` | `POST /daily-snippets/organize` |
| `daily_snippets_feedback` | `GET /daily-snippets/feedback` |
| `daily_snippets_update` | `PUT /daily-snippets/{snippet_id}` |
| `daily_snippets_delete` | `DELETE /daily-snippets/{snippet_id}` |
| `weekly_snippets_page_data` | `GET /weekly-snippets/page-data` |
| `weekly_snippets_get` | `GET /weekly-snippets/{snippet_id}` |
| `weekly_snippets_list` | `GET /weekly-snippets` |
| `weekly_snippets_create` | `POST /weekly-snippets` |
| `weekly_snippets_organize` | `POST /weekly-snippets/organize` |
| `weekly_snippets_feedback` | `GET /weekly-snippets/feedback` |
| `weekly_snippets_update` | `PUT /weekly-snippets/{snippet_id}` |
| `weekly_snippets_delete` | `DELETE /weekly-snippets/{snippet_id}` |
| `comments_list` | `GET /comments?daily_snippet_id=N` 또는 `?weekly_snippet_id=N` |
| `comments_create` | `POST /comments` |
| `comments_update` | `PUT /comments/{comment_id}` |
| `comments_delete` | `DELETE /comments/{comment_id}` |
| `notifications_list` | `GET /notifications` |
| `notifications_unread_count` | `GET /notifications/unread-count` |
| `notifications_read` | `PATCH /notifications/{notification_id}/read` |
| `notifications_read_all` | `PATCH /notifications/read-all` |
| `notifications_get_settings` | `GET /notifications/settings` |
| `notifications_update_settings` | `PATCH /notifications/settings` |
| `meeting_rooms_list` | `GET /meeting-rooms` |
| `meeting_rooms_reservations` | `GET /meeting-rooms/{room_id}/reservations` |
| `meeting_rooms_reserve` | `POST /meeting-rooms/{room_id}/reservations` |
| `meeting_rooms_cancel` | `DELETE /meeting-rooms/reservations/{reservation_id}` |
| `achievements_me` | `GET /achievements/me` |
| `achievements_recent` | `GET /achievements/recent` |
| `users_list` | `GET /students` *(교수/어드민)* |
| `users_search` | `GET /students/search` *(교수/어드민)* |
| `users_teams` | `GET /teams` *(교수/어드민)* |

### 참고

- 기존 `get_leaderboard` tool 및 `gcs://achievements/recent` resource는 현재 MCP capability에서 제외되었습니다.
- snippet 관련 기능은 위 Daily/Weekly tool 세트로 사용합니다.

---

## 2) 사전 준비

1. GCS Pulse API 토큰(`API_TOKEN`)을 준비합니다.
2. `<API_TOKEN>` 값을 실제 토큰으로 교체합니다.

---

## 3) 공통 연결 정보

모든 클라이언트에서 공통으로 사용하는 값입니다.

- 서버 이름(예시): `gcs-pulse`
- 서버 주소: `https://api.1000.school/mcp`
- 헤더: `Authorization: Bearer <API_TOKEN>`

---

## 4) Claude Code 설정

Claude Code에서는 CLI 명령으로 MCP 서버를 등록합니다.

### 4-1. 프로젝트 범위(권장)

현재 레포지토리에서만 사용하려면 아래 명령을 실행합니다.

```bash
claude mcp add --transport http --scope project gcs-pulse https://api.1000.school/mcp \
  --header "Authorization: Bearer <API_TOKEN>"
```

  ### 4-2. 사용자 전역 범위(선택)

모든 프로젝트에서 공통으로 사용하려면 `--scope user`를 사용합니다.

```bash
claude mcp add --transport http --scope user gcs-pulse https://api.1000.school/mcp \
  --header "Authorization: Bearer <API_TOKEN>"
```

### 4-3. 확인/관리 명령

```bash
# 등록된 MCP 서버 목록
claude mcp list

# 특정 MCP 서버 상세 정보
claude mcp get gcs-pulse

# MCP 서버 제거
claude mcp remove gcs-pulse
```

Claude Code 내부에서는 `/mcp` 명령으로 연결 상태를 확인할 수 있습니다.

---

## 5) Cursor 설정

### 방법 A. 설정 UI에서 `mcp.json` 열기

1. Cursor 열기
2. `Settings` → `Tools & MCP`
3. MCP 설정 파일을 열어 아래 내용 반영

프로젝트 전용:
- `<프로젝트 루트>/.cursor/mcp.json`

전역(모든 프로젝트 공통):
- `~/.cursor/mcp.json`

```json
{
  "mcpServers": {
    "gcs-pulse": {
      "type": "http",
      "url": "https://api.1000.school/mcp",
      "headers": {
        "Authorization": "Bearer <API_TOKEN>"
      }
    }
  }
}
```

4. 저장 후 Cursor를 완전히 종료/재실행합니다.

---

## 6) VS Code 설정

1. 명령 팔레트 열기 (`Cmd/Ctrl + Shift + P`)
2. 아래 중 하나를 실행
   - `MCP: Open Workspace Folder Configuration`
   - `MCP: Open User Configuration`
3. 설정 파일에 아래 내용 반영

워크스페이스 설정 파일:
- `<프로젝트 루트>/.vscode/mcp.json`

```json
{
  "servers": {
    "gcs-pulse": {
      "type": "http",
      "url": "https://api.1000.school/mcp",
      "headers": {
        "Authorization": "Bearer <API_TOKEN>"
      }
    }
  }
}
```

4. 저장 후 VS Code를 재시작(또는 `Developer: Reload Window`)합니다.

---

## 7) Claude Desktop 설정

1. Claude Desktop → `Settings` → `Developer` → `Edit Config`
2. 운영체제별 설정 파일:
   - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
3. 아래 설정을 반영합니다.

```json
{
  "mcpServers": {
    "gcs-pulse": {
      "type": "http",
      "url": "https://api.1000.school/mcp",
      "headers": {
        "Authorization": "Bearer <API_TOKEN>"
      }
    }
  }
}
```

4. 저장 후 Claude Desktop을 완전히 종료/재실행합니다.

---

## 8) 동작 확인

- 클라이언트에 `gcs-pulse` MCP 서버가 표시되는지 확인
- MCP 연결 후 initialize/ping 요청이 성공하는지 확인
- 호출 시 401/403 없이 응답되는지 확인

---

## 9) 문제 해결

### `401 Invalid API token` / 인증 실패
- 토큰 값 오타 여부 확인
- `Authorization` 헤더 형식 확인: `Bearer <API_TOKEN>`

### 서버가 보이지 않음
- JSON 문법 오류(쉼표, 따옴표) 확인
- 앱 완전 재시작 수행

### 연결 실패(네트워크)
- `https://api.1000.school/mcp` 접근 가능 여부 확인
- 사내망/프록시/보안SW가 HTTP 스트리밍 연결을 차단하지 않는지 확인

---

## 10) 보안 권장사항

- 토큰을 코드 저장소에 커밋하지 마세요.
- 가능하면 클라이언트별 사용자 설정(로컬/전역 파일)에서만 토큰을 관리하세요.
- 토큰 유출이 의심되면 즉시 폐기하고 재발급하세요.
