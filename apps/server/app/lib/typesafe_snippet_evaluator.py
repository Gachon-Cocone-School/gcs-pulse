"""Typed JEV judgments for snippet scores and Playbook update safety."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from app.core.config import settings

try:  # Keep local/test environments usable before the optional dependency is installed.
    from typesafe_sdk import AsyncTypeSafeClient, Choice, Noul, Score
except ImportError:  # pragma: no cover - exercised by deployment configuration
    AsyncTypeSafeClient = Choice = Noul = Score = None


logger = logging.getLogger(__name__)

SCORE_MAXIMA = {
    "record_completeness": 15,
    "learning_signal_detection": 20,
    "cause_effect_connection": 20,
    "action_translation": 25,
    "learning_attitude_consistency": 20,
}

_RUBRIC_SUFFIXES = {
    "record_completeness": "기록의 구체성, 맥락, 결과가 충분한가?",
    "learning_signal_detection": "새롭게 알게 된 점과 학습 신호가 분명한가?",
    "cause_effect_connection": "행동·사건·결과 사이의 인과관계를 설명하는가?",
    "action_translation": "다음에 실행할 구체적이고 검증 가능한 행동으로 옮겼는가?",
    "learning_attitude_consistency": "회고와 실행을 이어 가는 학습 태도가 드러나는가?",
}


@dataclass(frozen=True)
class JevSnippetEvaluation:
    scores: dict[str, dict[str, float | int]]
    playbook_relation: str
    playbook_confidence: float
    playbook_evidence: float
    should_auto_apply_playbook: bool
    model: str


def _enabled() -> bool:
    return bool(settings.TYPESAFE_API_KEY) and settings.ENVIRONMENT != "test" and AsyncTypeSafeClient is not None


def _score_criteria(question: str) -> list[str]:
    return [
        f"0/5: 판단할 근거가 전혀 없다. {question}",
        f"1/5: 단편적인 언급만 있어 매우 부족하다. {question}",
        f"2/5: 일부 근거는 있지만 중요한 맥락이나 구체성이 빠져 있다. {question}",
        f"3/5: 기본 근거가 있어 보통 수준이다. {question}",
        f"4/5: 구체적 근거와 맥락이 충분하다. {question}",
        f"5/5: 검증 가능한 세부사항과 성찰이 명확하고 일관되다. {question}",
    ]


def _scaled_score(raw_score: float, maximum: int) -> int:
    # System One returns an expected rubric level, which can be fractional.
    return max(0, min(maximum, round(raw_score / 5 * maximum)))


async def evaluate_snippet_with_jev(
    *,
    snippet_content: str,
    playbook_content: str | None,
    snippet_kind: str,
) -> JevSnippetEvaluation | None:
    """Return one batched System One judgment, or None without affecting feedback."""
    if not _enabled():
        return None

    questions: dict[str, Any] = {
        key: Score(instructions=question, criteria=_score_criteria(question))
        for key, question in _RUBRIC_SUFFIXES.items()
    }
    questions["playbook_relation"] = Choice(
        instructions=(
            "현재 스니펫이 기존 Playbook과 어떤 관계인지 고르세요. "
            "confirm=현재 Playbook을 뒷받침, revise=기존 항목 수정 필요, "
            "extend=새 항목 추가 필요, none=Playbook이 없거나 판단 근거 부족."
        ),
        criteria={"confirm": None, "revise": None, "extend": None, "none": None},
    )
    questions["playbook_update_supported"] = Noul(
        instructions="이 스니펫만으로 기존 Playbook을 자동 수정 또는 확장할 충분한 직접 근거가 있는가?",
        criteria={
            "true": "기록에 구체적인 행동 또는 결과가 있어 자동 반영해도 된다.",
            "false": "추측, 일반론, 또는 근거 부족이므로 기존 Playbook을 유지해야 한다.",
        },
    )
    state = {
        "snippet_kind": snippet_kind,
        "snippet": snippet_content,
        "current_playbook": playbook_content or "(No playbook yet)",
    }

    try:
        # Pass the app setting explicitly: Pydantic loads apps/server/.env,
        # whereas the SDK itself only consults process environment variables.
        async with AsyncTypeSafeClient(
            api_key=settings.TYPESAFE_API_KEY,
            model=settings.TYPESAFE_MODEL,
        ) as client:
            result = await client.system_one(state, questions)

        scores = {
            key: {
                "score": _scaled_score(float(result.scores[key].score), maximum),
                "max_score": maximum,
                "confidence": round(float(result.scores[key].confidence), 4),
            }
            for key, maximum in SCORE_MAXIMA.items()
        }
        relation = result.choices["playbook_relation"]
        evidence = float(result.nouls["playbook_update_supported"].noul)
        relation_name = str(relation.choice)
        relation_confidence = float(relation.confidence)
        should_auto_apply = (
            bool(playbook_content and playbook_content.strip())
            and relation_name in {"revise", "extend"}
            and relation_confidence >= settings.TYPESAFE_PLAYBOOK_CONFIDENCE_THRESHOLD
            and evidence >= settings.TYPESAFE_PLAYBOOK_EVIDENCE_THRESHOLD
        )
        return JevSnippetEvaluation(
            scores=scores,
            playbook_relation=relation_name,
            playbook_confidence=round(relation_confidence, 4),
            playbook_evidence=round(evidence, 4),
            should_auto_apply_playbook=should_auto_apply,
            model=settings.TYPESAFE_MODEL,
        )
    except Exception:
        # Feedback remains available from Copilot when JEV is temporarily unavailable.
        logger.exception("snippet.jev.evaluation_failed", extra={"snippet_kind": snippet_kind})
        return None


async def enrich_feedback_with_jev(
    feedback: dict[str, Any],
    *,
    snippet_content: str,
    playbook_content: str | None,
    snippet_kind: str,
) -> dict[str, Any]:
    evaluation = await evaluate_snippet_with_jev(
        snippet_content=snippet_content,
        playbook_content=playbook_content,
        snippet_kind=snippet_kind,
    )
    if evaluation is None:
        return feedback

    enriched = dict(feedback)
    enriched["scores"] = evaluation.scores
    enriched["total_score"] = sum(item["score"] for item in evaluation.scores.values())
    enriched["playbook_relation"] = evaluation.playbook_relation
    enriched["jev"] = {
        "model": evaluation.model,
        "score_confidence": {
            key: score["confidence"] for key, score in evaluation.scores.items()
        },
        "playbook_confidence": evaluation.playbook_confidence,
        "playbook_evidence": evaluation.playbook_evidence,
        "playbook_auto_apply": evaluation.should_auto_apply_playbook,
    }

    if not evaluation.should_auto_apply_playbook:
        # No review queue: uncertain or weakly evidenced proposals simply do not change the Playbook.
        enriched["playbook_update_markdown"] = None
    return enriched
