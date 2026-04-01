from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def get_by_path(value: Any, path: str, default: Any = None) -> Any:
    if not path:
        return default
    current = value
    for part in path.split("."):
        if isinstance(current, dict):
            if part not in current:
                return default
            current = current[part]
            continue
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                return default
            if index >= len(current):
                return default
            current = current[index]
            continue
        return default
    return current


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def normalize_datetime_string(value: Any) -> str:
    if isinstance(value, (int, float)):
        if value > 10_000_000_000:
            dt = datetime.fromtimestamp(value / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(value, tz=timezone.utc)
        return dt.isoformat()

    text = str(value or "").strip()
    if not text:
        return ""
    if text.isdigit():
        number = int(text)
        if number > 10_000_000_000:
            dt = datetime.fromtimestamp(number / 1000, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(number, tz=timezone.utc)
        return dt.isoformat()
    if text.endswith("Z"):
        return text[:-1] + "+00:00"
    if " " in text and "T" not in text:
        return text.replace(" ", "T")
    return text


def parse_datetime(value: Any | None) -> datetime | None:
    if not value:
        return None
    normalized = normalize_datetime_string(value)
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def format_date_yyyy_mm_dd(value: str | None) -> str:
    dt = parse_datetime(value)
    if dt is None:
        return ""
    return dt.strftime("%Y/%m/%d")


def utc_now() -> datetime:
    return datetime.now(tz=timezone.utc)
