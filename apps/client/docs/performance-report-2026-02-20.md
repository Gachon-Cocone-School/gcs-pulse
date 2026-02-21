# GCS Mono 성능 분석 보고서 (추가 측정)

- 작성일: 2026-02-21
- 대상 리포지토리: `gcs-mono`
- 범위: Next.js Client (`apps/client`) + FastAPI Server (`apps/server`)
- 성격: 2026-02-20 보고서 후속 측정 (개선 반영 상태 재평가)

---

## 1) 핵심 요약 (Executive Summary)

이번 후속 측정 기준으로, 이전 대비 다음 개선이 확인되었습니다.

1. **스니펫 페이지 초기 JS payload 감소**
   - `/daily-snippets`: **603.5KB → 451.8KB** (**-25.1%**)
   - `/weekly-snippets`: **603.4KB → 451.6KB** (**-25.2%**)

2. **페이지 초기 데이터 워터폴 지연 감소**
   - Daily(기존 4콜 시나리오 vs 신규 1콜): **7.82ms → 4.23ms** (**-45.9%**)
   - Weekly(기존 4콜 시나리오 vs 신규 1콜): **6.89ms → 3.88ms** (**-43.7%**)

3. **남은 병목**
   - 동시성에서 `POST /comments` tail latency가 가장 큼 (p95 **221.55ms**)
   - 스니펫 라우트 초기 번들에 여전히 대형 청크(약 184KB, 142KB) 포함

---

## 2) 측정 환경 및 방법

### 환경
- OS: Darwin 25.3.0
- Client: Next.js 16.0.7 (`next build` 후 `next start`)
- Server: FastAPI + SQLAlchemy(Async)
- 벤치 서버:
  - Client: `127.0.0.1:3000`
  - Server: `127.0.0.1:8000` (test 모드, `perf_test.db`, test auth bypass)

### 방법
1. **빌드/번들 분석**
   - `.next/static/chunks/*.js` 용량 집계
   - `page_client-reference-manifest.js` 기반 route 초기 JS payload 계산

2. **클라이언트 응답시간 측정**
   - 페이지별 반복 요청(30회)으로 avg/p50/p95 산출
   - 동시성 20, 총 100요청으로 처리량(rps) 및 지연 측정

3. **서버 API 성능 측정**
   - 인증 세션 기준 순차/동시성 측정
   - `page-data` 신규 경로와 기존 list 경로 비교

4. **워터폴 비교 시뮬레이션**
   - 기존 클라이언트 로딩 시나리오(다중 호출) vs 신규 `/page-data` 단일 호출

---

## 3) 클라이언트 성능 결과

## 3-1. 전체 청크 용량

- `.next/static/chunks/*.js`
  - 파일 수: **31개**
  - 총합: **1,463,258 bytes** (약 **1.40 MB**)

상위 청크:
- `93b2275fe9ff8a6b.js`: 213,850 bytes
- `80c85e03b9f1c789.js`: 183,998 bytes
- `d027480a53636471.js`: 170,028 bytes
- `c95801a2424dadf1.js`: 142,433 bytes

## 3-2. route별 초기 JS payload (manifest 기반)

| Route | 현재(2026-02-21) | 이전(2026-02-20) | 변화 |
|---|---:|---:|---:|
| `/` | 120.1 KB | 117.3 KB | +2.8 KB |
| `/daily-snippets` | 451.8 KB | 603.5 KB | **-151.7 KB (-25.1%)** |
| `/weekly-snippets` | 451.6 KB | 603.4 KB | **-151.8 KB (-25.2%)** |
| `/settings` | 162.3 KB | 158.5 KB | +3.8 KB |

해석:
- 스니펫 페이지 초기 payload가 유의미하게 감소.
- 다만 `/daily-snippets`, `/weekly-snippets`는 여전히 홈 대비 약 3.8배 수준으로 큼.

## 3-3. 페이지 응답시간 (단건 반복, 30회)

| Route | avg | p50 | p95 |
|---|---:|---:|---:|
| `/` | 1.75ms | 0.92ms | 2.08ms |
| `/login` | 0.83ms | 0.72ms | 0.87ms |
| `/terms` | 0.79ms | 0.70ms | 0.81ms |
| `/settings` | 0.71ms | 0.63ms | 0.72ms |
| `/daily-snippets` | 4.25ms | 2.47ms | 4.41ms |
| `/weekly-snippets` | 2.01ms | 1.88ms | 2.29ms |

## 3-4. 동시성(20 concurrent, 100 req)

| Route | RPS | avg | p50 | p95 |
|---|---:|---:|---:|---:|
| `/daily-snippets` | 466.50 | 38.46ms | 39.68ms | 43.33ms |
| `/weekly-snippets` | 556.74 | 32.43ms | 34.49ms | 40.44ms |

---

## 4) 서버 성능 결과

## 4-1. 순차 측정 (인증 세션)

| Endpoint | avg | p50 | p95 | status |
|---|---:|---:|---:|---|
| `GET /snippet_date` | 0.63ms | 0.61ms | 0.73ms | 200 |
| `GET /daily-snippets?scope=own` | 2.20ms | 2.14ms | 2.44ms | 200 |
| `GET /weekly-snippets?scope=own` | 2.80ms | 2.74ms | 3.05ms | 200 |
| `GET /daily-snippets/page-data` | 4.09ms | 3.99ms | 4.55ms | 200 |
| `GET /weekly-snippets/page-data` | 4.08ms | 4.03ms | 4.47ms | 200 |
| `POST /daily-snippets` | 2.88ms | 2.80ms | 3.14ms | 200 |
| `POST /weekly-snippets` | 2.85ms | 2.77ms | 3.17ms | 200 |

해석:
- `page-data` 단일 API는 list 단건보다 endpoint 자체는 무겁지만,
- 클라이언트 총 호출 수를 줄여 E2E 초기 로딩에는 유리함.

## 4-2. 동시성(20 concurrent, 100 req)

| Endpoint | RPS | avg | p50 | p95 | status |
|---|---:|---:|---:|---:|---|
| `GET /daily-snippets?scope=own` | 364.76 | 51.67ms | 49.37ms | 74.23ms | 200 |
| `GET /weekly-snippets?scope=own` | 378.70 | 50.07ms | 46.80ms | 72.09ms | 200 |
| `GET /daily-snippets/page-data` | 267.89 | 70.46ms | 62.99ms | 103.35ms | 200 |
| `GET /weekly-snippets/page-data` | 279.95 | 67.60ms | 62.58ms | 97.78ms | 200 |
| `GET /comments` | 365.71 | 51.88ms | 52.40ms | 71.80ms | 200 |
| `POST /comments` | 225.93 | 77.36ms | 52.65ms | **221.55ms** | 200 |

해석:
- 댓글 쓰기(`POST /comments`)가 동시성 tail latency 최댓값.
- 스니펫 조회계열 대비 write 경로의 분산이 큼.

## 4-3. rate limit 영향 확인

동시성 부하에서 다음 엔드포인트는 rate limit에 빠르게 도달:
- `GET /auth/me`: 200(20건), 429(80건)
- `GET /terms`: 200(20건), 429(80건)

=> 이 두 경로는 **벤치 수치 해석 시 429 비율을 함께 봐야 함**.

---

## 5) 워터폴 개선 효과 (핵심)

기존 로딩(다중 API) vs 신규 `page-data`(단일 API) 비교:

| 시나리오 | avg | p50 | p95 |
|---|---:|---:|---:|
| old_daily_flow | 7.82ms | 7.72ms | 8.20ms |
| new_daily_flow | **4.23ms** | **4.17ms** | **4.57ms** |
| old_weekly_flow | 6.89ms | 6.76ms | 7.39ms |
| new_weekly_flow | **3.88ms** | **3.86ms** | **4.02ms** |

요약:
- Daily: **-45.9%**
- Weekly: **-43.7%**

---

## 6) 코드 레벨 진단 (현재 상태)

### 반영된 개선
1. **초기 데이터 로딩 단일화**
   - Client: `apps/client/src/lib/loadSnippetPageData.ts`
   - Server: `apps/server/app/routers/daily_snippets.py`, `apps/server/app/routers/weekly_snippets.py`
   - `/page-data` 경로 도입으로 호출 수 축소

2. **마크다운 렌더러 분리**
   - `apps/client/src/components/views/MarkdownRenderer.tsx` 신설
   - `SnippetForm`, `CommentList`에서 공통 사용

### 남은 병목/이슈
1. **스니펫 라우트 초기 청크 여전히 큼**
   - route payload에 대형 청크(약 184KB, 142KB) 포함

2. **댓글 쓰기 경로 tail latency 큼**
   - 동시성에서 `POST /comments` p95 221.55ms

3. **list 응답 editable 계산의 반복 조회 패턴**
   - `daily_snippets.py`, `weekly_snippets.py` 리스트 루프에서 owner 조회 반복

4. **디버그 로그 잔존**
   - `apps/client/src/components/views/TeamSnippetFeed.tsx`의 `console.log` 출력

5. **운영/보안 주의사항**
   - 민감한 환경변수(토큰/시크릿)는 저장소 추적 제외 필요 (`.env` 관리 정책 점검)

---

## 7) 우선순위 제안

### P0
1. **스니펫 페이지 초기 로드 청크 추가 축소**
   - 탭 비활성 영역(팀 피드/미리보기)의 실제 렌더 시점 지연 검토

2. **댓글 쓰기 경로 최적화**
   - write 경로의 DB/권한 체크 구간 점검 및 tail latency 완화

### P1
3. **`page-data` 내부 쿼리 비용 최적화**
   - prev/next 탐색 및 owner/editable 계산 경량화

4. **반복 owner 조회(N+1성 패턴) 제거**
   - list 결과에서 owner 정보 활용 일관화

5. **디버그 로그 제거**
   - 불필요한 런타임 로그 정리

### P2
6. **rate limit 정책 재검토**
   - 벤치/운영 환경 분리 또는 사용자 단위 key 보강

---

## 8) 결론

후속 측정 결과, 현재 변경 사항으로:
- **스니펫 페이지 초기 payload 약 25% 축소**
- **초기 데이터 로딩 워터폴 약 44~46% 단축**

즉, 사용자 체감 성능에 직접 영향을 주는 핵심 구간은 분명히 개선되었습니다.

다음 최대 효과 지점은
1) 스니펫 라우트 초기 청크 추가 경량화,
2) 댓글 쓰기 tail latency 완화
입니다.

---

## 9) 2026-02-21 추가 최적화 반영 결과 (댓글 + 번들 지연 로딩)

이번 라운드에서 아래 2가지를 추가 반영했습니다.

- Server: `POST /comments` 경로의 불필요 조회/refresh 제거
- Client: `TeamSnippetFeed`, `CommentList`, `SnippetAnalysisReport` 지연 로딩 + 팀 피드 debug 로그 제거

### 9-1. `POST /comments` 동시성 성능 (20 concurrent / 100 req)

| 지표 | 변경 전 | 변경 후 | 변화 |
|---|---:|---:|---:|
| RPS | 225.93 | 249.73 | **+10.5%** |
| avg | 77.36ms | 60.77ms | **-21.4%** |
| p50 | 52.65ms | 34.43ms | **-34.6%** |
| p95 | 221.55ms | 172.43ms | **-22.2%** |

### 9-2. snippet 페이지 초기 JS payload (manifest 기준)

| Route | 변경 전 | 변경 후 | 변화 |
|---|---:|---:|---:|
| `/daily-snippets` | 451.8 KB | 251.7 KB | **-200.1 KB (-44.3%)** |
| `/weekly-snippets` | 451.6 KB | 251.5 KB | **-200.1 KB (-44.3%)** |

참고(동일 빌드 기준):
- `/`: 117.3 KB
- `/settings`: 158.6 KB

### 9-3. 검증 결과

- `npm --prefix "/Users/namjookim/projects/gcs-mono/apps/client" run lint` ✅
- `npm --prefix "/Users/namjookim/projects/gcs-mono/apps/client" run build` ✅
- E2E high 일부(스니펫 핵심 시나리오) ✅
  - `CHK-DAILY-001~003`, `CHK-WEEKLY-001~003` 통과
- E2E high 중 토큰 발급 시나리오(`CHK-*-004`)는 **기존 설정 페이지 상태 의존 이슈로 실패**
  - 실패 지점: "새 토큰 생성" 버튼 탐색
  - 본 변경(댓글/번들)과 직접 연관 없는 기존 이슈로 분리 관리 권장
- 서버 댓글 smoke (작성/조회/수정/삭제 + 권한 경계) ✅

---

## 10) PR 본문 초안

### Summary
`POST /comments` 서버 경로를 경량화하고, 스니펫 페이지의 팀 피드/댓글/분석 컴포넌트를 지연 로딩으로 전환해 동시성 tail latency와 초기 JS payload를 함께 줄였습니다.

### What changed

#### Server
- `get_user_by_sub_basic` 추가 (consents 미포함 조회)
- `get_viewer_or_401(..., include_consents=False)` 옵션 도입 및 댓글 라우터 적용
- 댓글 라우터에서 snippet owner 재조회 제거 (`snippet.user` 재사용)
- `create_comment` / `update_comment`의 `commit + refresh + 재조회` → `commit + 재조회`로 단순화

#### Client
- `daily-snippets`, `weekly-snippets`에서 `TeamSnippetFeed`를 `next/dynamic`으로 지연 로딩
- `TeamSnippetCard`의 `CommentList`, `SnippetAnalysisReport` 지연 로딩
- `SnippetForm`의 `SnippetAnalysisReport` 지연 로딩
- `TeamSnippetFeed` debug `console.log` 제거

#### Docs
- 본 문서에 before/after 성능 수치 및 검증 결과 업데이트

### Performance impact
- `POST /comments` (20 concurrent / 100 req)
  - p95: **221.55ms → 172.43ms (-22.2%)**
  - avg: **77.36ms → 60.77ms (-21.4%)**
- Initial JS payload
  - `/daily-snippets`: **451.8KB → 251.7KB (-44.3%)**
  - `/weekly-snippets`: **451.6KB → 251.5KB (-44.3%)**

### Test plan
- [x] Client lint/build 통과
- [x] 스니펫 핵심 E2E high (`CHK-001~003`) 통과
- [x] 댓글 CRUD smoke 통과
- [x] 댓글 권한 경계(작성자/팀/비팀) smoke 통과
- [ ] 설정 토큰 발급 E2E(`CHK-004`) 기존 이슈 별도 트래킹

### Risk / Rollback
- Risk: 지연 로딩 구간의 첫 진입 시 fallback 노출 타이밍 변화 가능
- Mitigation: 로딩 fallback 추가, 기존 조건 렌더 게이트 유지
- Rollback: 아래 파일 원복 시 즉시 이전 동작 복귀
  - `apps/server/app/crud.py`
  - `apps/server/app/routers/snippet_utils.py`
  - `apps/server/app/routers/comments.py`
  - `apps/client/src/app/daily-snippets/page.client.tsx`
  - `apps/client/src/app/weekly-snippets/page.client.tsx`
  - `apps/client/src/components/views/TeamSnippetCard.tsx`
  - `apps/client/src/components/views/SnippetForm.tsx`
  - `apps/client/src/components/views/TeamSnippetFeed.tsx`
