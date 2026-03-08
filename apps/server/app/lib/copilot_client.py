from __future__ import annotations

from typing import Any, AsyncIterator, Dict, Optional
import asyncio
import json
import logging
from time import perf_counter

import httpx

from app.core.copilot_settings import settings
from app.lib.copilot_token_manager import token_manager

logger = logging.getLogger(__name__)


class CopilotClient:
    def __init__(self, timeout: Optional[int] = None) -> None:
        self._timeout = timeout or settings.COPILOT_REQUEST_TIMEOUT
        self._client: Optional[httpx.AsyncClient] = None
        # Optional lock to serialize token refresh to avoid thundering herd
        self._token_lock = asyncio.Lock()

    async def _ensure_client(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

    def _build_headers(self, copilot_token: str) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {copilot_token}",
            "Content-Type": "application/json",
            "Editor-Version": settings.EDITOR_VERSION,
            "Editor-Plugin-Version": settings.EDITOR_PLUGIN_VERSION,
            "Openai-Intent": "conversation-panel",
            "Openai-Organization": "github-copilot",
            "User-Agent": "GitHubCopilotChat/0.12.0",
            "Accept": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Optional[dict] = None,
        params: Optional[dict] = None,
        request_meta: Optional[dict] = None,
    ) -> Any:
        await self._ensure_client()

        # Acquire token (serialize refresh)
        async with self._token_lock:
            copilot_token = await token_manager.get_copilot_token()
            api_endpoint = token_manager.get_api_endpoint()

        url = path if path.startswith("http") else f"{api_endpoint.rstrip('/')}/{path.lstrip('/')}"
        headers = self._build_headers(copilot_token)

        # Simple retry for 429/5xx
        retries = 3
        backoff = 0.5
        last_exc = None
        meta = dict(request_meta or {})
        request_start = perf_counter()
        for attempt in range(retries):
            attempt_start = perf_counter()
            try:
                client = self._client
                if client is None:
                    raise RuntimeError("HTTP client is not initialized")
                resp = await client.request(method, url, json=json, params=params, headers=headers)
                resp.raise_for_status()
                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                total_elapsed_ms = round((perf_counter() - request_start) * 1000, 2)
                logger.info(
                    "copilot.request.success",
                    extra={
                        **meta,
                        "event": "copilot.request",
                        "status": "ok",
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "elapsed_ms": attempt_elapsed_ms,
                        "total_elapsed_ms": total_elapsed_ms,
                    },
                )
                return resp.json()
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                retryable = status in (401, 429, 502, 503, 504)
                logger.warning(
                    "copilot.request.http_error",
                    extra={
                        **meta,
                        "event": "copilot.request.attempt",
                        "status": "error",
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "http_status": status,
                        "retryable": retryable,
                        "backoff_ms": round(backoff * 1000, 2) if retryable and attempt < retries - 1 else 0,
                        "elapsed_ms": attempt_elapsed_ms,
                        "error_type": type(e).__name__,
                    },
                )
                if status == 401:
                    token_manager._copilot_token = None  # intentionally simple
                    if attempt == retries - 1:
                        raise
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                if status in (429, 502, 503, 504):
                    last_exc = e
                    if attempt == retries - 1:
                        break
                    await asyncio.sleep(backoff)
                    backoff *= 2
                    continue
                raise
            except httpx.RequestError as e:
                last_exc = e
                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                logger.warning(
                    "copilot.request.transport_error",
                    extra={
                        **meta,
                        "event": "copilot.request.attempt",
                        "status": "error",
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "retryable": True,
                        "backoff_ms": round(backoff * 1000, 2) if attempt < retries - 1 else 0,
                        "elapsed_ms": attempt_elapsed_ms,
                        "error_type": type(e).__name__,
                    },
                )
                if attempt == retries - 1:
                    break
                await asyncio.sleep(backoff)
                backoff *= 2
                continue

        total_elapsed_ms = round((perf_counter() - request_start) * 1000, 2)
        logger.error(
            "copilot.request.failed",
            extra={
                **meta,
                "event": "copilot.request",
                "status": "error",
                "max_retries": retries,
                "total_elapsed_ms": total_elapsed_ms,
                "error_type": type(last_exc).__name__ if last_exc else "RuntimeError",
            },
        )

        if last_exc:
            raise last_exc
        raise RuntimeError("Unknown error while calling Copilot API")

    async def chat_stream(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        request_meta: Optional[dict] = None,
        **kwargs,
    ) -> AsyncIterator[str]:
        await self._ensure_client()

        # Acquire token (serialize refresh)
        async with self._token_lock:
            copilot_token = await token_manager.get_copilot_token()
            api_endpoint = token_manager.get_api_endpoint()

        url = f"{api_endpoint.rstrip('/')}/chat/completions"
        headers = self._build_headers(copilot_token)
        headers["Accept"] = "text/event-stream"

        payload = {
            "messages": messages,
            "model": model or settings.COPILOT_DEFAULT_MODEL,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens
        payload.update(kwargs)

        retries = 3
        backoff = 0.5
        last_exc = None
        meta = dict(request_meta or {})
        request_start = perf_counter()

        for attempt in range(retries):
            attempt_start = perf_counter()
            emitted_any = False

            try:
                client = self._client
                if client is None:
                    raise RuntimeError("HTTP client is not initialized")

                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue

                        data = line[5:].strip()
                        if not data or data == "[DONE]":
                            continue

                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError:
                            continue

                        choices = chunk.get("choices")
                        if not isinstance(choices, list) or not choices:
                            continue

                        delta = choices[0].get("delta")
                        if not isinstance(delta, dict):
                            continue

                        content = delta.get("content")
                        if isinstance(content, str) and content:
                            emitted_any = True
                            yield content

                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                total_elapsed_ms = round((perf_counter() - request_start) * 1000, 2)
                logger.info(
                    "copilot.request.success",
                    extra={
                        **meta,
                        "event": "copilot.request",
                        "status": "ok",
                        "stream": True,
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "elapsed_ms": attempt_elapsed_ms,
                        "total_elapsed_ms": total_elapsed_ms,
                    },
                )
                return
            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                retryable = status in (401, 429, 502, 503, 504)
                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                logger.warning(
                    "copilot.request.http_error",
                    extra={
                        **meta,
                        "event": "copilot.request.attempt",
                        "status": "error",
                        "stream": True,
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "http_status": status,
                        "retryable": retryable,
                        "backoff_ms": round(backoff * 1000, 2) if retryable and attempt < retries - 1 else 0,
                        "elapsed_ms": attempt_elapsed_ms,
                        "error_type": type(e).__name__,
                    },
                )

                if status == 401:
                    token_manager._copilot_token = None  # intentionally simple

                if emitted_any or not retryable or attempt == retries - 1:
                    last_exc = e
                    break

                await asyncio.sleep(backoff)
                backoff *= 2
                continue
            except httpx.RequestError as e:
                attempt_elapsed_ms = round((perf_counter() - attempt_start) * 1000, 2)
                logger.warning(
                    "copilot.request.transport_error",
                    extra={
                        **meta,
                        "event": "copilot.request.attempt",
                        "status": "error",
                        "stream": True,
                        "retry_attempt": attempt + 1,
                        "max_retries": retries,
                        "retryable": True,
                        "backoff_ms": round(backoff * 1000, 2) if attempt < retries - 1 else 0,
                        "elapsed_ms": attempt_elapsed_ms,
                        "error_type": type(e).__name__,
                    },
                )

                if emitted_any or attempt == retries - 1:
                    last_exc = e
                    break

                await asyncio.sleep(backoff)
                backoff *= 2
                continue

        total_elapsed_ms = round((perf_counter() - request_start) * 1000, 2)
        logger.error(
            "copilot.request.failed",
            extra={
                **meta,
                "event": "copilot.request",
                "status": "error",
                "stream": True,
                "max_retries": retries,
                "total_elapsed_ms": total_elapsed_ms,
                "error_type": type(last_exc).__name__ if last_exc else "RuntimeError",
            },
        )

        if last_exc:
            raise last_exc
        raise RuntimeError("Unknown error while calling Copilot API")

    async def chat(
        self,
        messages: list[dict],
        *,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        request_meta: Optional[dict] = None,
        **kwargs,
    ) -> dict:
        payload = {
            "messages": messages,
            "model": model or settings.COPILOT_DEFAULT_MODEL,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        payload.update(kwargs)

        return await self.request(
            "POST",
            "/chat/completions",
            json=payload,
            request_meta=request_meta,
        )

    async def close(self) -> None:
        if self._client:
            await self._client.aclose()
            self._client = None


# We'll create the instance at startup and expose via app.state or a dependency
copilot_client: Optional[CopilotClient] = None
