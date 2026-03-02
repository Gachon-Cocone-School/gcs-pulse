# 교수 멘토링 기능 기획안 (개정안 v2)

> GCS Pulse 교수 멘토링 시스템
> 작성일: 2026-03-02
> 핵심 방향: **Weekly-first + Risk-driven + Copilot-assisted**

---

## 1. 개정 목표

기존 위험도 모델은 작성 빈도 중심이라 피상적인 판단이 발생할 수 있다.
이번 v2 개정안은 `apps/server/prompts/`의 실제 스니펫 구성/평가 항목을 위험도 모델에 직접 연결해, 위험도 판단의 해상도를 높이는 것이 목표다.

핵심 개선:
1. 주간 운영(weekly) 중심, 일일 개입은 고위험 예외 처리
2. 프롬프트 평가축 기반의 계층형 위험도 모델(L1/L2/L3)
3. 위험 근거를 프롬프트 항목명 그대로 노출하는 explainability
4. 위험 밴드가 아닌 평가 패턴 기반 톤 추천 정책

---

## 2. 운영 원칙 (Micro-management 지양)

### 2.1 기본 철학
- 교수는 매일 전수 코멘트를 수행하지 않는다.
- 학생 자율 학습을 기본으로 두고, 위험 신호가 확인된 학생만 선택적으로 개입한다.
- 개입 목표는 통제가 아니라 회복(학습 루틴 복구)이다.

### 2.2 멘토링 Cadence

| 구분 | 주기 | 대상 | 목적 |
|---|---|---|---|
| 기본 멘토링 | 주 1회 Weekly Review | 전체 학생 요약 + 우선순위군 | 위험 조기 탐지, 주간 방향 조정 |
| 예외 개입 | 필요 시 Daily Intervention | High/Critical 학생 | 이탈 방지, 단기 회복 |

### 2.3 개입 운영 원칙 (자율 참여형)
- 교수별 일일/주간 **숫자 할당량·상한선은 두지 않는다**.
- 주간 위험 큐를 공동으로 보고, 여러 교수가 **자율적으로 개입 대상을 선택**한다.
- 동일 학생에 단기간 코멘트가 과도하게 몰리지 않도록, 최근 교수 코멘트 이력/시점을 참고해 자연스럽게 분산한다.
- 시스템은 `다음 고위험 학생` 추천만 제공하고, 실제 선택/개입 여부는 교수 재량으로 둔다.

---

## 3. 프롬프트 기반 신호체계 정렬

아래는 실제 프롬프트 구조를 기준으로 위험 신호를 정의한 매핑이다.

### 3.1 입력 구조 (파일별)

| 파일 | 기대 입력 | 위험도에 반영되는 핵심 구성항목 |
|---|---|---|
| `daily_feedback.md` | `Daily Snippet` + `Playbook` | learning_sources(`highlight/lowlight/emotion/energy/decision`), playbook_relation(`confirm/revise/extend/none`) |
| `weekly_feedback.md` | `Weekly Snippet` + `My Playbook` | strategy_linkage(`current_strategy/weekly_signal/recommended_shift/confidence`) |
| `organize_daily.md` | Raw → Daily 8개 구조화 | 오늘 한 일, 수행 목적, 하이라이트, 로우라이트, 내일 우선순위, 팀 기여 가치, 배움/남길 말, 헬스 체크(10점) |
| `organize_weekly.md` | 최근 7일 daily 묶음 | 이번주 한 일, 잘된 점/잘못된 점/아쉬운 점, 주요지표, 배움, 다음주 주요 할 일 |
| `suggest_daily_from_previous.md` | 날짜 + 전날 snippet | Daily 8개 섹션 초안(organize_daily와 동일 템플릿) |

### 3.2 점수화 평가축 (프롬프트 내 정의)

`daily_feedback.md`/`weekly_feedback.md` 공통 평가축:
- `record_completeness` (15)
- `learning_signal_detection` (25)
- `cause_effect_connection` (20)
- `action_translation` (20)
- `learning_attitude_consistency` (20)

추가 신호:
- `헬스 체크(10점)` (daily 템플릿 입력)
- `strategy_linkage.*`, `playbook_relation.*`
- `다음주 주요 할 일`/`next_action`의 미이행 이월 패턴

### 3.3 기존 모델 대비 보강 포인트

기존 모델이 놓치던 축:
- 인과 추론 품질 (`cause_effect_connection`)
- 행동 전환력 (`action_translation`)
- 지속성 추세 (`learning_attitude_consistency`)
- 전략 정렬도 (`strategy_linkage`, `playbook_relation`)
- 과업 이월/병목 (`next_action`, `다음주 주요 할 일`)

---

## 4. 위험도 모델 v2 (Prompt 정렬 계층형)

### 4.1 모델 구조
- **L1: Daily execution risk** (당일 실행/회고 품질)
- **L2: Weekly reflection/strategy risk** (주간 전략/실행 정합)
- **L3: Trend risk** (2~4주 악화·재발 추세)
- 최종 `risk_score(0~100)` + `confidence` 보정

정규화:

```text
clip(x) = min(max(x, 0), 1)
d_item = 1 - (item_score / item_max)
```

### 4.2 L1: Daily execution risk

```text
L1 = 100 * clip(
  0.12*d_record_completeness +
  0.14*d_learning_signal_detection +
  0.16*d_cause_effect_connection +
  0.17*d_action_translation +
  0.16*d_learning_attitude_consistency +
  0.10*m_daily_structure_gap +
  0.10*m_frequency_gap +
  0.05*m_affective_strain
)
```

- `m_daily_structure_gap`: Daily 필수 섹션 공란 비율
- `m_frequency_gap`: 연속 미작성 + 7일 작성률 결손
- `m_affective_strain`: 헬스체크 저하 + 정서 저하 표현

### 4.3 L2: Weekly reflection/strategy risk

```text
weekly_rubric_risk =
  0.15*d_record_completeness +
  0.20*d_learning_signal_detection +
  0.20*d_cause_effect_connection +
  0.20*d_action_translation +
  0.25*d_learning_attitude_consistency

L2 = 100 * clip(
  0.40*weekly_rubric_risk +
  0.30*m_strategy_drift +
  0.20*m_action_carryover +
  0.10*m_daily_instability
)
```

- `m_strategy_drift`: `strategy_linkage.*`, `playbook_relation.*` 불일치 반복
- `m_action_carryover`: `next_action`/`다음주 주요 할 일` 미이행 이월률
- `m_daily_instability`: 최근 7일 L1 변동성

### 4.4 L3: Trend risk (2~4주)

```text
m_trend_accel      = clip((L2_t - avg(L2_t-1, L2_t-2)) / 25)
m_trend_slope_4w   = clip((L2_t - L2_t-3) / 40)
m_trend_volatility = clip(std(L2_t-3..t) / 20)
m_relapse_rate     = clip(relapse_count_4w / max(1, recovered_count_4w))

L3 = 100 * clip(
  0.40*m_trend_accel +
  0.30*m_trend_slope_4w +
  0.20*m_trend_volatility +
  0.10*m_relapse_rate
)
```

### 4.5 최종 통합 점수

```text
L1_recent = EMA(last_3_days_L1, alpha=0.6)
raw_risk  = 0.40*L1_recent + 0.35*L2 + 0.25*L3

confidence = 0.50*data_coverage + 0.30*signal_agreement + 0.20*history_depth
risk_score = clip(raw_risk - 8*(1 - confidence), 0, 100)
```

Risk Band:
- Low: 0~29
- Medium: 30~59
- High: 60~79
- Critical: 80~100

Critical 게이트:
- `risk_score >= 80` AND
  - `L1/L2/L3` 중 2개 이상이 70+, 또는
  - `L3 >= 75` (급격한 악화/재발 추세)

### 4.6 Prompt 항목 ↔ Risk Factor 매핑

| Prompt 항목명 | Risk Factor | 계층 |
|---|---|---|
| `record_completeness` | RF1_execution_continuity | L1/L2 |
| `learning_signal_detection` | RF2_reflection_depth | L1/L2 |
| `cause_effect_connection` | RF3_reasoning_quality | L1/L2 |
| `action_translation` | RF4_actionability | L1/L2 |
| `learning_attitude_consistency` | RF5_persistence | L1/L2 |
| `내일의 우선순위`, `next_action`, `다음주 주요 할 일` | RF4_actionability | L1/L2 |
| `로우라이트`, `잘못된 점`, `아쉬운 점` | RF6_blocker_recurrence | L2/L3 |
| `헬스 체크 (10점)`, `emotion`, `energy` | RF7_affective_strain | L1/L2 |
| `strategy_linkage.*`, `playbook_relation.*` | RF8_strategy_drift | L2/L3 |
| 주차별 L2 이력 | RF9_trend_relapse | L3 |

원칙: `reasons[]`에 prompt 항목명을 그대로 노출한다.

---

## 5. Explainability & JSON 스키마 (v2)

### 5.1 reasons 표준

```json
{
  "layer": "L2",
  "risk_factor": "RF8_strategy_drift",
  "prompt_items": [
    "strategy_linkage.weekly_signal",
    "playbook_relation.relation_type"
  ],
  "severity": "high",
  "impact": 11.6,
  "evidence": "최근 2주 relation_type=revise 반복",
  "why_it_matters": "전략 불일치 누적 시 실행 실패 확률 증가"
}
```

### 5.2 출력 스키마 (요약)

```json
{
  "risk_score": 69,
  "risk_band": "High",
  "daily_subscores": {},
  "weekly_subscores": {},
  "trend_subscores": {},
  "confidence": {
    "score": 0.82,
    "data_coverage": 0.90,
    "signal_agreement": 0.78,
    "history_depth": 0.75
  },
  "reasons": [],
  "tone_policy": {
    "primary": "질문",
    "secondary": ["제안"],
    "suppressed": ["훈계"],
    "trigger_patterns": ["P2_insight_but_blocked"],
    "policy_confidence": 0.79
  },
  "needs_professor_review": true
}
```

---

## 6. 코멘트 톤 추천 정책 (패턴 기반)

단순 risk band 기반이 아니라 평가항목 패턴으로 결정:

| 패턴 | 조건 | 기본 톤 |
|---|---|---|
| P1_recovery_seed | 학습 신호는 있으나 실행 전환 약함 | 격려 → 제안 |
| P2_insight_but_blocked | 인과 이해는 높으나 action_translation 낮음 | 질문 → 제안 |
| P3_affective_strain | 헬스체크/정서 저하 + 기록 급락 | 격려 → 질문 |
| P4_repeat_non_execution | 2주 이상 미이행 반복 + confidence 높음 | 훈계(소프트) → 제안 |
| P5_strategy_mismatch | recommended_shift 반복 + relation_type revise/none | 질문 → 제안 |
| P6_stabilizing | L2 2주 연속 하락 + L3 낮음 | 격려 |

훈계 허용 게이트:
1. `risk_band >= High`
2. `confidence >= 0.75`
3. 동일 미이행 패턴 2회 이상
4. `P3_affective_strain`이 아닐 것

---

## 7. 교수 화면/UX 개선

### 7.1 KPI 카드 전환
기존 코멘트량 카드 대신:
- 주간 위험군 회복률
- 고위험 잔여 인원
- 4주 유지율
- 재발률

### 7.2 Risk Queue 중심 화면
- `GET /professor/risk-queue` 기반의 주간 우선순위 큐 제공 (할당/상한 없음)
- 학생 카드에 `risk_score/risk_band/top reasons` 표시
- `다음 고위험 학생` 추천 이동 제공 (선택은 교수 자율)

### 7.3 AI 추천 코멘트
- 톤 탭(격려/제안/질문/훈계)
- 원클릭 삽입 + 교수 최종 수정 후 전송
- 자동 전송 금지

---

## 8. 기술 구현 설계

### 8.1 데이터 모델
1) `comments.comment_type`: `peer | professor`
2) `student_risk_snapshots` (권장)
- `user_id, evaluated_at, l1, l2, l3, risk_score, risk_band, confidence, reasons_json`
3) (선택) `mentor_assignments`

### 8.2 API
- `GET /professor/overview`
- `GET /professor/risk-queue`
- `GET /professor/students/{user_id}/risk-history`
- `POST /professor/students/{user_id}/risk-evaluate`
- `GET /daily-snippets?scope=all` (교수 전용)

### 8.3 계산 정책
- 주간 배치: 전체 학생 L2/L3 재계산
- 이벤트 기반: snippet/playbook 변경 시 L1 즉시 재계산
- L2 급변(+15 이상) 또는 주차 경계 시 L3 재계산

---

## 9. 안전장치

### 9.1 오탐/미탐 완화
- High/Critical은 다중근거(서로 다른 factor 2개+) 필수
- 히스테리시스: 상향 승급 2회 연속 관측 시 확정
- EMA + 2~4주 추세 창으로 노이즈 완화
- low confidence 구간 점수 하향 보정

### 9.2 Human-in-the-loop
- AI는 추천 전용(자동 코멘트 금지)
- `needs_professor_review=true`면 학생 노출 금지
- 교수 override(점수/밴드/톤) 허용 + 사유 저장

### 9.3 금지 표현 정책
- 훈계 톤에서도 인신공격/낙인/수치심 유발 문구 차단
- 기본 우선순위: 격려 > 제안 > 질문 > 훈계

---

## 10. 운영 KPI 및 로드맵

### 10.1 KPI
핵심 KPI:
- 위험도 하락률 (2주 내 High→Medium/Low)
- 회복률 (개입 후 7일 내 작성 재개)
- 4주 유지율
- 재발률
- 교수 코멘트 후 72시간 내 반응률

보조 KPI:
- AI 추천 채택/수정/기각 비율
- 패턴별 정탐률(precision)

### 10.2 단계별 구현
- **Phase 1**: risk model v2 기본 적용(L1/L2), risk-queue, AI 추천 코멘트
- **Phase 2**: L3 추세/재발, risk history, KPI 대시보드
- **Phase 3**: 오탐 피드백 자동 튜닝, 학기 리포트 자동화

---

## 부록: 관련 프롬프트 파일
- `apps/server/prompts/daily_feedback.md`
- `apps/server/prompts/weekly_feedback.md`
- `apps/server/prompts/organize_daily.md`
- `apps/server/prompts/organize_weekly.md`
- `apps/server/prompts/suggest_daily_from_previous.md`

> 운영 원칙 한 줄: 교수 멘토링의 기본 단위는 주간 리뷰이며, 일일 개입은 고위험 학생의 학습 회복이 필요한 경우에만 선택적으로 수행한다.
