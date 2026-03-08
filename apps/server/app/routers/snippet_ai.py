from __future__ import annotations

import json
import logging
from pathlib import Path
from time import perf_counter
from typing import Any, AsyncIterator

from fastapi import HTTPException

from app.core.config import settings
from app.lib.copilot_client import CopilotClient

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
PROMPT_NAMES = [
    "organize_daily.md",
    "suggest_daily_from_previous.md",
    "organize_weekly.md",
    "daily_feedback.md",
    "weekly_feedback.md",
]
_PROMPT_CACHE: dict[str, str] = {}
_TEST_COPILOT_TOKEN_MISSING = "No OAuth token available to request Copilot token"


def _is_test_copilot_token_missing_error(exc: Exception) -> bool:
    return settings.ENVIRONMENT == "test" and _TEST_COPILOT_TOKEN_MISSING in str(exc)


def _build_test_organized_content(content: str) -> str:
    stripped = content.strip() or "(내용 없음)"
    return (
        "### 테스트 환경 AI 정리 결과\n"
        "- 핵심 요약:\n"
        f"  - {stripped}\n"
        "- 다음 액션:\n"
        "  - 핵심 문장을 기준으로 후속 작업을 구체화하세요."
    )


def _build_test_feedback_json(snippet_label: str) -> str:
    return json.dumps(
        {
            "total_score": 75,
            "scores": {
                "record_completeness": {"score": 12, "max_score": 15},
                "learning_signal_detection": {"score": 14, "max_score": 20},
                "cause_effect_connection": {"score": 14, "max_score": 20},
                "action_translation": {"score": 18, "max_score": 25},
                "learning_attitude_consistency": {"score": 17, "max_score": 20},
            },
            "key_learning": f"{snippet_label} 내용을 기반으로 핵심 흐름을 정리했습니다.",
            "learning_sources": ["snippet"],
            "next_action": "핵심 요약을 바탕으로 다음 실행 항목을 1개 이상 작성하세요.",
            "mentor_comment": "테스트 환경 대체 응답입니다. 실제 운영에서는 AI 피드백이 제공됩니다.",
            "next_reflection_mission": "다음 기록에서 실행 결과를 1문장으로 회고하세요.",
            "anchoring_message": "작은 기록의 누적이 큰 성장을 만듭니다.",
            "playbook_update_markdown": "## Action Playbook\n- 다음 실행 항목을 완료 후 결과를 기록하세요.",
        },
        ensure_ascii=False,
    )


def _load_prompt_or_500(prompt_name: str) -> str:
    cached_prompt = _PROMPT_CACHE.get(prompt_name)
    if cached_prompt is not None:
        return cached_prompt

    prompt_path = PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=500, detail="System prompt not found")

    system_prompt = prompt_path.read_text(encoding="utf-8")
    _PROMPT_CACHE[prompt_name] = system_prompt
    return system_prompt


def preload_prompts(prompt_names: list[str] | None = None) -> None:
    for prompt_name in (prompt_names or PROMPT_NAMES):
        _load_prompt_or_500(prompt_name)


async def organize_content_with_ai(
    content: str,
    copilot: CopilotClient,
    prompt_name: str = "organize_daily.md",
    profile_context: dict[str, Any] | None = None,
) -> str:
    chunks: list[str] = []
    async for chunk in organize_content_with_ai_stream(
        content,
        copilot,
        prompt_name=prompt_name,
        profile_context=profile_context,
    ):
        chunks.append(chunk)
    return "".join(chunks)


async def organize_content_with_ai_stream(
    content: str,
    copilot: CopilotClient,
    prompt_name: str = "organize_daily.md",
    profile_context: dict[str, Any] | None = None,
) -> AsyncIterator[str]:
    base_context = dict(profile_context or {})

    prompt_read_start = perf_counter()
    system_prompt = _load_prompt_or_500(prompt_name)
    prompt_read_ms = round((perf_counter() - prompt_read_start) * 1000, 2)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    try:
        chat_start = perf_counter()
        chunk_count = 0
        async for chunk in copilot.chat_stream(
            messages,
            request_meta={
                **base_context,
                "event": "copilot.request",
                "prompt_name": prompt_name,
            },
        ):
            chunk_count += 1
            yield chunk

        chat_elapsed_ms = round((perf_counter() - chat_start) * 1000, 2)
        logger.info(
            "snippet.ai.organize",
            extra={
                **base_context,
                "event": "snippet.ai.organize",
                "status": "ok",
                "prompt_name": prompt_name,
                "input_chars": len(content),
                "prompt_read_ms": prompt_read_ms,
                "chat_elapsed_ms": chat_elapsed_ms,
                "chunk_count": chunk_count,
                "stream": True,
            },
        )
    except Exception as exc:
        if _is_test_copilot_token_missing_error(exc):
            logger.warning(
                "Using test organize fallback due to missing Copilot token",
                extra={
                    **base_context,
                    "event": "snippet.ai.organize",
                    "status": "fallback",
                    "prompt_name": prompt_name,
                    "input_chars": len(content),
                    "prompt_read_ms": prompt_read_ms,
                    "stream": True,
                },
            )
            yield _build_test_organized_content(content)
            return

        logger.exception(
            "AI processing failed",
            extra={
                **base_context,
                "event": "snippet.ai.organize",
                "status": "error",
                "prompt_name": prompt_name,
                "input_chars": len(content),
                "prompt_read_ms": prompt_read_ms,
                "error_type": type(exc).__name__,
                "stream": True,
            },
        )
        raise HTTPException(status_code=502, detail="AI processing failed")


async def generate_feedback_with_ai(
    snippet_content: str,
    playbook_content: str | None,
    copilot: CopilotClient,
    prompt_name: str = "daily_feedback.md",
    snippet_label: str = "Daily Snippet",
    profile_context: dict[str, Any] | None = None,
) -> str:
    base_context = dict(profile_context or {})

    prompt_read_start = perf_counter()
    system_prompt = _load_prompt_or_500(prompt_name)
    prompt_read_ms = round((perf_counter() - prompt_read_start) * 1000, 2)

    user_input = f"{snippet_label}:\n{snippet_content}\n\n"
    if playbook_content:
        user_input += f"My Playbook:\n{playbook_content}"
    else:
        user_input += "My Playbook:\n(No playbook yet)"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        chat_start = perf_counter()
        resp = await copilot.chat(
            messages,
            response_format={"type": "json_object"},
            temperature=0,
            request_meta={
                **base_context,
                "event": "copilot.request",
                "prompt_name": prompt_name,
            },
        )
        chat_elapsed_ms = round((perf_counter() - chat_start) * 1000, 2)
        if not resp or "choices" not in resp or not resp["choices"]:
            raise ValueError("Empty response from AI")

        logger.info(
            "snippet.ai.feedback",
            extra={
                **base_context,
                "event": "snippet.ai.feedback",
                "status": "ok",
                "prompt_name": prompt_name,
                "snippet_chars": len(snippet_content),
                "playbook_chars": len(playbook_content or ""),
                "prompt_read_ms": prompt_read_ms,
                "chat_elapsed_ms": chat_elapsed_ms,
            },
        )
        return resp["choices"][0]["message"]["content"]
    except Exception as exc:
        if _is_test_copilot_token_missing_error(exc):
            logger.warning(
                "Using test feedback fallback due to missing Copilot token",
                extra={
                    **base_context,
                    "event": "snippet.ai.feedback",
                    "status": "fallback",
                    "prompt_name": prompt_name,
                    "prompt_read_ms": prompt_read_ms,
                },
            )
            return _build_test_feedback_json(snippet_label)

        logger.exception(
            "AI feedback generation failed",
            extra={
                **base_context,
                "event": "snippet.ai.feedback",
                "status": "error",
                "prompt_name": prompt_name,
                "prompt_read_ms": prompt_read_ms,
                "error_type": type(exc).__name__,
            },
        )
        raise HTTPException(status_code=502, detail="AI processing failed")


def parse_feedback_json(feedback_json: str) -> dict:
    if not isinstance(feedback_json, str):
        raise ValueError("Feedback JSON must be a string")

    try:
        parsed = json.loads(feedback_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Feedback JSON is invalid") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Feedback JSON must be an object")

    raw_total_score = parsed.get("total_score")
    if raw_total_score is None:
        raise ValueError("Feedback JSON missing total_score")

    try:
        float(raw_total_score)
    except (TypeError, ValueError) as exc:
        raise ValueError("Feedback JSON total_score must be numeric") from exc

    scores = parsed.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Feedback JSON scores must be an object")

    playbook_update = parsed.get("playbook_update_markdown")
    if playbook_update is not None and not isinstance(playbook_update, str):
        raise ValueError("Feedback JSON playbook_update_markdown must be a string")

    parsed["playbook_update_markdown"] = playbook_update
    return parsed
