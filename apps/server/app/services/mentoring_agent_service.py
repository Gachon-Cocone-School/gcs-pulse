from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Awaitable, Callable

from app.core.config import settings

try:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        query,
    )
except ModuleNotFoundError:  # pragma: no cover
    AssistantMessage = object
    ResultMessage = object
    TextBlock = object
    ClaudeAgentOptions = None
    query = None

SYSTEM_PROMPT = """
당신은 대학 교수의 멘토링 보조 AI입니다.

규칙:
- 반드시 한국어로 답변한다.
- 답변은 마크다운으로 작성한다.
- 근거 없이 단정하지 않는다.
- 학생 개인정보를 과도하게 노출하지 않는다.
- 코멘트 '등록'은 제안만 하고, 실행은 항상 교수 승인 후라는 점을 명시한다.
""".strip()

MEMORY_SYSTEM_PROMPT = """
당신은 교수 멘토링 메모리 병합기입니다.
입력으로 기존 메모리와 최신 대화가 주어지면, 향후 멘토링에 필요한 핵심 인사이트만 한국어 마크다운 bullet로 갱신하세요.
제약:
- 중복 제거
- 사실/관찰/추천 액션 중심
- 장황한 서술 금지
""".strip()


@dataclass
class MentoringAgentResult:
    content_markdown: str
    tool_calls: list[dict[str, Any]]
    latency_ms: int
    tokens_input: int | None = None
    tokens_output: int | None = None


class MentoringAgentService:
    def __init__(self) -> None:
        self.api_key = settings.CLAUDE_API_KEY
        self.base_url = settings.CLAUDE_API_BASE_URL
        self.model = settings.CLAUDE_MODEL or "claude-opus-4-6"
        self.cwd = str(Path(__file__).resolve().parents[2])

    def _build_user_prompt(self, *, user_message: str, memory_markdown: str) -> str:
        memory = memory_markdown.strip() or "(저장된 메모리 없음)"
        return (
            "[교수 메모리]\n"
            f"{memory}\n\n"
            "[교수 요청]\n"
            f"{user_message}\n\n"
            "요청을 분석해 실행 가능한 제안과 근거를 간결히 제시하세요."
        )

    def _build_options(self, *, system_prompt: str, include_partial_messages: bool) -> Any:
        if query is None or ClaudeAgentOptions is None:
            raise RuntimeError("claude-agent-sdk가 설치되지 않았습니다.")

        env: dict[str, str] = {"ANTHROPIC_API_KEY": self.api_key}
        if self.base_url:
            env["ANTHROPIC_BASE_URL"] = self.base_url

        return ClaudeAgentOptions(
            model=self.model,
            system_prompt=system_prompt,
            cwd=self.cwd,
            allowed_tools=[],
            permission_mode="default",
            max_turns=1,
            include_partial_messages=include_partial_messages,
            env=env,
            thinking={"type": "adaptive"},
        )

    @staticmethod
    def _extract_text(message: Any) -> str:
        parts: list[str] = []
        for block in getattr(message, "content", []) or []:
            if isinstance(block, TextBlock):
                text = getattr(block, "text", "")
                if text:
                    parts.append(text)
        return "".join(parts)

    @staticmethod
    def _extract_tokens(usage: Any) -> tuple[int | None, int | None]:
        if not isinstance(usage, dict):
            return None, None

        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        return (
            input_tokens if isinstance(input_tokens, int) else None,
            output_tokens if isinstance(output_tokens, int) else None,
        )

    async def _run_streaming(
        self,
        *,
        user_message: str,
        memory_markdown: str,
        on_delta: Callable[[str], Awaitable[None] | None],
    ) -> MentoringAgentResult:
        started_at = perf_counter()
        prompt = self._build_user_prompt(user_message=user_message, memory_markdown=memory_markdown)

        options = self._build_options(system_prompt=SYSTEM_PROMPT, include_partial_messages=True)
        query_fn = query
        if query_fn is None:
            raise RuntimeError("claude-agent-sdk가 설치되지 않았습니다.")

        rendered_text = ""
        result_text: str | None = None
        usage: dict[str, Any] | None = None

        try:
            async for message in query_fn(prompt=prompt, options=options):
                if isinstance(message, AssistantMessage):
                    next_text = self._extract_text(message)
                    if not next_text:
                        continue

                    if next_text.startswith(rendered_text):
                        delta = next_text[len(rendered_text) :]
                    else:
                        delta = next_text

                    rendered_text = next_text
                    if delta:
                        callback_result = on_delta(delta)
                        if callback_result is not None:
                            await callback_result

                if isinstance(message, ResultMessage):
                    if isinstance(getattr(message, "usage", None), dict):
                        usage = message.usage
                    result_value = getattr(message, "result", None)
                    if isinstance(result_value, str) and result_value.strip():
                        result_text = result_value
        except Exception as exc:
            raise RuntimeError(f"Claude API 호출 실패: {exc}") from exc

        latency_ms = int((perf_counter() - started_at) * 1000)
        final_text = rendered_text.strip() or (result_text or "")
        tokens_input, tokens_output = self._extract_tokens(usage)

        return MentoringAgentResult(
            content_markdown=final_text,
            tool_calls=[],
            latency_ms=latency_ms,
            tokens_input=tokens_input,
            tokens_output=tokens_output,
        )

    async def generate_reply(
        self,
        *,
        user_message: str,
        memory_markdown: str,
    ) -> MentoringAgentResult:
        if not self.api_key:
            return MentoringAgentResult(
                content_markdown="CLAUDE_API_KEY가 설정되지 않아 에이전트 응답을 생성할 수 없습니다.",
                tool_calls=[],
                latency_ms=0,
                tokens_input=None,
                tokens_output=None,
            )

        return await self._run_streaming(
            user_message=user_message,
            memory_markdown=memory_markdown,
            on_delta=lambda _: None,
        )

    async def generate_reply_streaming(
        self,
        *,
        user_message: str,
        memory_markdown: str,
        on_delta: Callable[[str], Awaitable[None] | None],
    ) -> MentoringAgentResult:
        if not self.api_key:
            fallback = "CLAUDE_API_KEY가 설정되지 않아 에이전트 응답을 생성할 수 없습니다."
            callback_result = on_delta(fallback)
            if callback_result is not None:
                await callback_result
            return MentoringAgentResult(
                content_markdown=fallback,
                tool_calls=[],
                latency_ms=0,
                tokens_input=None,
                tokens_output=None,
            )

        return await self._run_streaming(
            user_message=user_message,
            memory_markdown=memory_markdown,
            on_delta=on_delta,
        )

    async def summarize_memory(
        self,
        *,
        previous_memory_markdown: str,
        user_message: str,
        assistant_message: str,
    ) -> str:
        if not self.api_key:
            base = previous_memory_markdown.strip()
            new_item = f"- 사용자 요청: {user_message[:120]}"
            return (base + "\n" + new_item).strip() if base else new_item

        user_prompt = (
            "[기존 메모리]\n"
            f"{previous_memory_markdown.strip() or '(없음)'}\n\n"
            "[최신 사용자 발화]\n"
            f"{user_message}\n\n"
            "[최신 어시스턴트 응답]\n"
            f"{assistant_message}\n"
        )

        options = self._build_options(system_prompt=MEMORY_SYSTEM_PROMPT, include_partial_messages=False)
        query_fn = query
        if query_fn is None:
            raise RuntimeError("claude-agent-sdk가 설치되지 않았습니다.")

        last_text = ""
        result_text = ""
        try:
            async for message in query_fn(prompt=user_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    extracted = self._extract_text(message)
                    if extracted:
                        last_text = extracted
                if isinstance(message, ResultMessage):
                    result_value = getattr(message, "result", None)
                    if isinstance(result_value, str) and result_value.strip():
                        result_text = result_value
        except Exception:
            base = previous_memory_markdown.strip()
            new_item = f"- 사용자 요청: {user_message[:120]}"
            return (base + "\n" + new_item).strip() if base else new_item

        merged = (last_text or result_text).strip()
        return merged or (previous_memory_markdown.strip() or "")
