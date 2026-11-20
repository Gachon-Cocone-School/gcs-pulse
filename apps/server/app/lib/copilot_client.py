"""OpenAI adapter for the application's existing chat contract."""

import logging
from collections.abc import AsyncIterator
from time import perf_counter
from typing import Any, Optional

from openai import AsyncOpenAI

from app.core.config import settings


logger = logging.getLogger(__name__)


class CopilotClient:
    def __init__(self) -> None:
        self._client = (
            AsyncOpenAI(
                api_key=settings.OPENAI_API_KEY,
                base_url="https://api.openai.com/v1",
                timeout=settings.OPENAI_REQUEST_TIMEOUT,
            )
            if settings.OPENAI_API_KEY
            else None
        )

    @property
    def sdk(self) -> AsyncOpenAI:
        if self._client is None:
            raise RuntimeError("OPENAI_API_KEY is missing")
        return self._client

    @staticmethod
    def _model(model: str | None) -> str:
        if model in (None, "", "gpt-5.6-luna"):
            return settings.OPENAI_GENERATION_MODEL
        return model

    @staticmethod
    def _responses_payload(
        messages: list[dict],
        *,
        model: str,
        stream: bool,
        max_tokens: Optional[int],
        **kwargs: Any,
    ) -> dict:
        """Translate the app's Chat Completions-style messages to Responses input."""
        instructions: list[str] = []
        input_items: list[dict] = []
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            if role == "system":
                instructions.append(str(content))
                continue
            input_items.append({"role": role, "content": content})

        payload: dict[str, Any] = {
            "model": model,
            "input": input_items,
            "stream": stream,
        }
        if instructions:
            payload["instructions"] = "\n\n".join(instructions)
        if max_tokens:
            payload["max_output_tokens"] = max_tokens
        # Reasoning models may reject the legacy temperature parameter.
        kwargs.pop("temperature", None)
        payload.update(kwargs)
        return payload

    @staticmethod
    def _response_text(response: dict) -> str:
        text = response.get("output_text")
        if isinstance(text, str) and text:
            return text

        parts: list[str] = []
        for item in response.get("output") or []:
            if not isinstance(item, dict):
                continue
            for content in item.get("content") or []:
                if isinstance(content, dict) and content.get("type") == "output_text":
                    value = content.get("text")
                    if isinstance(value, str):
                        parts.append(value)
        return "".join(parts)

    @classmethod
    def _as_chat_completion(cls, response: dict) -> dict:
        """Keep existing callers and the public chat route compatible."""
        return {
            "id": response.get("id"),
            "model": response.get("model"),
            "object": "chat.completion",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": cls._response_text(response)}}],
            "usage": response.get("usage"),
        }

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        request_meta: dict | None = None,
        **kwargs: Any,
    ) -> dict:
        payload = self._responses_payload(
            messages, model=self._model(model), stream=False, max_tokens=max_tokens, **kwargs
        )
        started = perf_counter()
        response = await self.sdk.responses.create(**payload, store=False)
        if response.status != "completed" or not response.output_text:
            raise RuntimeError(f"OpenAI response produced no complete text ({response.status})")
        self._log_completion(request_meta, response.model, started, stream=False)
        return self._as_chat_completion(response.model_dump())

    async def chat_stream(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        request_meta: dict | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = self._responses_payload(
            messages, model=self._model(model), stream=True, max_tokens=max_tokens, **kwargs
        )
        started = perf_counter()
        async with await self.sdk.responses.create(**payload, store=False) as stream:
            async for event in stream:
                if event.type == "response.output_text.delta":
                    yield event.delta
                elif event.type == "response.completed":
                    if not event.response.output_text:
                        raise RuntimeError("OpenAI stream completed without text")
                    self._log_completion(request_meta, event.response.model, started, stream=True)
                    return
                elif event.type in {"response.failed", "response.incomplete", "error"}:
                    raise RuntimeError(f"OpenAI stream ended with {event.type}")
        raise RuntimeError("OpenAI stream closed before completion")

    @staticmethod
    def _log_completion(
        request_meta: dict | None, model: str, started: float, *, stream: bool
    ) -> None:
        logger.info(
            "openai.request.success",
            extra={
                **(request_meta or {}),
                "model": model,
                "stream": stream,
                "elapsed_ms": round((perf_counter() - started) * 1000, 2),
            },
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
