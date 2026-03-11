import asyncio
from dataclasses import dataclass
from typing import Optional

import pytest

from app.services import mentoring_agent_service as service_module
from app.services.mentoring_agent_service import MentoringAgentService


def _patch_sdk_symbols(monkeypatch):
    monkeypatch.setattr(service_module, "ClaudeAgentOptions", lambda **kwargs: kwargs)


@dataclass
class _StubTextBlock:
    text: str


@dataclass
class _StubAssistantMessage:
    content: list[_StubTextBlock]


@dataclass
class _StubResultMessage:
    usage: Optional[dict] = None
    result: Optional[str] = None


def test_generate_reply_without_api_key_returns_fallback():
    service = MentoringAgentService()
    service.api_key = ""

    result = asyncio.run(
        service.generate_reply(user_message="테스트", memory_markdown="")
    )

    assert "CLAUDE_API_KEY" in result.content_markdown
    assert result.tokens_input is None
    assert result.tokens_output is None
    assert result.latency_ms == 0


def test_generate_reply_non_stream_maps_result(monkeypatch):
    service = MentoringAgentService()
    service.api_key = "test-key"

    async def fake_query(*, prompt, options):
        _ = (prompt, options)
        yield _StubAssistantMessage(content=[_StubTextBlock(text="안")])
        yield _StubAssistantMessage(content=[_StubTextBlock(text="안녕")])
        yield _StubResultMessage(usage={"input_tokens": 12, "output_tokens": 34}, result="안녕")

    _patch_sdk_symbols(monkeypatch)
    monkeypatch.setattr(service_module, "TextBlock", _StubTextBlock)
    monkeypatch.setattr(service_module, "AssistantMessage", _StubAssistantMessage)
    monkeypatch.setattr(service_module, "ResultMessage", _StubResultMessage)
    monkeypatch.setattr(service_module, "query", fake_query)

    result = asyncio.run(
        service.generate_reply(user_message="질문", memory_markdown="메모")
    )

    assert result.content_markdown == "안녕"
    assert result.tokens_input == 12
    assert result.tokens_output == 34
    assert result.tool_calls == []


def test_generate_reply_streaming_emits_delta(monkeypatch):
    service = MentoringAgentService()
    service.api_key = "test-key"

    async def fake_query(*, prompt, options):
        _ = (prompt, options)
        yield _StubAssistantMessage(content=[_StubTextBlock(text="멘")])
        yield _StubAssistantMessage(content=[_StubTextBlock(text="멘토")])
        yield _StubAssistantMessage(content=[_StubTextBlock(text="멘토링")])
        yield _StubResultMessage(usage={"input_tokens": 1, "output_tokens": 2}, result="멘토링")

    _patch_sdk_symbols(monkeypatch)
    monkeypatch.setattr(service_module, "TextBlock", _StubTextBlock)
    monkeypatch.setattr(service_module, "AssistantMessage", _StubAssistantMessage)
    monkeypatch.setattr(service_module, "ResultMessage", _StubResultMessage)
    monkeypatch.setattr(service_module, "query", fake_query)

    deltas: list[str] = []

    async def on_delta(delta: str) -> None:
        deltas.append(delta)

    result = asyncio.run(
        service.generate_reply_streaming(
            user_message="질문",
            memory_markdown="메모",
            on_delta=on_delta,
        )
    )

    assert deltas == ["멘", "토", "링"]
    assert result.content_markdown == "멘토링"


def test_generate_reply_raises_runtime_error_on_query_failure(monkeypatch):
    service = MentoringAgentService()
    service.api_key = "test-key"

    def fake_query(*, prompt, options):
        _ = (prompt, options)

        async def _stream():
            if False:
                yield ""
            raise RuntimeError("boom")

        return _stream()

    _patch_sdk_symbols(monkeypatch)
    monkeypatch.setattr(service_module, "query", fake_query)

    with pytest.raises(RuntimeError) as exc_info:
        asyncio.run(service.generate_reply(user_message="질문", memory_markdown="메모"))

    assert "Claude API 호출 실패" in str(exc_info.value)


def test_summarize_memory_fallback_on_failure(monkeypatch):
    service = MentoringAgentService()
    service.api_key = "test-key"

    def fake_query(*, prompt, options):
        _ = (prompt, options)

        async def _stream():
            if False:
                yield ""
            raise RuntimeError("failed")

        return _stream()

    _patch_sdk_symbols(monkeypatch)
    monkeypatch.setattr(service_module, "query", fake_query)

    merged = asyncio.run(
        service.summarize_memory(
            previous_memory_markdown="- 기존",
            user_message="아주 긴 요청" * 30,
            assistant_message="응답",
        )
    )

    assert merged.startswith("- 기존\n- 사용자 요청: ")


def test_summarize_memory_success_uses_assistant_text(monkeypatch):
    service = MentoringAgentService()
    service.api_key = "test-key"

    async def fake_query(*, prompt, options):
        _ = (prompt, options)
        yield _StubAssistantMessage(content=[_StubTextBlock(text="- 핵심 요약")])
        yield _StubResultMessage(result="- 핵심 요약")

    _patch_sdk_symbols(monkeypatch)
    monkeypatch.setattr(service_module, "TextBlock", _StubTextBlock)
    monkeypatch.setattr(service_module, "AssistantMessage", _StubAssistantMessage)
    monkeypatch.setattr(service_module, "ResultMessage", _StubResultMessage)
    monkeypatch.setattr(service_module, "query", fake_query)

    merged = asyncio.run(
        service.summarize_memory(
            previous_memory_markdown="",
            user_message="요청",
            assistant_message="응답",
        )
    )

    assert merged == "- 핵심 요약"
