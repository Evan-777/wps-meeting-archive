from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ParsedTitle:
    raw_title: str
    suggested_people_names: list[str]
    suggested_topic: str
    needs_confirmation: bool
    has_structured_title: bool
    note: str = ""


def parse_meeting_title(title: str, exclude_people: list[str] | None = None) -> ParsedTitle:
    exclude = set(exclude_people or [])
    raw_title = (title or "").strip()
    names: list[str] = []
    topic = raw_title
    note = ""
    has_structured_title = False

    if "_" in raw_title:
        left, _, right = raw_title.partition("_")
        if left.strip() and right.strip():
            has_structured_title = True
        candidate_names = [item.strip() for item in left.split("、") if item.strip()]
        seen: set[str] = set()
        for name in candidate_names:
            if name in exclude:
                continue
            if name in seen:
                continue
            seen.add(name)
            names.append(name)
        topic = right.strip() or raw_title
    else:
        note = "标题未包含下划线，无法稳定解析相关人员"

    needs_confirmation = not names or not topic
    if not topic:
        topic = raw_title
    return ParsedTitle(
        raw_title=raw_title,
        suggested_people_names=names,
        suggested_topic=topic,
        needs_confirmation=needs_confirmation,
        has_structured_title=has_structured_title,
        note=note,
    )
