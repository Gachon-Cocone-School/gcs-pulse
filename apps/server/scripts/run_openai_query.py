#!/usr/bin/env python3
"""Smoke test the application's OpenAI generation adapter."""

import asyncio
import json

from app.lib.copilot_client import CopilotClient


async def main() -> None:
    client = CopilotClient()
    try:
        response = await client.chat([{"role": "user", "content": "안녕?"}])
        print(json.dumps(response, ensure_ascii=False, indent=2))
    finally:
        await client.close()


if __name__ == "__main__":
    asyncio.run(main())
