from __future__ import annotations

import json
import secrets
import threading
import webbrowser
from dataclasses import dataclass
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib import parse, request

from .config import AppConfig, AuthConfig, save_config
from .utils import parse_datetime, utc_now


AUTH_URL = "https://openapi.wps.cn/oauth2/auth"
TOKEN_EXPIRY_SAFETY_SECONDS = 60
DEFAULT_REDIRECT_URI = "http://127.0.0.1:8765/callback"
DEFAULT_USER_SCOPE = (
    "kso.meeting.read,"
    "kso.meeting_minutes.read,"
    "kso.meeting_minutes_content.read,"
    "kso.meeting_recording.read,"
    "kso.meeting_recording_content.read,"
    "kso.group.read,"
    "kso.contact.read"
)


@dataclass
class AuthResult:
    code: str
    state: str


class CallbackHandler(BaseHTTPRequestHandler):
    result: AuthResult | None = None
    error: str | None = None
    done = threading.Event()

    def do_GET(self) -> None:  # noqa: N802
        parsed = parse.urlparse(self.path)
        params = parse.parse_qs(parsed.query)
        code = (params.get("code") or [""])[0]
        state = (params.get("state") or [""])[0]
        error = (params.get("error") or [""])[0]

        if error:
            CallbackHandler.error = error
            self._send_page("WPS authorization failed. You can close this page.")
            CallbackHandler.done.set()
            return

        if not code:
            CallbackHandler.error = "missing code"
            self._send_page("Missing authorization code. You can close this page.")
            CallbackHandler.done.set()
            return

        CallbackHandler.result = AuthResult(code=code, state=state)
        self._send_page("WPS authorization succeeded. You can close this page.")
        CallbackHandler.done.set()

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def _send_page(self, message: str) -> None:
        body = f"""<!doctype html>
<html>
  <head><meta charset="utf-8"><title>WPS OAuth</title></head>
  <body style="font-family: sans-serif; padding: 24px;">
    <h2>{message}</h2>
  </body>
</html>"""
        encoded = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def build_authorize_url(client_id: str, redirect_uri: str, scope: str, state: str) -> str:
    query = parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def exchange_authorization_code(
    auth: AuthConfig,
    code: str,
    redirect_uri: str,
) -> dict:
    return _request_token(
        auth,
        {
            "grant_type": "authorization_code",
            "client_id": auth.client_id,
            "client_secret": auth.client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        },
    )


def refresh_user_access_token(auth: AuthConfig) -> dict:
    if not auth.refresh_token:
        raise ValueError("missing refresh_token")
    return _request_token(
        auth,
        {
            "grant_type": "refresh_token",
            "client_id": auth.client_id,
            "client_secret": auth.client_secret,
            "refresh_token": auth.refresh_token,
        },
    )


def get_access_token(config: AppConfig) -> str:
    auth = config.auth

    if _has_valid_access_token(auth):
        return auth.access_token

    if auth.refresh_token:
        try:
            token_payload = refresh_user_access_token(auth)
        except Exception as exc:
            if auth.access_token and not auth.access_token_expires_at:
                return auth.access_token
            raise ValueError(
                "refresh_token 已失效或刷新失败，请重新运行授权命令获取新的 user token"
            ) from exc
        apply_token_payload(auth, token_payload)
        save_config(config)
        return auth.access_token

    if auth.access_token and not auth.access_token_expires_at:
        return auth.access_token

    if auth.client_id and auth.client_secret and not _wants_user_authorization(auth):
        token_payload = _request_token(
            auth,
            {
                "grant_type": "client_credentials",
                "client_id": auth.client_id,
                "client_secret": auth.client_secret,
            },
        )
        apply_token_payload(auth, token_payload)
        return auth.access_token

    required = [auth.client_id, auth.client_secret, auth.authorization_code, auth.redirect_uri]
    if not all(required):
        raise ValueError(
            "缺少可用 access_token，且无法自动刷新；请先运行授权命令重新获取 user token"
        )

    token_payload = exchange_authorization_code(
        auth=auth,
        code=auth.authorization_code,
        redirect_uri=auth.redirect_uri,
    )
    apply_token_payload(auth, token_payload)
    save_config(config)
    return auth.access_token


def authorize_user(
    auth: AuthConfig,
    *,
    open_browser: bool = True,
    host: str = "127.0.0.1",
    port: int = 8765,
    timeout_seconds: int = 300,
) -> dict:
    if not auth.client_id or not auth.client_secret:
        raise ValueError("授权前必须在 config.json 中提供 client_id/client_secret")

    if not auth.redirect_uri:
        auth.redirect_uri = f"http://{host}:{port}/callback"
    if not auth.scope:
        auth.scope = DEFAULT_USER_SCOPE

    state = secrets.token_urlsafe(16)
    CallbackHandler.result = None
    CallbackHandler.error = None
    CallbackHandler.done.clear()

    server = HTTPServer((host, port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    auth_url = build_authorize_url(
        client_id=auth.client_id,
        redirect_uri=auth.redirect_uri,
        scope=auth.scope,
        state=state,
    )
    print("Open this URL and finish authorization:")
    print(auth_url)
    if open_browser:
        webbrowser.open(auth_url)

    CallbackHandler.done.wait(timeout=timeout_seconds)
    server.server_close()

    if CallbackHandler.error:
        raise ValueError(f"WPS authorization failed: {CallbackHandler.error}")
    if CallbackHandler.result is None:
        raise ValueError("timeout waiting for authorization callback")
    if CallbackHandler.result.state != state:
        raise ValueError("state mismatch during authorization")

    return exchange_authorization_code(
        auth=auth,
        code=CallbackHandler.result.code,
        redirect_uri=auth.redirect_uri,
    )


def _has_valid_access_token(auth: AuthConfig) -> bool:
    if not auth.access_token:
        return False
    if not auth.access_token_expires_at:
        return False
    expires_at = parse_datetime(auth.access_token_expires_at)
    if expires_at is None:
        return False
    return utc_now() + timedelta(seconds=TOKEN_EXPIRY_SAFETY_SECONDS) < expires_at


def _request_token(auth: AuthConfig, form: dict[str, str]) -> dict:
    body = parse.urlencode(form).encode("utf-8")
    req = request.Request(
        auth.token_url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with request.urlopen(req) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    token = payload.get("access_token", "")
    if not token:
        raise ValueError(f"未能从 token 接口拿到 access_token: {payload}")
    return payload


def _wants_user_authorization(auth: AuthConfig) -> bool:
    return bool(auth.scope or auth.redirect_uri or auth.refresh_token or auth.authorization_code)


def apply_token_payload(auth: AuthConfig, payload: dict) -> None:
    auth.access_token = str(payload.get("access_token", "") or "")
    expires_in = int(payload.get("expires_in", 0) or 0)
    if expires_in > 0:
        auth.access_token_expires_at = (
            utc_now() + timedelta(seconds=max(0, expires_in - TOKEN_EXPIRY_SAFETY_SECONDS))
        ).isoformat()
    refresh_token = str(payload.get("refresh_token", "") or "")
    if refresh_token:
        auth.refresh_token = refresh_token
    refresh_expires_in = int(payload.get("refresh_expires_in", 0) or 0)
    if refresh_expires_in > 0:
        auth.refresh_expires_in = refresh_expires_in
