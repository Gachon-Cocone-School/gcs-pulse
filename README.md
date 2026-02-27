# GCS LMS 모노레포

[![CI](https://github.com/namjoo-kim-gachon/gcs-mono/actions/workflows/ci.yml/badge.svg)](https://github.com/namjoo-kim-gachon/gcs-mono/actions/workflows/ci.yml)
[![License: Non-Commercial](https://img.shields.io/badge/License-Non--Commercial-orange.svg)](./LICENSE)

이 프로젝트는 LMS 시스템을 위한 프론트엔드 클라이언트와 백엔드 서버를 포함하는 모노레포입니다.

## 프로젝트 구조

- **apps/client**: Next.js 프론트엔드 애플리케이션 
- **apps/server**: Python 백엔드 애플리케이션 

## 설정 및 실행

이 프로젝트는 작업 관리를 위해 [Turborepo](https://turbo.build/)를 사용합니다.

### 필수 조건

- Node.js (최신 LTS 버전 권장)
- Python 3.x (`venv` 지원 필요)

### 설치

루트 디렉토리에서 의존성을 설치합니다:
```bash
npm install
```

### 개발 모드 실행

클라이언트와 서버를 동시에 개발 모드로 실행하려면 다음 명령어를 사용하세요:
```bash
npx turbo run dev
```
> **참고:** `apps/server/venv`에 Python 가상 환경이 설정되어 있고 의존성이 설치되어 있는지 확인해주세요.

### 빌드

클라이언트를 빌드하려면:
```bash
npx turbo run build
```

### 서버 일일 업적 배치 실행 (Cron + CLI)

업적 부여 배치는 서버의 CLI 스크립트를 외부 Cron에서 하루 1회 실행하는 방식입니다.

```bash
# 평가만 수행 (DB 반영 없음)
python3 apps/server/scripts/run_daily_achievement_grants.py --dry-run

# 기본 대상일(비즈니스 기준 전일)로 실제 반영
python3 apps/server/scripts/run_daily_achievement_grants.py
```

Ubuntu cron 예시:

```cron
CRON_TZ=Asia/Seoul
5 0 * * * /opt/gcs-mono/apps/server/venv/bin/python /opt/gcs-mono/apps/server/scripts/run_daily_achievement_grants.py >> /var/log/gcs/daily_achievement_grants.log 2>&1
```

자세한 서버 운영/옵션은 `apps/server/README.md`를 참고하세요.
