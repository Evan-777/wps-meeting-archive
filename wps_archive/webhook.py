from __future__ import annotations

import json
from dataclasses import dataclass
from urllib import request


@dataclass
class WebhookClient:
    api_token: str

    def call(self, webhook_url: str, argv: dict[str, object] | None = None) -> dict:
        body = json.dumps({"Context": {"argv": argv or {}}}, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            webhook_url,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "AirScript-Token": self.api_token,
            },
        )
        with request.urlopen(req) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        if payload.get("error"):
            raise RuntimeError(f"AirScript webhook failed: {payload.get('error')}")
        return payload
