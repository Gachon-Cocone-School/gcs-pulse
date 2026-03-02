import json
from datetime import date
from types import SimpleNamespace

from app.risk_model_v2 import evaluate_student_risk_v2


def _daily(day: date, content: str, feedback: dict):
    return SimpleNamespace(
        date=day,
        content=content,
        feedback=json.dumps(feedback),
    )


def _weekly(week: date, content: str, feedback: dict):
    return SimpleNamespace(
        week=week,
        content=content,
        feedback=json.dumps(feedback),
    )


def _feedback(scores: dict[str, tuple[float, float]], **extra):
    payload = {
        "scores": {
            key: {"score": score, "max_score": max_score}
            for key, (score, max_score) in scores.items()
        },
        "learning_sources": ["insight"],
        "strategy_linkage": {
            "recommended_shift": "",
            "confidence": "low",
            "weekly_signal": "stable",
        },
        "playbook_relation": {"relation_type": "maintain"},
        "next_action": "내일 실행할 작업 1개",
        "key_learning": "오늘 배운 점",
    }
    payload.update(extra)
    return payload


def test_risk_model_v2_returns_expected_shape_with_empty_input():
    result = evaluate_student_risk_v2(daily_snippets=[], weekly_snippets=[])

    assert 0.0 <= result.risk_score <= 100.0
    assert result.risk_band in {"Low", "Medium", "High", "Critical"}
    assert {"score", "data_coverage", "signal_agreement", "history_depth"} <= set(result.confidence.keys())
    assert isinstance(result.reasons, list)
    assert isinstance(result.tone_policy, dict)


def test_risk_model_v2_higher_risk_for_low_quality_signals():
    high_daily = [
        _daily(
            date(2026, 2, 25),
            "",
            _feedback(
                {
                    "record_completeness": (2, 15),
                    "learning_signal_detection": (3, 25),
                    "cause_effect_connection": (2, 20),
                    "action_translation": (2, 20),
                    "learning_attitude_consistency": (2, 20),
                },
                learning_sources=["emotion"],
                key_learning="내일도 막막",
                next_action="",
            ),
        )
    ]
    high_weekly = [
        _weekly(
            date(2026, 2, 24),
            "",
            _feedback(
                {
                    "record_completeness": (2, 15),
                    "learning_signal_detection": (4, 25),
                    "cause_effect_connection": (3, 20),
                    "action_translation": (2, 20),
                    "learning_attitude_consistency": (3, 20),
                },
                strategy_linkage={
                    "recommended_shift": "전략 전환 필요",
                    "confidence": "high",
                    "weekly_signal": "unstable",
                },
                playbook_relation={"relation_type": "revise"},
                next_action="",
            ),
        )
    ]

    low_content = "\n".join(
        [
            "오늘 목표: 학습 유지",
            "목적: 핵심 개념 복습",
            "하이라이트: 문제 3개 해결",
            "로우라이트: 시간 관리 미흡",
            "우선순위: 핵심 과제",
            "팀 협업: 코드 리뷰 완료",
            "배움: 원인-결과 연결 개선",
            "헬스 체크 (10점): 8",
        ]
    )
    low_daily = [
        _daily(
            date(2026, 2, 25),
            low_content,
            _feedback(
                {
                    "record_completeness": (14, 15),
                    "learning_signal_detection": (23, 25),
                    "cause_effect_connection": (18, 20),
                    "action_translation": (18, 20),
                    "learning_attitude_consistency": (18, 20),
                },
                learning_sources=["insight"],
                next_action="내일 동일 루틴 유지",
            ),
        )
    ]
    low_weekly = [
        _weekly(
            date(2026, 2, 24),
            "주간 회고 및 실행 계획",
            _feedback(
                {
                    "record_completeness": (14, 15),
                    "learning_signal_detection": (22, 25),
                    "cause_effect_connection": (18, 20),
                    "action_translation": (18, 20),
                    "learning_attitude_consistency": (19, 20),
                },
                strategy_linkage={
                    "recommended_shift": "",
                    "confidence": "low",
                    "weekly_signal": "stable",
                },
                playbook_relation={"relation_type": "maintain"},
            ),
        )
    ]

    high = evaluate_student_risk_v2(daily_snippets=high_daily, weekly_snippets=high_weekly)
    low = evaluate_student_risk_v2(daily_snippets=low_daily, weekly_snippets=low_weekly)

    assert high.risk_score > low.risk_score
    assert high.l1 > low.l1
    assert high.l2 > low.l2


def test_risk_model_v2_l3_increases_with_relapse_and_acceleration():
    base_daily = [
        _daily(
            date(2026, 2, 25),
            "오늘 목표\n목적\n하이라이트\n로우라이트\n우선순위\n팀\n배움\n헬스 체크 (10점): 7",
            _feedback(
                {
                    "record_completeness": (10, 15),
                    "learning_signal_detection": (15, 25),
                    "cause_effect_connection": (12, 20),
                    "action_translation": (12, 20),
                    "learning_attitude_consistency": (12, 20),
                }
            ),
        )
    ]
    base_weekly = [
        _weekly(
            date(2026, 2, 24),
            "주간 회고",
            _feedback(
                {
                    "record_completeness": (10, 15),
                    "learning_signal_detection": (15, 25),
                    "cause_effect_connection": (12, 20),
                    "action_translation": (12, 20),
                    "learning_attitude_consistency": (12, 20),
                }
            ),
        )
    ]

    stable = evaluate_student_risk_v2(
        daily_snippets=base_daily,
        weekly_snippets=base_weekly,
        recent_l2_history=[35.0, 36.0, 34.0],
        recovered_count_4w=2,
        relapse_count_4w=0,
    )
    relapse = evaluate_student_risk_v2(
        daily_snippets=base_daily,
        weekly_snippets=base_weekly,
        recent_l2_history=[35.0, 55.0, 80.0],
        recovered_count_4w=1,
        relapse_count_4w=2,
    )

    assert relapse.l3 > stable.l3
    assert relapse.risk_score >= stable.risk_score


def test_risk_model_v2_derives_affective_tone_policy():
    daily = [
        _daily(
            date(2026, 2, 25),
            "오늘 목표\n목적\n하이라이트\n로우라이트\n우선순위\n팀\n배움\n헬스 체크 (10점): 2",
            _feedback(
                {
                    "record_completeness": (8, 15),
                    "learning_signal_detection": (10, 25),
                    "cause_effect_connection": (9, 20),
                    "action_translation": (8, 20),
                    "learning_attitude_consistency": (8, 20),
                },
                learning_sources=["emotion", "energy"],
            ),
        )
    ]
    weekly = [
        _weekly(
            date(2026, 2, 24),
            "주간 회고",
            _feedback(
                {
                    "record_completeness": (9, 15),
                    "learning_signal_detection": (11, 25),
                    "cause_effect_connection": (10, 20),
                    "action_translation": (9, 20),
                    "learning_attitude_consistency": (9, 20),
                }
            ),
        )
    ]

    result = evaluate_student_risk_v2(daily_snippets=daily, weekly_snippets=weekly)

    assert "P3_affective_strain" in result.tone_policy["trigger_patterns"]
    assert result.tone_policy["primary"] == "격려"
    assert "훈계" in result.tone_policy["suppressed"]
