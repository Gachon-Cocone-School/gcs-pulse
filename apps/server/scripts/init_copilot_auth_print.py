#!/usr/bin/env python3
"""CLI script to run GitHub device flow and print Copilot credentials as JSON.

This mirrors proxy/scripts/init_auth.py but prints the resulting credentials JSON to
stdout instead of saving it to a file.
"""

import asyncio
import json
import sys
from pathlib import Path

# Ensure proxy/src is importable (proxy package lives under ./proxy/src)
ROOT = Path(__file__).parent.parent
PROXY_SRC = ROOT / "proxy" / "src"
if str(PROXY_SRC) not in sys.path:
    sys.path.insert(0, str(PROXY_SRC))

from copilot_proxy.auth.device_flow import DeviceFlowAuth
from copilot_proxy.auth.token_manager import TokenManager


async def main() -> None:
    print("=" * 60)
    print("Copilot Auth - obtain GitHub OAuth and Copilot tokens")
    print("=" * 60)

    device_flow = DeviceFlowAuth()
    token_manager = TokenManager()

    try:
        oauth_token = await device_flow.authenticate()
    except TimeoutError as e:
        print(f"\n❌ 시간 초과: {e}")
        raise SystemExit(1)
    except PermissionError as e:
        print(f"\n❌ 권한 거부: {e}")
        raise SystemExit(1)
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        raise SystemExit(1)

    # Request Copilot token using the proxy token manager logic
    try:
        copilot_token, expires_at, api_endpoint = await token_manager._request_copilot_token(oauth_token)
    except Exception as e:
        print(f"\n⚠️  Copilot 토큰 발급 실패: {e}")
        print("Copilot 구독이 활성화되어 있는지, 또는 네트워크/엔드포인트가 접근 가능한지 확인하세요.")
        raise SystemExit(1)

    credentials = {
        "oauth_token": oauth_token,
        "copilot_token": copilot_token,
        "copilot_expires_at": expires_at,
        "copilot_api_endpoint": api_endpoint,
    }

    # Print JSON to stdout
    print("\n# Copy the JSON below and store it securely as an environment secret or a file if needed")
    print(json.dumps(credentials, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
