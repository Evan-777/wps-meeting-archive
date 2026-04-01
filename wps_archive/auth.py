from __future__ import annotations

import json
from urllib import parse, request

from .config import AuthConfig


def get_access_token(auth: AuthConfig) -> str:
    if auth.access_token:
        return auth.access_token
    if auth.client_id and auth.client_secret and not auth.authorization_code:
        body = parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": auth.client_id,
                "client_secret": auth.client_secret,
            }
        ).encode("utf-8")
    else:
        required = [auth.client_id, auth.client_secret, auth.authorization_code, auth.redirect_uri]
        if not all(required):
            raise ValueError(
                "缺少 access_token；请提供 auth.access_token，或提供 client_id/client_secret，"
                "若走授权码模式则还需 authorization_code/redirect_uri"
            )
        body = parse.urlencode(
            {
                "grant_type": "authorization_code",
                "client_id": auth.client_id,
                "client_secret": auth.client_secret,
                "code": auth.authorization_code,
                "redirect_uri": auth.redirect_uri,
            }
        ).encode("utf-8")
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
    return token
