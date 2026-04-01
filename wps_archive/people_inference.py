from __future__ import annotations

from typing import Any

GENERIC_ONLY_KEYWORDS = {"健康影响", "科学问题", "机制", "模型"}


def infer_people_names(title: str = "", topic: str = "", mapping: list[dict[str, Any]] | None = None) -> list[str]:
    rules = mapping or []
    haystack = f"{title} {topic}".strip()
    if not haystack:
        return []

    ranked: list[tuple[int, int, int, int, int, str]] = []
    for index, rule in enumerate(rules):
        name = str(rule.get("name", "")).strip()
        include_keywords = [
            str(keyword).strip()
            for keyword in (rule.get("include_keywords") or rule.get("keywords") or [])
            if str(keyword).strip()
        ]
        exclude_keywords = [
            str(keyword).strip()
            for keyword in (rule.get("exclude_keywords") or [])
            if str(keyword).strip()
        ]
        priority = int(rule.get("priority", 0) or 0)
        if not name or not include_keywords:
            continue

        if any(keyword in haystack for keyword in exclude_keywords):
            continue

        matched = [keyword for keyword in include_keywords if keyword in haystack]
        if not matched:
            continue
        if all(keyword in GENERIC_ONLY_KEYWORDS for keyword in matched):
            continue

        total_length = sum(len(keyword) for keyword in matched)
        match_count = len(matched)
        longest = max(len(keyword) for keyword in matched)
        ranked.append((priority, total_length, match_count, longest, -index, name))

    if not ranked:
        return []

    ranked.sort(reverse=True)
    best_key = ranked[0][:4]
    names: list[str] = []
    seen: set[str] = set()
    for priority, total_length, match_count, longest, _, name in ranked:
        if (priority, total_length, match_count, longest) != best_key:
            break
        if name in seen:
            continue
        seen.add(name)
        names.append(name)
    return names
