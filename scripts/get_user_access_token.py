#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer


AUTH_URL = "https://openapi.wps.cn/oauth2/auth"
TOKEN_URL = "https://openapi.wps.cn/oauth2/token"


@dataclass
class AuthResult:
    code: str
    state: str


class CallbackHandler(BaseHTTPRequestHandler):
    result: AuthResult | None = None
    error: str | None = None
    done = threading.Event()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
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


def exchange_code_for_token(
    client_id: str,
    client_secret: str,
    code: str,
    redirect_uri: str,
) -> dict:
    payload = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "code": code,
            "redirect_uri": redirect_uri,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        TOKEN_URL,
        data=payload,
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def build_authorize_url(client_id: str, redirect_uri: str, scope: str, state: str) -> str:
    query = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "scope": scope,
            "state": state,
        }
    )
    return f"{AUTH_URL}?{query}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Get WPS user access token via OAuth authorization_code flow")
    parser.add_argument("--client-id", required=True, help="WPS App ID")
    parser.add_argument("--client-secret", required=True, help="WPS App Key")
    parser.add_argument(
        "--scope",
        required=True,
        help="Comma-separated scopes, exactly matching the app permission names",
    )
    parser.add_argument(
        "--redirect-uri",
        default="http://127.0.0.1:8765/callback",
        help="Redirect URI configured in WPS open platform",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Local callback host")
    parser.add_argument("--port", type=int, default=8765, help="Local callback port")
    parser.add_argument("--state", default="", help="Optional custom state")
    parser.add_argument("--no-open", action="store_true", help="Print auth URL only, do not open browser")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    state = args.state or secrets.token_urlsafe(16)

    CallbackHandler.result = None
    CallbackHandler.error = None
    CallbackHandler.done.clear()

    server = HTTPServer((args.host, args.port), CallbackHandler)
    thread = threading.Thread(target=server.handle_request, daemon=True)
    thread.start()

    auth_url = build_authorize_url(
        client_id=args.client_id,
        redirect_uri=args.redirect_uri,
        scope=args.scope,
        state=state,
    )

    print("Open this URL and finish authorization:")
    print(auth_url)

    if not args.no_open:
        webbrowser.open(auth_url)

    CallbackHandler.done.wait(timeout=300)
    server.server_close()

    if CallbackHandler.error:
        print(json.dumps({"error": CallbackHandler.error}, ensure_ascii=False, indent=2))
        return 1

    if CallbackHandler.result is None:
        print(json.dumps({"error": "timeout waiting for callback"}, ensure_ascii=False, indent=2))
        return 1

    if CallbackHandler.result.state != state:
        print(
            json.dumps(
                {
                    "error": "state mismatch",
                    "expected_state": state,
                    "received_state": CallbackHandler.result.state,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1

    token_payload = exchange_code_for_token(
        client_id=args.client_id,
        client_secret=args.client_secret,
        code=CallbackHandler.result.code,
        redirect_uri=args.redirect_uri,
    )
    print(json.dumps(token_payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
