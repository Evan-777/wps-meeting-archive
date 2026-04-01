from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class SyncState:
    last_sync_at: str = ""


def load_state(path: Path) -> SyncState:
    if not path.exists():
        return SyncState()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SyncState(last_sync_at=payload.get("last_sync_at", ""))


def save_state(path: Path, state: SyncState) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"last_sync_at": state.last_sync_at}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
