from fastapi import Request
from typing import Optional
from app.lib.copilot_client import CopilotClient

async def get_copilot_client(request: Request) -> CopilotClient:
    client: Optional[CopilotClient] = getattr(request.app.state, "copilot_client", None)
    if client is None:
        raise RuntimeError("Copilot client not initialized. Ensure app startup creates it.")
    return client
