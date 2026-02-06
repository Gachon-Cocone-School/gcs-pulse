#!/usr/bin/env python3
"""Send a single test message '안녕?' to Copilot and print the response.

This script uses app.lib.copilot_client.CopilotClient and the TokenManager to
obtain or refresh Copilot tokens from env-provided credentials.

Be careful: this will contact GitHub APIs and Copilot endpoints. Do not paste
secrets publicly.
"""

import asyncio
import json
import sys
from app.core.copilot_settings import settings
from app.lib.copilot_client import CopilotClient

async def main():
    creds = settings.load_credentials()
    has_oauth = bool(creds.get("oauth_token"))
    has_copilot = bool(creds.get("copilot_token"))
    api_ep = creds.get("copilot_api_endpoint") or None

    print("Credentials available: oauth_token=", has_oauth, "copilot_token=", has_copilot)
    if api_ep:
        print("Using Copilot API endpoint:", api_ep)

    client = CopilotClient()
    try:
        messages = [{"role": "user", "content": "안녕?"}]
        resp = await client.chat(messages)
        # Pretty-print response, preserving unicode
        print("\n=== Copilot response ===")
        print(json.dumps(resp, ensure_ascii=False, indent=2))
    except Exception as e:
        print("Error calling Copilot:", e)
        sys.exit(2)
    finally:
        await client.close()

if __name__ == '__main__':
    asyncio.run(main())
