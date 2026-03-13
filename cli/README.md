# gcs-pulse-cli

GCS Pulse 백엔드를 터미널에서 조작하는 CLI입니다.

## 요구사항

- Python 3.9+
- 접근 가능한 GCS Pulse 서버 URL
- API 토큰(교수/어드민 권한 작업 시 해당 권한 토큰)

## 배포본 만들기 (wheel/sdist)

`cli` 디렉터리에서 실행:

```bash
python3 -m pip install --upgrade build
python3 -m build
```

생성물:

- `dist/*.whl`
- `dist/*.tar.gz`

## 설치하기

### 1) 로컬 개발(Editable)

```bash
pip3 install -e .
```

### 2) 배포본 설치

```bash
pip3 install dist/*.whl
```

설치 확인:

```bash
gcs-pulse-cli --help
```

## 기본 실행

```bash
gcs-pulse-cli --server-url https://api-dev.1000.school --api-token <TOKEN>
```

인자 없이 실행하면 REPL로 진입합니다.

## 빠른 시작

```bash
# 1) 인증 상태 확인
gcs-pulse-cli --json --server-url https://api-dev.1000.school --api-token <TOKEN> auth status

# 2) 프로젝트 세션 저장
gcs-pulse-cli --server-url https://api-dev.1000.school --api-token <TOKEN> --project . project new

# 3) 이후에는 --project로 재사용
gcs-pulse-cli --json --project . daily list --scope own --limit 5
gcs-pulse-cli --json --project . weekly list --scope own --limit 5
```

## project 기능(세션 저장/재사용)

`project` 명령은 서버 접속 설정을 프로젝트 폴더에 저장해 반복 입력을 줄여줍니다.

- 세션 파일: `.gcs-pulse-session.json`
- 저장되는 값: `server_url`, `api_token`, `timeout`, `project`
- 실행 시 `--project <DIR>`를 주면 세션을 자동 로드합니다.

```bash
# 최초 1회 생성
gcs-pulse-cli --server-url https://api-dev.1000.school --api-token <TOKEN> --project . project new

# 저장된 세션 확인
gcs-pulse-cli --json --project . project status

# 현재 옵션으로 세션 갱신
gcs-pulse-cli --server-url https://api-dev.1000.school --api-token <NEW_TOKEN> --project . project save

# 이후 명령은 --project만으로 실행 가능
gcs-pulse-cli --json --project . users list --limit 100 --offset 0
```

## 주요 명령

```bash
# Snippets
gcs-pulse-cli --json --api-token <TOKEN> daily list --scope all --limit 50 --offset 0
gcs-pulse-cli --json --api-token <TOKEN> weekly list --scope all --limit 50 --offset 0

# Comments
gcs-pulse-cli --json --api-token <TOKEN> comments list --daily-snippet-id 1
gcs-pulse-cli --json --api-token <TOKEN> comments create "좋은 정리예요" --comment-type GENERAL --daily-snippet-id 1

# Achievements
gcs-pulse-cli --json --api-token <TOKEN> achievements me
gcs-pulse-cli --json --api-token <TOKEN> achievements recent --limit 10

# 교수/어드민 전용 조회
gcs-pulse-cli --json --api-token <TOKEN> users list --limit 100 --offset 0
gcs-pulse-cli --json --api-token <TOKEN> users teams --limit 100 --offset 0
gcs-pulse-cli --json --api-token <TOKEN> users search --q kim --limit 20
```

## 출력 형식

- `--json` 사용 시: `{ ok, command, data, meta }` 또는 `{ ok:false, command, error }`
- 자동화/집계 작업에는 `--json` 사용을 권장합니다.

## 문제 해결

- `Installed CLI not found`:
  - PATH에 설치 위치가 잡혀 있는지 확인
  - `pip3 install -e .` 또는 wheel 재설치
- 401/403 오류:
  - 토큰 유효성 및 권한(교수/어드민) 확인
- 연결 실패:
  - `--server-url` 대상 서버 접근 가능 여부 확인
