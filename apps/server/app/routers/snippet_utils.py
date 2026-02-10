from datetime import datetime
import os
import logging

from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.lib.copilot_client import CopilotClient
from app.utils_time import current_business_date

logger = logging.getLogger(__name__)

router = APIRouter(tags=["snippet-utils"])


@router.get("/snippet_date")
async def get_snippet_date():
    """
    Returns the current business date for snippets.
    9:00 AM is the cutoff.
    00:00 - 09:00 -> Yesterday
    09:00 - 24:00 -> Today
    """
    now = datetime.now().astimezone()
    return {"date": current_business_date(now)}


def get_user_sub(request: Request) -> str:
    sub = request.session.get("user", {}).get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return sub


async def get_viewer_or_401(request: Request, db: AsyncSession):
    sub = get_user_sub(request)
    viewer = await crud.get_user_by_sub(db, sub)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")
    return viewer


def can_read_snippet(viewer, owner) -> bool:
    # allow owner or same-team members to read snippets
    if viewer.id == owner.id:
        return True
    if viewer.team_id and owner.team_id and viewer.team_id == owner.team_id:
        return True
    return False


def require_snippet_owner_write(viewer, owner) -> None:
    if viewer.id != owner.id:
        raise HTTPException(status_code=403, detail="Owner only")


def require_daily_snippet_not_past(snippet_date, now: datetime) -> None:
    if snippet_date < current_business_date(now):
        raise HTTPException(status_code=403, detail="Past date is read-only")


async def organize_content_with_ai(content: str, copilot: CopilotClient) -> str:
    prompt_path = "prompts/organize_daily.md"
    if not os.path.exists(prompt_path):
        raise HTTPException(status_code=500, detail="System prompt not found")

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    try:
        resp = await copilot.chat(messages)
        if not resp or "choices" not in resp or not resp["choices"]:
            raise ValueError("Empty response from AI")
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI processing failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"AI processing failed: {str(e)}")


async def generate_feedback_with_ai(
    daily_snippet_content: str,
    organized_content: str,
    playbook_content: str | None,
    copilot: CopilotClient,
) -> str:
    prompt_path = "prompts/daily_feedback.md"
    if not os.path.exists(prompt_path):
        raise HTTPException(status_code=500, detail="System prompt not found")

    with open(prompt_path, "r", encoding="utf-8") as f:
        system_prompt = f.read()

    user_input = f"Daily Snippet (Raw):\n{daily_snippet_content}\n\n"
    user_input += f"Daily Snippet (Organized):\n{organized_content}\n\n"
    if playbook_content:
        user_input += f"My Playbook:\n{playbook_content}"
    else:
        user_input += "My Playbook:\n(No playbook yet)"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        resp = await copilot.chat(messages, response_format={"type": "json_object"})
        if not resp or "choices" not in resp or not resp["choices"]:
            raise ValueError("Empty response from AI")
        return resp["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI feedback generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"AI processing failed: {str(e)}")
