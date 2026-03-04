import argparse
import json
import sys
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: dict[str, Any]


class QaVerifier:
    def __init__(self, base_url: str, origin: str):
        self.base_url = base_url.rstrip("/")
        self.origin = origin
        self.results: list[CheckResult] = []

    def _record(self, name: str, ok: bool, detail: dict[str, Any]) -> None:
        self.results.append(CheckResult(name=name, ok=ok, detail=detail))

    @staticmethod
    def _parse_header_list(value: str | None) -> set[str]:
        if not value:
            return set()
        return {item.strip().lower() for item in value.split(",") if item.strip()}

    def run(self) -> list[CheckResult]:
        with httpx.Client(base_url=self.base_url, follow_redirects=False, timeout=15.0) as client:
            login = client.get("/auth/google/callback")
            self._record(
                "login callback redirect",
                login.status_code in (302, 307),
                {"status": login.status_code, "location": login.headers.get("location")},
            )

            csrf_response = client.get("/auth/csrf")
            csrf_token = (
                csrf_response.json().get("csrf_token")
                if csrf_response.status_code == 200
                else None
            )
            self._record(
                "csrf endpoint issues token",
                csrf_response.status_code == 200
                and isinstance(csrf_token, str)
                and len(csrf_token) > 10,
                {
                    "status": csrf_response.status_code,
                    "token_length": len(csrf_token or ""),
                },
            )

            logout_no_csrf = client.post("/auth/logout")
            self._record(
                "logout without csrf blocked",
                logout_no_csrf.status_code == 403,
                {"status": logout_no_csrf.status_code, "body": logout_no_csrf.text},
            )

            logout_bad_csrf = client.post(
                "/auth/logout",
                headers={"X-CSRF-Token": "wrong-token"},
            )
            self._record(
                "logout with mismatched csrf blocked",
                logout_bad_csrf.status_code == 403,
                {"status": logout_bad_csrf.status_code, "body": logout_bad_csrf.text},
            )

            logout_ok = client.post(
                "/auth/logout",
                headers={"X-CSRF-Token": csrf_token or ""},
            )
            self._record(
                "logout with valid csrf succeeds",
                logout_ok.status_code == 200,
                {"status": logout_ok.status_code, "body": logout_ok.text},
            )

            logout_reuse = client.post(
                "/auth/logout",
                headers={"X-CSRF-Token": csrf_token or ""},
            )
            self._record(
                "old csrf token rejected after logout",
                logout_reuse.status_code == 403,
                {"status": logout_reuse.status_code, "body": logout_reuse.text},
            )

            safe_method = client.get("/terms")
            self._record(
                "safe method unaffected",
                safe_method.status_code == 200,
                {"status": safe_method.status_code, "body": safe_method.text},
            )

            relogin = client.get("/auth/google/callback")
            self._record(
                "relogin redirect",
                relogin.status_code in (302, 307),
                {"status": relogin.status_code, "location": relogin.headers.get("location")},
            )

            me = client.get("/auth/me")
            me_json = me.json() if me.headers.get("content-type", "").startswith("application/json") else {}
            self._record(
                "auth me authenticated",
                me.status_code == 200 and me_json.get("authenticated") is True,
                {"status": me.status_code, "body": me.text},
            )

            csrf_after_relogin = client.get("/auth/csrf")
            csrf_token_2 = (
                csrf_after_relogin.json().get("csrf_token")
                if csrf_after_relogin.status_code == 200
                else None
            )
            self._record(
                "csrf token available after relogin",
                isinstance(csrf_token_2, str) and len(csrf_token_2) > 10,
                {
                    "status": csrf_after_relogin.status_code,
                    "token_length": len(csrf_token_2 or ""),
                },
            )

            relogin_again = client.get("/auth/google/callback")
            csrf_after_login_rotation = client.get("/auth/csrf")
            csrf_token_3 = (
                csrf_after_login_rotation.json().get("csrf_token")
                if csrf_after_login_rotation.status_code == 200
                else None
            )
            self._record(
                "csrf token rotates on login callback",
                relogin_again.status_code in (302, 307)
                and isinstance(csrf_token_2, str)
                and isinstance(csrf_token_3, str)
                and csrf_token_2 != csrf_token_3,
                {
                    "login_status": relogin_again.status_code,
                    "token_changed": csrf_token_2 != csrf_token_3,
                },
            )

            active_csrf = csrf_token_3 or ""

            comments_no_csrf = client.post(
                "/comments",
                json={"content": "qa verify", "daily_snippet_id": 1},
            )
            self._record(
                "comments write without csrf blocked",
                comments_no_csrf.status_code == 403,
                {"status": comments_no_csrf.status_code, "body": comments_no_csrf.text},
            )

            comments_with_csrf = client.post(
                "/comments",
                json={"content": "qa verify", "daily_snippet_id": 1},
                headers={"X-CSRF-Token": active_csrf},
            )
            self._record(
                "comments write with csrf passes gate",
                comments_with_csrf.status_code != 403,
                {"status": comments_with_csrf.status_code, "body": comments_with_csrf.text},
            )

            users_no_csrf = client.patch(
                "/users/me/league",
                json={"league_type": "undergrad"},
            )
            self._record(
                "users league patch without csrf blocked",
                users_no_csrf.status_code == 403,
                {"status": users_no_csrf.status_code, "body": users_no_csrf.text},
            )

            users_with_csrf = client.patch(
                "/users/me/league",
                json={"league_type": "undergrad"},
                headers={"X-CSRF-Token": active_csrf},
            )
            self._record(
                "users league patch with csrf passes gate",
                users_with_csrf.status_code != 403,
                {"status": users_with_csrf.status_code, "body": users_with_csrf.text},
            )

            daily_no_csrf = client.post("/daily-snippets", json={"content": "qa-runtime"})
            self._record(
                "daily save without csrf blocked",
                daily_no_csrf.status_code == 403,
                {"status": daily_no_csrf.status_code, "body": daily_no_csrf.text},
            )

            daily_with_csrf = client.post(
                "/daily-snippets",
                json={"content": "qa-runtime"},
                headers={"X-CSRF-Token": active_csrf},
            )
            self._record(
                "daily save with csrf succeeds",
                daily_with_csrf.status_code == 200,
                {"status": daily_with_csrf.status_code, "body": daily_with_csrf.text},
            )

            weekly_no_csrf = client.post("/weekly-snippets", json={"content": "qa-runtime"})
            self._record(
                "weekly save without csrf blocked",
                weekly_no_csrf.status_code == 403,
                {"status": weekly_no_csrf.status_code, "body": weekly_no_csrf.text},
            )

            weekly_with_csrf = client.post(
                "/weekly-snippets",
                json={"content": "qa-runtime"},
                headers={"X-CSRF-Token": active_csrf},
            )
            self._record(
                "weekly save with csrf succeeds",
                weekly_with_csrf.status_code == 200,
                {"status": weekly_with_csrf.status_code, "body": weekly_with_csrf.text},
            )

            teams_no_csrf = client.post("/teams", json={"name": "QA Verify Team"})
            self._record(
                "teams create without csrf blocked",
                teams_no_csrf.status_code == 403,
                {"status": teams_no_csrf.status_code, "body": teams_no_csrf.text},
            )

            teams_with_csrf = client.post(
                "/teams",
                json={"name": "QA Verify Team"},
                headers={"X-CSRF-Token": active_csrf},
            )
            self._record(
                "teams create with csrf passes gate",
                teams_with_csrf.status_code != 403,
                {"status": teams_with_csrf.status_code, "body": teams_with_csrf.text},
            )

            mcp_bearer = client.post(
                "/mcp",
                headers={
                    "Authorization": "Bearer invalid-token",
                    "Accept": "application/json, text/event-stream",
                    "Content-Type": "application/json",
                },
                content=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}',
            )
            self._record(
                "bearer mcp request bypasses csrf",
                mcp_bearer.status_code == 401,
                {"status": mcp_bearer.status_code, "body": mcp_bearer.text},
            )

            non_bearer = client.post(
                "/auth/logout",
                headers={"Authorization": "Basic abc"},
            )
            self._record(
                "non bearer auth does not bypass csrf",
                non_bearer.status_code == 403,
                {"status": non_bearer.status_code, "body": non_bearer.text},
            )

            cors = client.options(
                "/auth/logout",
                headers={
                    "Origin": self.origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type,x-csrf-token,authorization,idempotency-key,x-test-now",
                },
            )
            allow_methods = self._parse_header_list(
                cors.headers.get("access-control-allow-methods")
            )
            allow_headers = self._parse_header_list(
                cors.headers.get("access-control-allow-headers")
            )
            required_methods = {"get", "post", "put", "patch", "delete", "options"}
            required_headers = {
                "content-type",
                "authorization",
                "x-csrf-token",
                "idempotency-key",
                "x-test-now",
            }
            self._record(
                "cors allowlist active",
                cors.status_code in (200, 204)
                and required_methods.issubset(allow_methods)
                and required_headers.issubset(allow_headers),
                {
                    "status": cors.status_code,
                    "allow_methods": cors.headers.get("access-control-allow-methods"),
                    "allow_headers": cors.headers.get("access-control-allow-headers"),
                    "allow_origin": cors.headers.get("access-control-allow-origin"),
                },
            )

            server_error = client.get("/daily-snippets?from_date=not-a-date")
            body_text = server_error.text
            self._record(
                "500 response does not expose internal error string",
                server_error.status_code == 500
                and "ValueError" not in body_text
                and "not-a-date" not in body_text,
                {"status": server_error.status_code, "body": body_text},
            )

        return self.results


def main() -> int:
    parser = argparse.ArgumentParser(description="Runtime QA verifier for P0 security checks")
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8011",
        help="Base URL of running server (default: http://127.0.0.1:8011)",
    )
    parser.add_argument(
        "--origin",
        default="http://localhost:3000",
        help="Origin header used for CORS preflight checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print raw JSON results in addition to summary",
    )
    args = parser.parse_args()

    verifier = QaVerifier(base_url=args.base_url, origin=args.origin)
    results = verifier.run()

    failed = [result for result in results if not result.ok]

    for result in results:
        marker = "PASS" if result.ok else "FAIL"
        print(f"[{marker}] {result.name}")

    print(f"\nSummary: {len(results) - len(failed)}/{len(results)} checks passed")

    if args.json:
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
