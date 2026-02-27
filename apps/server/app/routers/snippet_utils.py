from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import json
import logging

from fastapi import APIRouter, HTTPException
from starlette.requests import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.core.config import settings
from app.lib.copilot_client import CopilotClient
from app.models import ApiToken, User
from app.utils_time import current_business_date, to_business_timezone

logger = logging.getLogger(__name__)

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"
_TEST_COPILOT_TOKEN_MISSING = "No OAuth token available to request Copilot token"


def _is_test_copilot_token_missing_error(exc: Exception) -> bool:
    return settings.ENVIRONMENT == "test" and _TEST_COPILOT_TOKEN_MISSING in str(exc)


def _build_test_organized_content(content: str) -> str:
    stripped = content.strip() or "(내용 없음)"
    return (
        "### 테스트 환경 AI 정리 결과\n"
        "- 핵심 요약:\n"
        f"  - {stripped}\n"
        "- 다음 액션:\n"
        "  - 핵심 문장을 기준으로 후속 작업을 구체화하세요."
    )


def _build_test_feedback_json(snippet_label: str) -> str:
    return json.dumps(
        {
            "total_score": 75,
            "scores": {
                "record_completeness": {"score": 12, "max_score": 15},
                "learning_signal_detection": {"score": 14, "max_score": 20},
                "cause_effect_connection": {"score": 14, "max_score": 20},
                "action_translation": {"score": 18, "max_score": 25},
                "learning_attitude_consistency": {"score": 17, "max_score": 20},
            },
            "key_learning": f"{snippet_label} 내용을 기반으로 핵심 흐름을 정리했습니다.",
            "learning_sources": ["snippet"],
            "next_action": "핵심 요약을 바탕으로 다음 실행 항목을 1개 이상 작성하세요.",
            "mentor_comment": "테스트 환경 대체 응답입니다. 실제 운영에서는 AI 피드백이 제공됩니다.",
            "next_reflection_mission": "다음 기록에서 실행 결과를 1문장으로 회고하세요.",
            "anchoring_message": "작은 기록의 누적이 큰 성장을 만듭니다.",
            "playbook_update_markdown": "## Action Playbook\n- 다음 실행 항목을 완료 후 결과를 기록하세요.",
        },
        ensure_ascii=False,
    )

router = APIRouter(tags=["snippet-utils"])


@dataclass(frozen=True)
class BearerAuthContext:
    user: User
    api_token: ApiToken


def get_request_now(request: Request | None = None) -> datetime:
    if (
        request
        and settings.ENVIRONMENT == "test"
        and (override := request.headers.get("x-test-now"))
    ):
        try:
            parsed = datetime.fromisoformat(override)
            return to_business_timezone(parsed)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid x-test-now header") from exc
    return to_business_timezone(datetime.now().astimezone())


@router.get("/snippet_date")
async def get_snippet_date(request: Request):
    """
    Returns the current business date for snippets.
    9:00 AM is the cutoff.
    00:00 - 09:00 -> Yesterday
    09:00 - 24:00 -> Today
    """
    now = get_request_now(request)
    return {"date": current_business_date(now)}


def get_user_email(request: Request) -> str:
    email = request.session.get("user", {}).get("email")
    if not email:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return email


async def get_viewer_or_401(
    request: Request,
    db: AsyncSession,
    include_consents: bool = True,
):
    email = get_user_email(request)
    viewer = (
        await crud.get_user_by_email(db, email)
        if include_consents
        else await crud.get_user_by_email_basic(db, email)
    )
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")
    return viewer


def get_bearer_token(request: Request) -> str | None:
    authorization = request.headers.get("authorization")
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None

    token = token.strip()
    if not token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    return token


async def get_bearer_auth_or_401(request: Request, db: AsyncSession) -> BearerAuthContext:
    bearer_token = get_bearer_token(request)
    if bearer_token is None:
        raise HTTPException(status_code=401, detail="Invalid API token")

    api_token = await crud.get_api_token_by_raw_token(db, bearer_token)
    if not api_token:
        raise HTTPException(status_code=401, detail="Invalid API token")

    viewer = await crud.get_user_by_id(db, api_token.user_id)
    if not viewer:
        raise HTTPException(status_code=401, detail="User not found")

    await crud.touch_api_token_last_used_at(db, api_token)
    return BearerAuthContext(user=viewer, api_token=api_token)


async def get_snippet_viewer_or_401(request: Request, db: AsyncSession):
    bearer_token = get_bearer_token(request)
    if bearer_token is not None:
        auth_context = await get_bearer_auth_or_401(request, db)
        return auth_context.user

    return await get_viewer_or_401(request, db)


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


def is_snippet_editable(
    viewer,
    owner,
    target_date_or_week,
    kind: str,
    now: datetime | None = None,
    request: Request | None = None,
) -> bool:
    """
    Return True if the snippet should be editable by viewer.
    Rules:
    - Only owner can edit (viewer.id == owner.id)
    - For daily: editable only if target_date == current_business_date(now)
    - For weekly: editable only if target_week == current_business_week_start(now)

    Does NOT raise: returns bool so callers can decide on 403 vs 400.
    """
    if viewer.id != owner.id:
        return False
    now = now or get_request_now(request)
    # import locally to avoid circular imports
    from app.utils_time import current_business_date, current_business_week_start

    if kind == "daily":
        return target_date_or_week == current_business_date(now)
    elif kind == "weekly":
        return target_date_or_week == current_business_week_start(now)
    else:
        return False


async def organize_content_with_ai(
    content: str,
    copilot: CopilotClient,
    prompt_name: str = "organize_daily.md",
) -> str:
    prompt_path = PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=500, detail="System prompt not found")

    system_prompt = prompt_path.read_text(encoding="utf-8")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]

    try:
        resp = await copilot.chat(messages)
        if not resp or "choices" not in resp or not resp["choices"]:
            raise ValueError("Empty response from AI")
        return resp["choices"][0]["message"]["content"]
    except Exception as exc:
        if _is_test_copilot_token_missing_error(exc):
            logger.warning("Using test organize fallback due to missing Copilot token")
            return _build_test_organized_content(content)

        logger.exception("AI processing failed")
        raise HTTPException(status_code=502, detail="AI processing failed")


async def generate_feedback_with_ai(
    daily_snippet_content: str,
    organized_content: str,
    playbook_content: str | None,
    copilot: CopilotClient,
    prompt_name: str = "daily_feedback.md",
    snippet_label: str = "Daily Snippet",
) -> str:
    prompt_path = PROMPTS_DIR / prompt_name
    if not prompt_path.exists():
        raise HTTPException(status_code=500, detail="System prompt not found")

    system_prompt = prompt_path.read_text(encoding="utf-8")

    user_input = f"{snippet_label} (Raw):\n{daily_snippet_content}\n\n"
    user_input += f"{snippet_label} (Organized):\n{organized_content}\n\n"
    if playbook_content:
        user_input += f"My Playbook:\n{playbook_content}"
    else:
        user_input += "My Playbook:\n(No playbook yet)"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_input},
    ]

    try:
        resp = await copilot.chat(
            messages,
            response_format={"type": "json_object"},
            temperature=0,
        )
        if not resp or "choices" not in resp or not resp["choices"]:
            raise ValueError("Empty response from AI")
        return resp["choices"][0]["message"]["content"]
    except Exception as exc:
        if _is_test_copilot_token_missing_error(exc):
            logger.warning("Using test feedback fallback due to missing Copilot token")
            return _build_test_feedback_json(snippet_label)

        logger.exception("AI feedback generation failed")
        raise HTTPException(status_code=502, detail="AI processing failed")


def parse_feedback_json(feedback_json: str) -> dict:
    if not isinstance(feedback_json, str):
        raise ValueError("Feedback JSON must be a string")

    try:
        parsed = json.loads(feedback_json)
    except json.JSONDecodeError as exc:
        raise ValueError("Feedback JSON is invalid") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Feedback JSON must be an object")

    raw_total_score = parsed.get("total_score")
    if raw_total_score is None:
        raise ValueError("Feedback JSON missing total_score")

    try:
        float(raw_total_score)
    except (TypeError, ValueError) as exc:
        raise ValueError("Feedback JSON total_score must be numeric") from exc

    scores = parsed.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("Feedback JSON scores must be an object")

    playbook_update = parsed.get("playbook_update_markdown")
    if playbook_update is not None and not isinstance(playbook_update, str):
        raise ValueError("Feedback JSON playbook_update_markdown must be a string")

    parsed["playbook_update_markdown"] = playbook_update
    return parsed
