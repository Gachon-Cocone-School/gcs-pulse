# 클라이언트+서버 전반 중복 제거 리팩토링 디자인

작성일: 2026-02-14
주제: 코드 중복 제거 및 구조 정리를 통해 방만해진 코드를 단순화하되, 외부 동작(API/DB/화면)은 유지

## 요약
- 범위: 클라이언트+서버 전반 리팩토링
- 우선 목표: 동작 보존 최우선
- 변경 금지선: API 계약/DB 스키마 불변
- 선택한 접근: **A안(저위험 중복 제거 우선 + 점진 확장)**

## 성공 기준
1. API 엔드포인트/요청/응답 형식이 기존과 동일하다.
2. DB 스키마 및 마이그레이션 변경이 없다.
3. 사용자 관점 화면 동작/UX(조회, 이동, 저장, 댓글 토글 등)가 동일하다.
4. 서버/클라이언트의 중복 코드가 줄고, 책임 경계가 명확해진다.
5. 기존 테스트 및 빌드/타입 검증에서 회귀가 없다.

## 제약 조건
- 외부 계약(API/DB/UX)은 유지한다.
- 신규 기능 추가/성능 최적화 중심 변경은 이번 범위에서 제외한다.
- 대규모 폴더 재구성은 하지 않는다.

## 대안 비교

### 1) A안 — 저위험 중복 제거 우선 + 점진 확장 (선택)
- 내용:
  - 서버의 명확한 중복부터 정리
  - 클라이언트 daily/weekly 공통 흐름 추출
  - 분산 타입 정의 통합
- 장점:
  - 회귀 리스크가 가장 낮다.
  - 변경 이유가 명확하고 리뷰가 쉽다.
- 단점:
  - 큰 구조 재편 대비 체감 변화가 단계적이다.

### 2) B안 — 도메인 단위 대규모 재배치
- 장점: 장기 유지보수성 향상 여지가 큼
- 단점: 파일 이동/의존성 변경이 많아 검증 범위가 커짐

### 3) C안 — 타입/계약 중심 정리
- 장점: 타입 안정성 강화에 유리
- 단점: 즉각적인 중복 제거 체감은 상대적으로 낮을 수 있음

## 현재 코드 기준 주요 중복/핫스팟

1) 서버 daily/weekly 라우터 패턴 중복
- 참조:
  - `apps/server/app/routers/daily_snippets.py:26`
  - `apps/server/app/routers/weekly_snippets.py:48`
- 설명: 인증→조회→권한/편집 가능 여부→CRUD 호출 흐름이 거의 동일

2) weekly 라우터 인증/뷰어 조회 반복
- 참조:
  - `apps/server/app/routers/snippet_utils.py:37`
  - `apps/server/app/routers/weekly_snippets.py:52`
- 설명: 공통 유틸이 있음에도 로컬 인증 경로가 반복됨

3) `crud.py` 내 토큰 관련 함수 중복 정의
- 참조:
  - `apps/server/app/crud.py:278`
  - `apps/server/app/crud.py:447`
- 설명: 동일 성격 함수가 중복 선언되어 유지보수/오해 위험 존재

4) 클라이언트 daily/weekly 페이지 공통 흐름 중복
- 참조:
  - `apps/client/src/app/daily-snippets/page.tsx:35`
  - `apps/client/src/app/weekly-snippets/page.tsx:38`
- 설명: 로딩/이동 계산/저장/정리 흐름이 유사

5) 타입 선언 분산
- 참조:
  - `apps/client/src/lib/types.ts:1`
  - `apps/client/src/context/auth-context.tsx:6`
  - `apps/client/src/components/views/CommentList.tsx:15`
- 설명: 동일 도메인 타입의 다중 선언으로 drift 위험

## 설계

### 1. 아키텍처/경계
- 외부 계약은 고정하고 내부 중복만 제거한다.
- 변경 범위는 아래 3개 축으로 제한한다.
  1) 서버 인증 경로/중복 함수 정리
  2) 클라이언트 daily/weekly 공통 로직 추출
  3) 클라이언트 타입 단일 소스화

#### 비목표
- API 스펙 변경
- DB 스키마 변경
- 기능 추가
- 대규모 폴더 이동

### 2. 컴포넌트/모듈 상세

#### 서버
1) weekly 인증 경로 단일화
- 대상: `apps/server/app/routers/weekly_snippets.py`
- 방식: `snippet_utils.get_viewer_or_401()` 공통 유틸 사용으로 인증 반복 제거

2) CRUD 토큰 함수 단일 정의 유지
- 대상: `apps/server/app/crud.py`
- 방식: 중복 함수 블록 정리 후 단일 구현만 유지

3) 라우터 책임 유지
- 라우터는 요청/권한 체크/응답 조립 중심으로 유지

#### 클라이언트
1) daily/weekly 공통 로직 추출
- 대상:
  - `apps/client/src/app/daily-snippets/page.tsx`
  - `apps/client/src/app/weekly-snippets/page.tsx`
- 방식: 공통 상태/로딩/이동/저장 흐름을 훅(또는 유틸)로 추출, day/week 차이는 전략 파라미터로 분리

2) 타입 단일 소스 정리
- 대상: `lib/types.ts`, `auth-context.tsx`, `CommentList.tsx` 등
- 방식: User/Comment/Snippet 관련 중복 타입을 중심 타입 파일로 통합 후 참조 전환

3) UI 계약 불변
- `Button`/피드/카드 컴포넌트 props 계약과 동작은 유지

### 3. 데이터 흐름/오류 처리

#### 데이터 흐름
- 서버: 라우터 → 인증/뷰어 확인 → CRUD → 스키마 응답 흐름 유지
- 클라: 로드 → 조회 → 편집/저장/정리 → 상태 반영 흐름 유지
- 변경은 내부 호출 구조 단순화에 한정

#### 오류 처리
- 401/403/404/500 의미 및 노출 패턴 유지
- 신규 에러 포맷 도입 없음

## 검증 전략

### 서버
- 기존 플로우 테스트 중심 회귀 확인
  - `apps/server/tests/test_daily_snippets_flow.py:18`
  - `apps/server/tests/test_weekly_snippets_flow.py:18`
  - `apps/server/tests/test_snippet_editable_utils.py:12`
- weekly 인증 실패(401) 및 토큰 CRUD 동등성 확인

### 클라이언트
- lint/build/type 검증
- 수동 시나리오
  - daily/weekly 조회
  - 이전/다음 이동
  - 저장/정리
  - 댓글 토글
  - readOnly 규칙 동일성

### 계약 불변 검증
- API 응답 구조 변경 없음 확인
- DB 스키마 변경 없음 확인

## 리스크와 완화
1) 타입 정리 중 TS 회귀
- 완화: 타입 변경은 참조 치환 중심으로 작게 적용, 빌드/타입 체크 즉시 검증

2) 권한/편집 가능 여부 회귀
- 완화: weekly 인증 경로 통일 후 권한 테스트 우선 실행

3) UI 토글/버튼 동작 회귀
- 완화: 관련 화면 수동 검증 케이스를 고정 체크리스트로 운영

## 단계별 실행 순서(고수준)
1. 서버 중복 정리(weekly 인증 경로 통일, CRUD 중복 함수 정리)
2. 클라이언트 daily/weekly 공통 로직 추출
3. 클라이언트 타입 통합
4. 서버/클라 검증 수행 및 회귀 확인

## 다음 단계
- 이 디자인을 기준으로 `superpowers:writing-plans`를 호출해 구현 계획(파일 단위 작업/검증 절차)을 작성한다.
