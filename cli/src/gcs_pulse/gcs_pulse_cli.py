from __future__ import annotations

import shlex
import shutil
import sys
from dataclasses import dataclass
from typing import Any

import click

from gcs_pulse.core import achievements as core_achievements
from gcs_pulse.core import auth as core_auth
from gcs_pulse.core import comments as core_comments
from gcs_pulse.core import meeting_rooms as core_meeting_rooms
from gcs_pulse.core import project as core_project
from gcs_pulse.core import snippets as core_snippets
from gcs_pulse.core.users import (
    list_students as core_list_students,
    list_teams as core_list_teams,
    search_students as core_search_students,
)
from gcs_pulse.core.session import SessionState
from gcs_pulse.utils.gcs_pulse_backend import BackendClient, BackendError
from gcs_pulse.utils.output import emit, error_payload, success_payload
from gcs_pulse.utils.repl_skin import BANNER, HELP, PROMPT


@dataclass
class AppContext:
    json_output: bool = False
    server_url: str = "http://127.0.0.1:8000"
    api_token: str = ""
    project_dir: str | None = None
    timeout: float = 20.0
    repl: bool = False
    backend: BackendClient | None = None


def _load_project_if_possible(state: AppContext) -> None:
    if not state.project_dir:
        return

    status = core_project.project_status(state.project_dir)
    if not status.get("exists"):
        return

    loaded = SessionState.from_dict(status["session"])
    if not state.server_url:
        state.server_url = loaded.server_url
    if not state.api_token:
        state.api_token = loaded.api_token
    if not state.timeout:
        state.timeout = loaded.timeout


def _ensure_backend(state: AppContext) -> BackendClient:
    if state.backend is None:
        _load_project_if_possible(state)
        state.backend = BackendClient(
            server_url=state.server_url,
            api_token=state.api_token,
            timeout=state.timeout,
        )
    return state.backend


def _resolve_cli(binary_name: str) -> list[str]:
    force_installed = os_env_truthy("CLI_ANYTHING_FORCE_INSTALLED")
    installed = shutil.which(binary_name)
    if installed:
        return [installed]
    if force_installed:
        raise RuntimeError(f"Installed CLI not found: {binary_name}")
    return [sys.executable, "-m", "gcs_pulse"]


def os_env_truthy(name: str) -> bool:
    raw = (os_getenv(name) or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def os_getenv(name: str) -> str | None:
    import os

    return os.getenv(name)


def _emit_result(ctx: AppContext, command: str, data: Any) -> None:
    emit(success_payload(command, data, meta={"server_url": ctx.server_url}), json_output=ctx.json_output)


def _emit_error(ctx: AppContext, error: Exception, command: str) -> None:
    if isinstance(error, BackendError):
        backend_error = error
        payload = error_payload(backend_error.code, backend_error.message, backend_error.details)
    elif isinstance(error, click.ClickException):
        payload = error_payload("CLICK_ERROR", error.message)
    else:
        payload = error_payload("UNEXPECTED", str(error))
    payload["command"] = command
    emit(payload, json_output=ctx.json_output)


def _run(ctx: AppContext, command: str, fn) -> None:
    try:
        data = fn()
        _emit_result(ctx, command, data)
    except Exception as exc:  # noqa: BLE001
        _emit_error(ctx, exc, command)
        raise SystemExit(1) from exc


def _save_current_project(ctx: AppContext) -> dict[str, Any]:
    if not ctx.project_dir:
        raise click.ClickException("--project is required")
    session = SessionState(
        server_url=ctx.server_url,
        api_token=ctx.api_token,
        timeout=ctx.timeout,
        project=ctx.project_dir,
    )
    return core_project.save_project(ctx.project_dir, session)


def _run_repl(base_ctx: AppContext) -> None:
    click.echo(BANNER)
    click.echo(HELP)

    while True:
        try:
            line = input(PROMPT).strip()
        except EOFError:
            click.echo()
            return

        if not line:
            continue
        if line in {"exit", "quit"}:
            return
        if line == "help":
            click.echo(HELP)
            continue

        args = shlex.split(line)
        try:
            cli.main(
                args=args,
                prog_name="gcs-pulse-cli",
                standalone_mode=False,
                obj=base_ctx,
            )
        except SystemExit:
            continue
        except Exception as exc:  # noqa: BLE001
            _emit_error(base_ctx, exc, "repl")


@click.group(invoke_without_command=True)
@click.option("--json", "json_output", is_flag=True, help="Emit compact JSON payload")
@click.option("--server-url", default=None, help="Backend base URL")
@click.option("--api-token", default=None, help="Bearer token for API/MCP")
@click.option("--project", "project_dir", default=None, help="Project directory for session file")
@click.option("--timeout", default=None, type=float)
@click.pass_context
def cli(
    click_ctx: click.Context,
    json_output: bool,
    server_url: str | None,
    api_token: str | None,
    project_dir: str | None,
    timeout: float | None,
) -> None:
    base = click_ctx.obj if isinstance(click_ctx.obj, AppContext) else AppContext()
    base.json_output = json_output or base.json_output
    if server_url:
        base.server_url = server_url
    if api_token:
        base.api_token = api_token
    if project_dir:
        base.project_dir = project_dir
    if timeout is not None:
        base.timeout = timeout
    click_ctx.obj = base

    if click_ctx.invoked_subcommand is None:
        _run_repl(base)


@cli.group(name="project")
@click.pass_obj
def project_cmd(ctx: AppContext) -> None:
    del ctx


@project_cmd.command("new")
@click.pass_obj
def project_new(ctx: AppContext) -> None:
    _run(ctx, "project new", lambda: _save_current_project(ctx))


@project_cmd.command("status")
@click.pass_obj
def project_status(ctx: AppContext) -> None:
    if not ctx.project_dir:
        raise click.ClickException("--project is required")
    project_dir = ctx.project_dir
    _run(ctx, "project status", lambda: core_project.project_status(project_dir))


@project_cmd.command("save")
@click.pass_obj
def project_save(ctx: AppContext) -> None:
    _run(ctx, "project save", lambda: _save_current_project(ctx))


@cli.group(name="auth")
@click.pass_obj
def auth_cmd(ctx: AppContext) -> None:
    del ctx


@auth_cmd.command("status")
@click.pass_obj
def auth_status_cmd(ctx: AppContext) -> None:
    _run(ctx, "auth status", lambda: core_auth.auth_status(_ensure_backend(ctx)))


@auth_cmd.command("verify")
@click.pass_obj
def auth_verify_cmd(ctx: AppContext) -> None:
    _run(ctx, "auth verify", lambda: core_auth.auth_verify(_ensure_backend(ctx)))


@cli.group(name="comments")
@click.pass_obj
def comments_cmd(ctx: AppContext) -> None:
    del ctx


@comments_cmd.command("list")
@click.option("--daily-snippet-id", type=int, default=None)
@click.option("--weekly-snippet-id", type=int, default=None)
@click.pass_obj
def comments_list_cmd(ctx: AppContext, daily_snippet_id: int | None, weekly_snippet_id: int | None) -> None:
    _run(
        ctx,
        "comments list",
        lambda: core_comments.list_comments(
            _ensure_backend(ctx),
            daily_snippet_id=daily_snippet_id,
            weekly_snippet_id=weekly_snippet_id,
        ),
    )


@comments_cmd.command("create")
@click.argument("content")
@click.option("--comment-type", default="GENERAL")
@click.option("--daily-snippet-id", type=int, default=None)
@click.option("--weekly-snippet-id", type=int, default=None)
@click.pass_obj
def comments_create_cmd(
    ctx: AppContext,
    content: str,
    comment_type: str,
    daily_snippet_id: int | None,
    weekly_snippet_id: int | None,
) -> None:
    _run(
        ctx,
        "comments create",
        lambda: core_comments.create_comment(
            _ensure_backend(ctx),
            content=content,
            comment_type=comment_type,
            daily_snippet_id=daily_snippet_id,
            weekly_snippet_id=weekly_snippet_id,
        ),
    )


@comments_cmd.command("update")
@click.argument("comment_id", type=int)
@click.argument("content")
@click.pass_obj
def comments_update_cmd(ctx: AppContext, comment_id: int, content: str) -> None:
    _run(
        ctx,
        "comments update",
        lambda: core_comments.update_comment(_ensure_backend(ctx), comment_id, content=content),
    )


@comments_cmd.command("delete")
@click.argument("comment_id", type=int)
@click.pass_obj
def comments_delete_cmd(ctx: AppContext, comment_id: int) -> None:
    _run(ctx, "comments delete", lambda: core_comments.delete_comment(_ensure_backend(ctx), comment_id))


@cli.group(name="achievements")
@click.pass_obj
def achievements_cmd(ctx: AppContext) -> None:
    del ctx


@achievements_cmd.command("me")
@click.pass_obj
def achievements_me_cmd(ctx: AppContext) -> None:
    _run(ctx, "achievements me", lambda: core_achievements.my_achievements(_ensure_backend(ctx)))


@achievements_cmd.command("recent")
@click.option("--limit", type=int, default=10)
@click.pass_obj
def achievements_recent_cmd(ctx: AppContext, limit: int) -> None:
    _run(
        ctx,
        "achievements recent",
        lambda: core_achievements.recent_achievements(_ensure_backend(ctx), limit=limit),
    )


@cli.group(name="meeting-rooms")
@click.pass_obj
def meeting_rooms_cmd(ctx: AppContext) -> None:
    del ctx


@meeting_rooms_cmd.command("list")
@click.pass_obj
def meeting_rooms_list_cmd(ctx: AppContext) -> None:
    _run(ctx, "meeting-rooms list", lambda: core_meeting_rooms.list_rooms(_ensure_backend(ctx)))


@meeting_rooms_cmd.command("reservations")
@click.option("--room-id", type=int, required=True)
@click.option("--date", required=True)
@click.pass_obj
def meeting_rooms_reservations_cmd(ctx: AppContext, room_id: int, date: str) -> None:
    _run(
        ctx,
        "meeting-rooms reservations",
        lambda: core_meeting_rooms.list_reservations(_ensure_backend(ctx), room_id=room_id, date=date),
    )


@meeting_rooms_cmd.command("reserve")
@click.option("--room-id", type=int, required=True)
@click.option("--start-at", required=True)
@click.option("--end-at", required=True)
@click.option("--purpose", default=None)
@click.pass_obj
def meeting_rooms_reserve_cmd(
    ctx: AppContext,
    room_id: int,
    start_at: str,
    end_at: str,
    purpose: str | None,
) -> None:
    _run(
        ctx,
        "meeting-rooms reserve",
        lambda: core_meeting_rooms.create_reservation(
            _ensure_backend(ctx),
            room_id=room_id,
            start_at=start_at,
            end_at=end_at,
            purpose=purpose,
        ),
    )


@meeting_rooms_cmd.command("cancel")
@click.argument("reservation_id", type=int)
@click.pass_obj
def meeting_rooms_cancel_cmd(ctx: AppContext, reservation_id: int) -> None:
    _run(
        ctx,
        "meeting-rooms cancel",
        lambda: core_meeting_rooms.cancel_reservation(_ensure_backend(ctx), reservation_id=reservation_id),
    )


def _snippet_group(kind: str):
    @cli.group(name=kind)
    @click.pass_obj
    def _group(ctx: AppContext) -> None:
        del ctx

    @_group.command("list")
    @click.option("--limit", type=int, default=50)
    @click.option("--offset", type=int, default=0)
    @click.option("--order", default="desc")
    @click.option("--from-key", default=None)
    @click.option("--to-key", default=None)
    @click.option("--id", "snippet_id", type=int, default=None)
    @click.option("--q", default=None)
    @click.option("--scope", default="own")
    @click.pass_obj
    def _list(
        ctx: AppContext,
        limit: int,
        offset: int,
        order: str,
        from_key: str | None,
        to_key: str | None,
        snippet_id: int | None,
        q: str | None,
        scope: str,
    ) -> None:
        def _do() -> dict[str, Any]:
            query = {
                "limit": limit,
                "offset": offset,
                "order": order,
                "id": snippet_id,
                "q": q,
                "scope": scope,
            }
            if kind == "daily":
                query["from_date"] = from_key
                query["to_date"] = to_key
                return core_snippets.daily_list(_ensure_backend(ctx), **query)
            query["from_week"] = from_key
            query["to_week"] = to_key
            return core_snippets.weekly_list(_ensure_backend(ctx), **query)

        _run(ctx, f"{kind} list", _do)

    @_group.command("get")
    @click.argument("snippet_id", type=int)
    @click.pass_obj
    def _get(ctx: AppContext, snippet_id: int) -> None:
        fn = core_snippets.daily_get if kind == "daily" else core_snippets.weekly_get
        _run(ctx, f"{kind} get", lambda: fn(_ensure_backend(ctx), snippet_id))

    @_group.command("create")
    @click.argument("content")
    @click.pass_obj
    def _create(ctx: AppContext, content: str) -> None:
        fn = core_snippets.daily_create if kind == "daily" else core_snippets.weekly_create
        _run(ctx, f"{kind} create", lambda: fn(_ensure_backend(ctx), content))

    @_group.command("organize")
    @click.argument("content", required=False, default="")
    @click.pass_obj
    def _organize(ctx: AppContext, content: str) -> None:
        fn = core_snippets.daily_organize if kind == "daily" else core_snippets.weekly_organize
        _run(ctx, f"{kind} organize", lambda: fn(_ensure_backend(ctx), content))

    @_group.command("feedback")
    @click.pass_obj
    def _feedback(ctx: AppContext) -> None:
        fn = core_snippets.daily_feedback if kind == "daily" else core_snippets.weekly_feedback
        _run(ctx, f"{kind} feedback", lambda: fn(_ensure_backend(ctx)))

    @_group.command("update")
    @click.argument("snippet_id", type=int)
    @click.argument("content")
    @click.pass_obj
    def _update(ctx: AppContext, snippet_id: int, content: str) -> None:
        fn = core_snippets.daily_update if kind == "daily" else core_snippets.weekly_update
        _run(ctx, f"{kind} update", lambda: fn(_ensure_backend(ctx), snippet_id, content))

    @_group.command("delete")
    @click.argument("snippet_id", type=int)
    @click.pass_obj
    def _delete(ctx: AppContext, snippet_id: int) -> None:
        fn = core_snippets.daily_delete if kind == "daily" else core_snippets.weekly_delete
        _run(ctx, f"{kind} delete", lambda: fn(_ensure_backend(ctx), snippet_id))


_snippet_group("daily")
_snippet_group("weekly")


@cli.group(name="users")
@click.pass_obj
def users_cmd(ctx: AppContext) -> None:
    del ctx


@users_cmd.command("search")
@click.option("--q", required=True)
@click.option("--limit", type=int, default=20)
@click.pass_obj
def users_search_cmd(ctx: AppContext, q: str, limit: int) -> None:
    _run(
        ctx,
        "users search",
        lambda: core_search_students(_ensure_backend(ctx), q=q, limit=limit),
    )


@users_cmd.command("list")
@click.option("--limit", type=int, default=100)
@click.option("--offset", type=int, default=0)
@click.pass_obj
def users_list_cmd(ctx: AppContext, limit: int, offset: int) -> None:
    _run(
        ctx,
        "users list",
        lambda: core_list_students(_ensure_backend(ctx), limit=limit, offset=offset),
    )


@users_cmd.command("teams")
@click.option("--limit", type=int, default=100)
@click.option("--offset", type=int, default=0)
@click.pass_obj
def users_teams_cmd(ctx: AppContext, limit: int, offset: int) -> None:
    _run(
        ctx,
        "users teams",
        lambda: core_list_teams(_ensure_backend(ctx), limit=limit, offset=offset),
    )


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
