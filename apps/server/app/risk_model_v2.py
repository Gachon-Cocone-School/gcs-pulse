from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import pstdev

from app.models import DailySnippet, WeeklySnippet


DAILY_SCORE_MAX = {
    "record_completeness": 15.0,
    "learning_signal_detection": 25.0,
    "cause_effect_connection": 20.0,
    "action_translation": 20.0,
    "learning_attitude_consistency": 20.0,
}

WEEKLY_SCORE_MAX = {
    "record_completeness": 15.0,
    "learning_signal_detection": 25.0,
    "cause_effect_connection": 20.0,
    "action_translation": 20.0,
    "learning_attitude_consistency": 20.0,
}

RISK_BANDS: list[tuple[str, float, float]] = [
    ("Low", 0.0, 29.999),
    ("Medium", 30.0, 59.999),
    ("High", 60.0, 79.999),
    ("Critical", 80.0, 100.0),
]


@dataclass
class RiskEvaluationResult:
    l1: float
    l2: float
    l3: float
    risk_score: float
    risk_band: str
    daily_subscores: dict
    weekly_subscores: dict
    trend_subscores: dict
    confidence: dict
    reasons: list[dict]
    tone_policy: dict
    needs_professor_review: bool


@dataclass
class _ParsedDaily:
    snippet: DailySnippet
    feedback: dict


@dataclass
class _ParsedWeekly:
    snippet: WeeklySnippet
    feedback: dict


def evaluate_student_risk_v2(
    *,
    daily_snippets: list[DailySnippet],
    weekly_snippets: list[WeeklySnippet],
    recent_l2_history: list[float] | None = None,
    recovered_count_4w: int = 0,
    relapse_count_4w: int = 0,
    today: date | None = None,
) -> RiskEvaluationResult:
    parsed_daily = _parse_daily_feedbacks(daily_snippets)
    parsed_weekly = _parse_weekly_feedbacks(weekly_snippets)

    l1, daily_subscores, daily_reason_inputs = _compute_l1(parsed_daily, daily_snippets)
    l2, weekly_subscores, weekly_reason_inputs = _compute_l2(parsed_weekly, parsed_daily)

    l2_history = [float(v) for v in (recent_l2_history or []) if isinstance(v, (int, float))]
    if l2 > 0:
        l2_history.append(l2)
    l3, trend_subscores, trend_reason_inputs = _compute_l3(
        l2_history=l2_history,
        recovered_count_4w=recovered_count_4w,
        relapse_count_4w=relapse_count_4w,
    )

    l1_recent = _ema(_recent_values([l1], window=3), alpha=0.6)
    raw_risk = 0.40 * l1_recent + 0.35 * l2 + 0.25 * l3

    data_coverage = _compute_data_coverage(parsed_daily, parsed_weekly)
    signal_agreement = _compute_signal_agreement(l1, l2, l3)
    history_depth = _compute_history_depth(l2_history)
    confidence_score = _clip01(0.50 * data_coverage + 0.30 * signal_agreement + 0.20 * history_depth)

    risk_score = _clip(raw_risk - 8 * (1 - confidence_score), 0.0, 100.0)
    risk_band = _risk_band(risk_score)

    reasons = _build_reasons(
        l1=l1,
        l2=l2,
        l3=l3,
        daily_reason_inputs=daily_reason_inputs,
        weekly_reason_inputs=weekly_reason_inputs,
        trend_reason_inputs=trend_reason_inputs,
    )

    tone_policy = _derive_tone_policy(
        l1=l1,
        l2=l2,
        l3=l3,
        risk_band=risk_band,
        confidence=confidence_score,
        daily_subscores=daily_subscores,
        weekly_subscores=weekly_subscores,
        trend_subscores=trend_subscores,
    )

    needs_professor_review = risk_band in {"High", "Critical"}

    return RiskEvaluationResult(
        l1=round(l1, 2),
        l2=round(l2, 2),
        l3=round(l3, 2),
        risk_score=round(risk_score, 2),
        risk_band=risk_band,
        daily_subscores=daily_subscores,
        weekly_subscores=weekly_subscores,
        trend_subscores=trend_subscores,
        confidence={
            "score": round(confidence_score, 4),
            "data_coverage": round(data_coverage, 4),
            "signal_agreement": round(signal_agreement, 4),
            "history_depth": round(history_depth, 4),
        },
        reasons=reasons,
        tone_policy=tone_policy,
        needs_professor_review=needs_professor_review,
    )


def _parse_daily_feedbacks(snippets: list[DailySnippet]) -> list[_ParsedDaily]:
    items: list[_ParsedDaily] = []
    for snippet in snippets:
        parsed = _parse_feedback_json(snippet.feedback)
        if parsed:
            items.append(_ParsedDaily(snippet=snippet, feedback=parsed))
    items.sort(key=lambda item: item.snippet.date)
    return items


def _parse_weekly_feedbacks(snippets: list[WeeklySnippet]) -> list[_ParsedWeekly]:
    items: list[_ParsedWeekly] = []
    for snippet in snippets:
        parsed = _parse_feedback_json(snippet.feedback)
        if parsed:
            items.append(_ParsedWeekly(snippet=snippet, feedback=parsed))
    items.sort(key=lambda item: item.snippet.week)
    return items


def _parse_feedback_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except Exception:
        return None
    if not isinstance(parsed, dict):
        return None
    return parsed


def _compute_l1(
    parsed_daily: list[_ParsedDaily],
    all_daily: list[DailySnippet],
) -> tuple[float, dict, dict]:
    if not parsed_daily:
        return (
            70.0,
            {
                "rubric_risk": 0.7,
                "m_daily_structure_gap": 1.0,
                "m_frequency_gap": 1.0,
                "m_affective_strain": 0.6,
            },
            {
                "deltas": {
                    "record_completeness": 0.8,
                    "learning_signal_detection": 0.8,
                    "cause_effect_connection": 0.8,
                    "action_translation": 0.8,
                    "learning_attitude_consistency": 0.8,
                },
                "m_daily_structure_gap": 1.0,
                "m_frequency_gap": 1.0,
                "m_affective_strain": 0.6,
            },
        )

    latest = parsed_daily[-1]
    deltas = _extract_rubric_deltas(latest.feedback, DAILY_SCORE_MAX)

    m_daily_structure_gap = _measure_daily_structure_gap(latest.snippet.content)
    m_frequency_gap = _measure_frequency_gap(all_daily)
    m_affective_strain = _measure_affective_strain(parsed_daily)

    l1 = 100.0 * _clip01(
        0.12 * deltas["record_completeness"]
        + 0.14 * deltas["learning_signal_detection"]
        + 0.16 * deltas["cause_effect_connection"]
        + 0.17 * deltas["action_translation"]
        + 0.16 * deltas["learning_attitude_consistency"]
        + 0.10 * m_daily_structure_gap
        + 0.10 * m_frequency_gap
        + 0.05 * m_affective_strain
    )

    return (
        l1,
        {
            "rubric_risk": round(
                0.12 * deltas["record_completeness"]
                + 0.14 * deltas["learning_signal_detection"]
                + 0.16 * deltas["cause_effect_connection"]
                + 0.17 * deltas["action_translation"]
                + 0.16 * deltas["learning_attitude_consistency"],
                4,
            ),
            "m_daily_structure_gap": round(m_daily_structure_gap, 4),
            "m_frequency_gap": round(m_frequency_gap, 4),
            "m_affective_strain": round(m_affective_strain, 4),
        },
        {
            "deltas": deltas,
            "m_daily_structure_gap": m_daily_structure_gap,
            "m_frequency_gap": m_frequency_gap,
            "m_affective_strain": m_affective_strain,
            "latest_daily_feedback": latest.feedback,
        },
    )


def _compute_l2(
    parsed_weekly: list[_ParsedWeekly],
    parsed_daily: list[_ParsedDaily],
) -> tuple[float, dict, dict]:
    if not parsed_weekly:
        return (
            65.0,
            {
                "weekly_rubric_risk": 0.65,
                "m_strategy_drift": 0.8,
                "m_action_carryover": 0.7,
                "m_daily_instability": 0.6,
            },
            {
                "deltas": {
                    "record_completeness": 0.75,
                    "learning_signal_detection": 0.75,
                    "cause_effect_connection": 0.75,
                    "action_translation": 0.75,
                    "learning_attitude_consistency": 0.75,
                },
                "m_strategy_drift": 0.8,
                "m_action_carryover": 0.7,
                "m_daily_instability": 0.6,
                "latest_weekly_feedback": {},
            },
        )

    latest = parsed_weekly[-1]
    deltas = _extract_rubric_deltas(latest.feedback, WEEKLY_SCORE_MAX)

    weekly_rubric_risk = (
        0.15 * deltas["record_completeness"]
        + 0.20 * deltas["learning_signal_detection"]
        + 0.20 * deltas["cause_effect_connection"]
        + 0.20 * deltas["action_translation"]
        + 0.25 * deltas["learning_attitude_consistency"]
    )

    m_strategy_drift = _measure_strategy_drift(parsed_weekly)
    m_action_carryover = _measure_action_carryover(parsed_daily, parsed_weekly)
    m_daily_instability = _measure_daily_instability(parsed_daily)

    l2 = 100.0 * _clip01(
        0.40 * weekly_rubric_risk
        + 0.30 * m_strategy_drift
        + 0.20 * m_action_carryover
        + 0.10 * m_daily_instability
    )

    return (
        l2,
        {
            "weekly_rubric_risk": round(weekly_rubric_risk, 4),
            "m_strategy_drift": round(m_strategy_drift, 4),
            "m_action_carryover": round(m_action_carryover, 4),
            "m_daily_instability": round(m_daily_instability, 4),
        },
        {
            "deltas": deltas,
            "m_strategy_drift": m_strategy_drift,
            "m_action_carryover": m_action_carryover,
            "m_daily_instability": m_daily_instability,
            "latest_weekly_feedback": latest.feedback,
        },
    )


def _compute_l3(
    *,
    l2_history: list[float],
    recovered_count_4w: int,
    relapse_count_4w: int,
) -> tuple[float, dict, dict]:
    if len(l2_history) < 1:
        default = {
            "m_trend_accel": 0.0,
            "m_trend_slope_4w": 0.0,
            "m_trend_volatility": 0.0,
            "m_relapse_rate": 0.0,
        }
        return 0.0, default, default

    history = l2_history[-4:]
    current = history[-1]

    if len(history) >= 3:
        baseline = sum(history[-3:-1]) / 2.0
    elif len(history) == 2:
        baseline = history[0]
    else:
        baseline = history[-1]

    m_trend_accel = _clip01((current - baseline) / 25.0)

    if len(history) >= 4:
        m_trend_slope_4w = _clip01((history[-1] - history[0]) / 40.0)
        volatility_source = history
    elif len(history) >= 2:
        m_trend_slope_4w = _clip01((history[-1] - history[0]) / 40.0)
        volatility_source = history
    else:
        m_trend_slope_4w = 0.0
        volatility_source = history

    m_trend_volatility = _clip01((pstdev(volatility_source) if len(volatility_source) > 1 else 0.0) / 20.0)
    m_relapse_rate = _clip01(relapse_count_4w / max(1, recovered_count_4w))

    l3 = 100.0 * _clip01(
        0.40 * m_trend_accel
        + 0.30 * m_trend_slope_4w
        + 0.20 * m_trend_volatility
        + 0.10 * m_relapse_rate
    )

    trend = {
        "m_trend_accel": round(m_trend_accel, 4),
        "m_trend_slope_4w": round(m_trend_slope_4w, 4),
        "m_trend_volatility": round(m_trend_volatility, 4),
        "m_relapse_rate": round(m_relapse_rate, 4),
    }
    return l3, trend, trend


def _extract_rubric_deltas(feedback: dict, max_scores: dict[str, float]) -> dict[str, float]:
    scores = feedback.get("scores") if isinstance(feedback, dict) else {}
    if not isinstance(scores, dict):
        scores = {}

    deltas: dict[str, float] = {}
    for key, max_score in max_scores.items():
        payload = scores.get(key)
        if isinstance(payload, dict):
            score = _to_float(payload.get("score"), default=max_score * 0.5)
            payload_max = _to_float(payload.get("max_score"), default=max_score)
            if payload_max <= 0:
                payload_max = max_score
        else:
            score = max_score * 0.5
            payload_max = max_score

        normalized = 1.0 - (score / payload_max)
        deltas[key] = _clip01(normalized)

    return deltas


def _measure_daily_structure_gap(content: str | None) -> float:
    if not content or not content.strip():
        return 1.0

    required_markers = [
        "오늘",
        "목적",
        "하이라이트",
        "로우라이트",
        "우선순위",
        "팀",
        "배움",
        "헬스",
    ]
    lowered = content.lower()
    misses = 0
    for marker in required_markers:
        if marker.lower() not in lowered:
            misses += 1
    return _clip01(misses / len(required_markers))


def _measure_frequency_gap(all_daily: list[DailySnippet]) -> float:
    if not all_daily:
        return 1.0

    dates = sorted({snippet.date for snippet in all_daily})
    if not dates:
        return 1.0

    end_date = dates[-1]
    start_date = end_date - timedelta(days=6)
    in_window = [d for d in dates if start_date <= d <= end_date]
    coverage = len(in_window) / 7.0

    max_streak_gap = 0
    if in_window:
        prev = in_window[0]
        for current in in_window[1:]:
            diff = (current - prev).days - 1
            if diff > max_streak_gap:
                max_streak_gap = diff
            prev = current
        leading_gap = max(0, (in_window[0] - start_date).days)
        trailing_gap = max(0, (end_date - in_window[-1]).days)
        max_streak_gap = max(max_streak_gap, leading_gap, trailing_gap)

    streak_penalty = _clip01(max_streak_gap / 3.0)
    return _clip01((1 - coverage) * 0.7 + streak_penalty * 0.3)


def _extract_health_score(content: str | None) -> float | None:
    if not content:
        return None
    candidates = []
    token = "헬스"
    for line in content.splitlines():
        if token in line:
            digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in line)
            for part in digits.split():
                try:
                    value = float(part)
                except ValueError:
                    continue
                if 0 <= value <= 10:
                    candidates.append(value)
    if not candidates:
        return None
    return candidates[-1]


def _measure_affective_strain(parsed_daily: list[_ParsedDaily]) -> float:
    if not parsed_daily:
        return 0.6

    latest_feedback = parsed_daily[-1].feedback
    learning_sources = latest_feedback.get("learning_sources")
    source_penalty = 0.0
    if isinstance(learning_sources, list):
        lowered = {str(item).strip().lower() for item in learning_sources}
        if "emotion" in lowered or "energy" in lowered:
            source_penalty += 0.2

    health_scores = [
        score for score in (_extract_health_score(item.snippet.content) for item in parsed_daily[-5:]) if score is not None
    ]
    if health_scores:
        latest_health = health_scores[-1]
        avg_health = sum(health_scores) / len(health_scores)
        low_health = _clip01((6.0 - latest_health) / 6.0)
        drop = _clip01((avg_health - latest_health) / 4.0)
        health_penalty = _clip01(0.7 * low_health + 0.3 * drop)
    else:
        health_penalty = 0.4

    return _clip01(health_penalty + source_penalty)


def _measure_strategy_drift(parsed_weekly: list[_ParsedWeekly]) -> float:
    if not parsed_weekly:
        return 0.8

    recent = parsed_weekly[-3:]
    drift_points = 0.0
    max_points = max(1, len(recent))

    for item in recent:
        feedback = item.feedback
        strategy_linkage = feedback.get("strategy_linkage") if isinstance(feedback, dict) else None
        if isinstance(strategy_linkage, dict):
            shift = str(strategy_linkage.get("recommended_shift") or "").strip()
            confidence = str(strategy_linkage.get("confidence") or "").strip().lower()
            if shift:
                drift_points += 0.5
            if confidence == "high":
                drift_points += 0.2

        relation = feedback.get("playbook_relation") if isinstance(feedback, dict) else None
        if isinstance(relation, dict):
            relation_type = str(relation.get("relation_type") or "").strip().lower()
            if relation_type in {"revise", "none"}:
                drift_points += 0.5

    return _clip01(drift_points / (max_points * 1.2))


def _measure_action_carryover(
    parsed_daily: list[_ParsedDaily],
    parsed_weekly: list[_ParsedWeekly],
) -> float:
    flags: list[int] = []

    for item in parsed_daily[-7:]:
        next_action = str(item.feedback.get("next_action") or "").strip().lower()
        lowlight = str(item.feedback.get("key_learning") or "").strip().lower()
        stale = int((not next_action) or ("내일" in lowlight and "실행" not in next_action))
        flags.append(stale)

    for item in parsed_weekly[-2:]:
        next_action = str(item.feedback.get("next_action") or "").strip().lower()
        strategy_linkage = item.feedback.get("strategy_linkage") if isinstance(item.feedback, dict) else None
        shift = ""
        if isinstance(strategy_linkage, dict):
            shift = str(strategy_linkage.get("recommended_shift") or "").strip().lower()
        stale = int((not next_action) or (bool(shift) and shift in next_action))
        flags.append(stale)

    if not flags:
        return 0.7

    return _clip01(sum(flags) / len(flags))


def _measure_daily_instability(parsed_daily: list[_ParsedDaily]) -> float:
    if len(parsed_daily) < 2:
        return 0.5

    scores: list[float] = []
    for item in parsed_daily[-7:]:
        deltas = _extract_rubric_deltas(item.feedback, DAILY_SCORE_MAX)
        val = (
            0.12 * deltas["record_completeness"]
            + 0.14 * deltas["learning_signal_detection"]
            + 0.16 * deltas["cause_effect_connection"]
            + 0.17 * deltas["action_translation"]
            + 0.16 * deltas["learning_attitude_consistency"]
        )
        scores.append(100.0 * _clip01(val))

    if len(scores) < 2:
        return 0.5

    return _clip01(pstdev(scores) / 20.0)


def _compute_data_coverage(parsed_daily: list[_ParsedDaily], parsed_weekly: list[_ParsedWeekly]) -> float:
    daily_cov = _clip01(len(parsed_daily[-7:]) / 7.0)
    weekly_cov = _clip01(len(parsed_weekly[-4:]) / 4.0)
    return _clip01(0.7 * daily_cov + 0.3 * weekly_cov)


def _compute_signal_agreement(l1: float, l2: float, l3: float) -> float:
    spread = max(l1, l2, l3) - min(l1, l2, l3)
    return _clip01(1.0 - (spread / 100.0))


def _compute_history_depth(l2_history: list[float]) -> float:
    return _clip01(len(l2_history[-4:]) / 4.0)


def _build_reasons(
    *,
    l1: float,
    l2: float,
    l3: float,
    daily_reason_inputs: dict,
    weekly_reason_inputs: dict,
    trend_reason_inputs: dict,
) -> list[dict]:
    reasons: list[dict] = []

    daily_deltas = daily_reason_inputs.get("deltas", {})
    weekly_deltas = weekly_reason_inputs.get("deltas", {})

    if daily_deltas.get("record_completeness", 0) >= 0.4 or daily_reason_inputs.get("m_daily_structure_gap", 0) >= 0.4:
        impact = round(
            100
            * (
                0.12 * daily_deltas.get("record_completeness", 0)
                + 0.10 * daily_reason_inputs.get("m_daily_structure_gap", 0)
            ),
            2,
        )
        reasons.append(
            {
                "layer": "L1",
                "risk_factor": "RF1_execution_continuity",
                "prompt_items": ["record_completeness"],
                "severity": _severity_from_impact(impact),
                "impact": impact,
                "evidence": "일간 기록 완성도 또는 구조 결손 비율이 높습니다.",
                "why_it_matters": "기록 연속성이 깨지면 회복 루틴이 약해집니다.",
            }
        )

    if daily_deltas.get("action_translation", 0) >= 0.45 or weekly_deltas.get("action_translation", 0) >= 0.45:
        impact = round(
            100
            * (
                0.17 * daily_deltas.get("action_translation", 0)
                + 0.20 * weekly_deltas.get("action_translation", 0)
            ),
            2,
        )
        reasons.append(
            {
                "layer": "L1" if impact < 14 else "L2",
                "risk_factor": "RF4_actionability",
                "prompt_items": ["action_translation", "next_action", "다음주 주요 할 일"],
                "severity": _severity_from_impact(impact),
                "impact": impact,
                "evidence": "회고가 다음 실행으로 충분히 연결되지 않았습니다.",
                "why_it_matters": "행동 전환이 약하면 학습 신호가 누적되지 않습니다.",
            }
        )

    if weekly_reason_inputs.get("m_strategy_drift", 0) >= 0.45:
        impact = round(100 * (0.30 * weekly_reason_inputs.get("m_strategy_drift", 0)), 2)
        reasons.append(
            {
                "layer": "L2",
                "risk_factor": "RF8_strategy_drift",
                "prompt_items": ["strategy_linkage.weekly_signal", "playbook_relation.relation_type"],
                "severity": _severity_from_impact(impact),
                "impact": impact,
                "evidence": "전략 재정렬 신호가 반복되고 있습니다.",
                "why_it_matters": "전략 불일치가 누적되면 실행 실패 확률이 증가합니다.",
            }
        )

    if daily_reason_inputs.get("m_affective_strain", 0) >= 0.5:
        impact = round(100 * (0.05 * daily_reason_inputs.get("m_affective_strain", 0)), 2)
        reasons.append(
            {
                "layer": "L1",
                "risk_factor": "RF7_affective_strain",
                "prompt_items": ["learning_sources", "헬스 체크 (10점)", "emotion", "energy"],
                "severity": _severity_from_impact(impact),
                "impact": impact,
                "evidence": "정서/에너지 저하와 컨디션 하락 신호가 감지되었습니다.",
                "why_it_matters": "정서적 부담이 커지면 실행 지속성이 급격히 낮아질 수 있습니다.",
            }
        )

    if trend_reason_inputs.get("m_trend_accel", 0) >= 0.45 or trend_reason_inputs.get("m_relapse_rate", 0) >= 0.35:
        impact = round(
            100
            * (
                0.40 * trend_reason_inputs.get("m_trend_accel", 0)
                + 0.10 * trend_reason_inputs.get("m_relapse_rate", 0)
            ),
            2,
        )
        reasons.append(
            {
                "layer": "L3",
                "risk_factor": "RF9_trend_relapse",
                "prompt_items": ["주차별 L2 이력"],
                "severity": _severity_from_impact(impact),
                "impact": impact,
                "evidence": "최근 주차에서 위험도 악화 가속 또는 재발 신호가 관찰됩니다.",
                "why_it_matters": "추세 악화는 단기 개입 지연 시 이탈로 이어질 가능성이 큽니다.",
            }
        )

    if not reasons:
        fallback_impact = round(max(l1, l2, l3) * 0.12, 2)
        reasons.append(
            {
                "layer": "L2",
                "risk_factor": "RF2_reflection_depth",
                "prompt_items": ["learning_signal_detection", "cause_effect_connection"],
                "severity": _severity_from_impact(fallback_impact),
                "impact": fallback_impact,
                "evidence": "핵심 위험 신호는 경미하지만 회고 깊이 개선 여지가 있습니다.",
                "why_it_matters": "회고 품질을 높이면 위험 전이를 조기에 차단할 수 있습니다.",
            }
        )

    reasons.sort(key=lambda item: item.get("impact", 0), reverse=True)
    return reasons[:5]


def _derive_tone_policy(
    *,
    l1: float,
    l2: float,
    l3: float,
    risk_band: str,
    confidence: float,
    daily_subscores: dict,
    weekly_subscores: dict,
    trend_subscores: dict,
) -> dict:
    trigger_patterns: list[str] = []

    if daily_subscores.get("m_affective_strain", 0) >= 0.5:
        trigger_patterns.append("P3_affective_strain")
    elif weekly_subscores.get("m_strategy_drift", 0) >= 0.45:
        trigger_patterns.append("P5_strategy_mismatch")
    elif weekly_subscores.get("m_action_carryover", 0) >= 0.5:
        trigger_patterns.append("P2_insight_but_blocked")
    elif trend_subscores.get("m_trend_slope_4w", 0) <= 0.25 and l2 < 50:
        trigger_patterns.append("P6_stabilizing")
    elif daily_subscores.get("rubric_risk", 0) >= 0.55 and weekly_subscores.get("m_action_carryover", 0) >= 0.4:
        trigger_patterns.append("P4_repeat_non_execution")
    else:
        trigger_patterns.append("P1_recovery_seed")

    primary = "질문"
    secondary = ["제안"]
    suppressed = ["훈계"]

    pattern = trigger_patterns[0]
    if pattern == "P1_recovery_seed":
        primary = "격려"
        secondary = ["제안"]
    elif pattern == "P2_insight_but_blocked":
        primary = "질문"
        secondary = ["제안"]
    elif pattern == "P3_affective_strain":
        primary = "격려"
        secondary = ["질문"]
        suppressed = ["훈계"]
    elif pattern == "P4_repeat_non_execution":
        primary = "훈계"
        secondary = ["제안"]
    elif pattern == "P5_strategy_mismatch":
        primary = "질문"
        secondary = ["제안"]
    elif pattern == "P6_stabilizing":
        primary = "격려"
        secondary = []

    allow_soft_discipline = (
        risk_band in {"High", "Critical"}
        and confidence >= 0.75
        and pattern == "P4_repeat_non_execution"
        and "P3_affective_strain" not in trigger_patterns
    )

    if allow_soft_discipline:
        suppressed = []
    elif "훈계" not in suppressed:
        suppressed.append("훈계")

    policy_confidence = _clip01(
        0.35 * confidence
        + 0.25 * _clip01(max(l1, l2, l3) / 100.0)
        + 0.40 * (1.0 if trigger_patterns else 0.5)
    )

    return {
        "primary": primary,
        "secondary": secondary,
        "suppressed": suppressed,
        "trigger_patterns": trigger_patterns,
        "policy_confidence": round(policy_confidence, 4),
    }


def _severity_from_impact(impact: float) -> str:
    if impact >= 15:
        return "high"
    if impact >= 7:
        return "medium"
    return "low"


def _risk_band(score: float) -> str:
    for name, lower, upper in RISK_BANDS:
        if lower <= score <= upper:
            return name
    return "Critical" if score > 100 else "Low"


def _ema(values: list[float], alpha: float) -> float:
    if not values:
        return 0.0
    result = values[0]
    for value in values[1:]:
        result = alpha * value + (1 - alpha) * result
    return result


def _recent_values(values: list[float], window: int) -> list[float]:
    if window <= 0:
        return values
    return values[-window:]


def _to_float(value, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if math.isnan(number) or math.isinf(number):
        return default
    return number


def _clip01(value: float) -> float:
    return _clip(value, 0.0, 1.0)


def _clip(value: float, low: float, high: float) -> float:
    if value < low:
        return low
    if value > high:
        return high
    return value
