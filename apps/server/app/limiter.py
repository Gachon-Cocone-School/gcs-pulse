from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def auth_me_rate_limit_key(request: Request) -> str:
    session_user = request.session.get("user") if hasattr(request, "session") else None

    if isinstance(session_user, dict):
        user_email = session_user.get("email")
        if isinstance(user_email, str) and user_email.strip():
            return f"user:{user_email.strip().lower()}"

    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=get_remote_address)
