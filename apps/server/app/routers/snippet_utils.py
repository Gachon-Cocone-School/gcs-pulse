from datetime import timedelta

from fastapi import APIRouter
from starlette.requests import Request

from app.routers import snippet_access, snippet_ai
from app.utils_time import current_business_date

router = APIRouter(tags=["snippet-utils"])


BearerAuthContext = snippet_access.BearerAuthContext
get_request_now = snippet_access.get_request_now


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

get_user_email = snippet_access.get_user_email
get_viewer_or_401 = snippet_access.get_viewer_or_401
get_bearer_token = snippet_access.get_bearer_token
get_bearer_auth_or_401 = snippet_access.get_bearer_auth_or_401
get_snippet_viewer_or_401 = snippet_access.get_snippet_viewer_or_401
can_read_snippet = snippet_access.can_read_snippet
require_snippet_owner_write = snippet_access.require_snippet_owner_write
is_snippet_editable = snippet_access.is_snippet_editable
is_snippet_editable_safe = snippet_access.is_snippet_editable_safe
def set_snippet_editable(
    snippet,
    viewer,
    owner,
    kind: str,
    key_attr: str,
    request: Request,
) -> bool:
    return snippet_access.set_snippet_editable(
        snippet,
        viewer,
        owner,
        kind,
        key_attr,
        request,
        is_snippet_editable_fn=is_snippet_editable,
    )

apply_editable_to_snippet_list = snippet_access.apply_editable_to_snippet_list


async def build_snippet_page_data(
    db,
    viewer,
    request: Request,
    snippet_id: int | None,
    server_key,
    kind: str,
    key_attr: str,
    key_step: timedelta,
    get_snippet_by_id,
    list_snippets_for_range,
    can_read_snippet_fn=None,
    is_snippet_editable_fn=None,
    requested_key=None,
) -> dict:
    editability_fn = is_snippet_editable_fn or is_snippet_editable
    return await snippet_access.build_snippet_page_data(
        db=db,
        viewer=viewer,
        request=request,
        snippet_id=snippet_id,
        server_key=server_key,
        requested_key=requested_key,
        kind=kind,
        key_attr=key_attr,
        key_step=key_step,
        get_snippet_by_id=get_snippet_by_id,
        list_snippets_for_range=list_snippets_for_range,
        can_read_snippet_fn=can_read_snippet_fn,
        is_snippet_editable_fn=editability_fn,
    )


organize_content_with_ai = snippet_ai.organize_content_with_ai
organize_content_with_ai_stream = snippet_ai.organize_content_with_ai_stream
generate_feedback_with_ai = snippet_ai.generate_feedback_with_ai
generate_feedback_with_ai_stream = snippet_ai.generate_feedback_with_ai_stream
parse_feedback_json = snippet_ai.parse_feedback_json
