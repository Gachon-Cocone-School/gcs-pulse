import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List
from app.dependencies_copilot import get_copilot_client
from app.lib.copilot_client import CopilotClient

router = APIRouter(prefix="/v1")
logger = logging.getLogger(__name__)


class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str | None = None
    messages: List[Message]
    max_tokens: int | None = None
    stream: bool | None = False

@router.post("/chat/completions")
async def chat_completions(req: ChatRequest, client: CopilotClient = Depends(get_copilot_client)):
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    try:
        resp = await client.chat(messages, model=req.model, max_tokens=req.max_tokens)
    except Exception:
        logger.exception("Chat completion request failed")
        raise HTTPException(status_code=502, detail="AI upstream request failed")
    return resp
