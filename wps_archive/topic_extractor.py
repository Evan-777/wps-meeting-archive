from __future__ import annotations

import re


SUMMARY_HEADING_RE = re.compile(r"^\s*#+\s*(.+?)\s*$")
CHINESE_TEXT_RE = re.compile(r"[\u4e00-\u9fffA-Za-z0-9]+")
TOPIC_HINT_WORDS = ["问题", "分析", "设计", "方案", "机制", "反演", "优化", "修改", "汇报", "测试", "参数"]
GENERIC_TRANSCRIPT_FRAGMENTS = ["我们", "今天", "继续", "然后", "就是", "这个", "那个", "一下", "一个"]
TRANSCRIPT_SPLIT_RE = re.compile(r"[，。！？；\n]+")
TRANSCRIPT_PREFIX_RE = re.compile(r"^(我们今天继续|我们今天|今天继续|继续|然后|就是|今天|我们|先|再|主要是|主要|一下|讨论|分析)+")
CONTENT_SPLIT_RE = re.compile(r"[。！？；\n]+")
SEGMENT_SPLIT_RE = re.compile(r"[、，,；;]|以及|并且|并|和|与|及")
HIGH_CONFIDENCE_SHORT_TOPICS = {"NO2阈值", "源汇分析"}
GENERIC_BARE_TOPICS = {"健康影响", "科学问题", "机制", "模型"}
SOURCE_QUALIFIERS = [
    "航空排放",
    "电厂排放",
    "火电",
    "电力排放",
    "燃煤电厂",
    "健康暴露",
    "贫困人口",
    "美国排放数据",
    "造纸厂",
    "沙尘",
    "水稻甲烷",
    "能源甲烷",
    "交通源",
    "VOCs",
    "VOC",
    "臭氧",
    "NO2",
    "空调",
]
PATTERN_TERMS = [
    (re.compile(r"AI辅助55版本", re.IGNORECASE), "AI辅助55版本"),
    (re.compile(r"55版本"), "55版本"),
    (re.compile(r"化学机制开发"), "化学机制开发"),
    (re.compile(r"NO2(?:浓度)?阈值|NO\s*2(?:浓度)?阈值", re.IGNORECASE), "NO2阈值"),
    (re.compile(r"季节机制转换点"), "季节机制转换点"),
    (re.compile(r"臭氧季节变化"), "臭氧季节变化"),
    (re.compile(r"源汇(?:角度)?(?:分析)?"), "源汇分析"),
    (re.compile(r"航空排放(?:健康影响)?"), "航空排放健康影响"),
    (re.compile(r"电厂排放健康(?:影响)?"), "电厂排放健康影响"),
    (re.compile(r"电力排放健康(?:影响)?"), "电力排放健康影响"),
    (re.compile(r"燃煤电厂(?:排放)?健康(?:影响)?"), "燃煤电厂健康影响"),
    (re.compile(r"火电(?:排放)?健康(?:影响)?"), "火电健康影响"),
    (re.compile(r"优化函数参数设置"), "优化函数参数设置"),
    (re.compile(r"结果量级"), "结果量级"),
    (re.compile(r"观测误差"), "观测误差"),
    (re.compile(r"造纸厂数据(?:的)?(?:分类|整理)"), "造纸厂数据分类"),
    (re.compile(r"产能(?:信息|数据|匹配)"), "产能匹配"),
    (re.compile(r"缺失数据"), "产能匹配"),
    (re.compile(r"机器学习模型"), "机器学习模型"),
    (re.compile(r"贫困人口分布数据"), "贫困人口分布数据"),
    (re.compile(r"健康暴露(?:不平等性)?"), "健康暴露不平等性"),
    (re.compile(r"不平等性"), "不平等性"),
    (re.compile(r"美国排放数据"), "美国排放数据"),
    (re.compile(r"排放数据对比分析"), "排放数据对比分析"),
    (re.compile(r"伴随模型"), "伴随模型"),
]

DOMAIN_HINTS = [
    "优化函数参数设置",
    "AI辅助55版本",
    "55版本",
    "化学机制开发",
    "结果量级",
    "观测误差",
    "航空排放",
    "航空排放健康影响",
    "电厂排放",
    "电厂排放健康影响",
    "电力排放",
    "燃煤电厂",
    "火电",
    "臭氧污染",
    "臭氧季节变化",
    "NO2阈值",
    "季节机制转换点",
    "臭氧",
    "NO2",
    "AOD",
    "OX",
    "SOA",
    "排放",
    "健康",
    "模型",
    "数据",
    "预测",
    "量级",
    "参数",
    "优化函数",
    "伴随模型",
    "空气质量",
    "阈值",
    "源汇",
    "机制",
    "光化学",
    "基尼系数",
    "航线",
    "机场",
    "国家尺度",
    "多尺度",
    "空调",
    "造纸厂",
    "美国",
    "南北",
    "气溶胶",
    "forcing",
    "轨迹",
    "论文",
    "引言",
]

GENERIC_PREFIXES = [
    "文章进展",
    "论文引言",
    "未来工作",
    "其他事务",
    "会议总结",
    "研究计划",
    "结果讨论",
    "初步结果分享",
]
GENERIC_SUFFIXES = [
    "讨论会议",
    "会议总结",
    "结果分享",
    "问题讨论",
    "讨论",
    "会议",
]

GENERIC_TOPICS = {
    "",
    "会议",
    "会议记录",
    "会议纪要",
    "会议讨论",
    "讨论",
    "总结",
    "章节",
    "健康影响",
    "科学问题",
    "机制",
    "模型",
}

GENERIC_SEGMENTS = {
    "文章撰写",
    "论文修改",
    "论文修改结构",
    "初步结果",
    "结果分享",
    "文章进展",
    "研究进展",
    "研究计划",
    "问题讨论",
    "会议记录",
    "会议纪要",
    "识别出部分缺失数据",
}


def extract_topic_from_recording_content(
    summary_text: str = "",
    chapters: list[dict] | None = None,
    transcript_text: str = "",
) -> str:
    chapters = chapters or []

    summary_candidates = _extract_summary_candidates(summary_text)
    best_chapter = ""
    for chapter in chapters:
        chapter_topic = _extract_topic_from_chapter(
            str(chapter.get("title", "")),
            str(chapter.get("content", "")),
        )
        if not chapter_topic:
            continue
        if not best_chapter:
            best_chapter = chapter_topic
        if not _is_generic_candidate(chapter_topic):
            best_chapter = chapter_topic
            break

    best_summary = _pick_best_candidate(summary_candidates)
    if best_summary and not _is_generic_candidate(best_summary) and (
        _score_candidate(best_summary) > _score_candidate(best_chapter) or not best_chapter
    ):
        return best_summary

    if best_chapter:
        return best_chapter

    transcript_candidates: list[tuple[int, str]] = []
    for raw_clause in TRANSCRIPT_SPLIT_RE.split(transcript_text):
        topic = normalize_topic_text(TRANSCRIPT_PREFIX_RE.sub("", raw_clause))
        if not is_meaningful_topic(topic):
            continue
        if not any(hint in topic for hint in TOPIC_HINT_WORDS):
            continue
        transcript_candidates.append((_score_transcript_topic(topic), topic))
    if transcript_candidates:
        transcript_candidates.sort(key=lambda item: (-item[0], len(item[1])))
        return transcript_candidates[0][1]

    return ""


def normalize_topic_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("关于", "")
    value = value.replace("的", "")
    tokens = CHINESE_TEXT_RE.findall(value)
    value = "".join(tokens).strip()
    value = _strip_generic_edges(value)
    return value[:40]


def is_meaningful_topic(text: str) -> bool:
    value = normalize_topic_text(text)
    if not value:
        return False
    if value in GENERIC_TOPICS:
        return False
    if value.endswith("的会议"):
        return False
    if len(value) < 4 and value not in HIGH_CONFIDENCE_SHORT_TOPICS:
        return False
    return True


def _score_transcript_topic(topic: str) -> int:
    score = _score_candidate(topic)
    for fragment in GENERIC_TRANSCRIPT_FRAGMENTS:
        if fragment in topic:
            score -= 4
    if topic.endswith("讨论") and score <= 3:
        score -= 2
    if 4 <= len(topic) <= 12:
        score += 2
    return score


def _extract_summary_candidates(summary_text: str) -> list[str]:
    candidates: list[str] = []
    lines = summary_text.splitlines()
    for line in lines:
        match = SUMMARY_HEADING_RE.match(line)
        if not match:
            continue
        topic = _refine_candidate(match.group(1))
        if is_meaningful_topic(topic):
            candidates.append(topic)
    return candidates


def _extract_content_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    for raw_line in CONTENT_SPLIT_RE.split(text):
        clause = _refine_candidate(raw_line)
        if not is_meaningful_topic(clause):
            continue
        if any(hint in clause for hint in DOMAIN_HINTS):
            candidates.append(clause)
    return candidates


def _extract_topic_from_chapter(title: str, content: str) -> str:
    title_topic = normalize_topic_text(title)
    content_candidates = _extract_content_candidates(content)
    content_topic = _pick_best_candidate(content_candidates)

    if title_topic and not _is_generic_candidate(title_topic):
        if content_topic and _score_candidate(content_topic) >= _score_candidate(title_topic) + 2:
            return content_topic
        return title_topic

    if content_topic:
        return content_topic
    return title_topic


def _refine_candidate(text: str) -> str:
    value = normalize_topic_text(text)
    if not value:
        return ""

    segments = _extract_domain_segments(text)
    if segments:
        combined = _combine_segments(segments)
        if combined and _drops_required_qualifiers(value, combined):
            return value
        if combined and _is_generic_candidate(combined) and not _is_generic_candidate(value):
            return value
        if combined and (
            _is_generic_candidate(value)
            or len(value) > 14
            or _score_candidate(combined) >= _score_candidate(value) - 1
        ):
            return combined

    return value


def _extract_domain_segments(text: str) -> list[str]:
    seen = set()
    segments: list[str] = []
    for term in _extract_pattern_terms(text):
        if term in seen:
            continue
        seen.add(term)
        segments.append(term)
    for raw_part in SEGMENT_SPLIT_RE.split(text or ""):
        segment = normalize_topic_text(raw_part)
        segment = _strip_segment_filler(segment)
        if not is_meaningful_topic(segment):
            continue
        if not _contains_domain_hint(segment):
            continue
        if segment in GENERIC_SEGMENTS:
            continue
        if segment in seen:
            continue
        seen.add(segment)
        segments.append(segment)
    return segments


def _combine_segments(segments: list[str]) -> str:
    compact_segments = [segment for segment in segments if len(segment) <= 12]
    if compact_segments:
        segments = compact_segments

    ranked = []
    seen = set()
    for segment in segments:
        if not segment or segment in seen:
            continue
        seen.add(segment)
        ranked.append((_score_candidate(segment), len(segment), segment))
    if not ranked:
        return ""

    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    chosen: list[str] = []
    for score, _, segment in ranked:
        if score <= 0:
            continue
        if any(segment in existing or existing in segment for existing in chosen):
            continue
        chosen.append(segment)
        if len(chosen) >= 2:
            break
    return "与".join(chosen)


def _pick_best_candidate(candidates: list[str]) -> str:
    if not candidates:
        return ""
    ranked = []
    seen = set()
    for item in candidates:
        value = normalize_topic_text(item)
        if not value or value in seen:
            continue
        seen.add(value)
        ranked.append((_score_candidate(value), len(value), value))
    if not ranked:
        return ""
    ranked.sort(key=lambda item: (-item[0], -item[1], item[2]))
    best_score, _, best_value = ranked[0]
    if best_score <= 0:
        return ""
    return best_value


def _score_candidate(topic: str) -> int:
    score = 0
    for hint in DOMAIN_HINTS:
        if hint in topic:
            score += 3
    for hint in TOPIC_HINT_WORDS:
        if hint in topic:
            score += 1
    for prefix in GENERIC_PREFIXES:
        if topic.startswith(prefix):
            score -= 6
    for suffix in GENERIC_SUFFIXES:
        if topic.endswith(suffix):
            score -= 4
    if "与" in topic:
        score += 1
    if any(ch.isdigit() for ch in topic):
        score += 2
    if 6 <= len(topic) <= 18:
        score += 2
    elif len(topic) > 24:
        score -= 2
    return score


def _contains_domain_hint(text: str) -> bool:
    return any(hint in text for hint in DOMAIN_HINTS) or bool(_extract_pattern_terms(text))


def _is_generic_candidate(topic: str) -> bool:
    if not topic:
        return True
    if topic in GENERIC_BARE_TOPICS:
        return True
    if topic in GENERIC_SEGMENTS:
        return True
    if any(topic.startswith(prefix) for prefix in GENERIC_PREFIXES):
        return True
    hint_count = sum(1 for hint in DOMAIN_HINTS if hint in topic)
    has_source_qualifier = any(qualifier in topic for qualifier in SOURCE_QUALIFIERS)
    if any(fragment in topic for fragment in ["论文提纲", "未来预测", "研究计划", "撰写安排", "文章撰写", "论文修改", "基金申请"]):
        return True
    if topic.endswith("问题") and hint_count <= 2:
        return True
    if ("论文引言" in topic or "科学问题" in topic) and hint_count <= 2 and not has_source_qualifier:
        return True
    return False


def _drops_required_qualifiers(original: str, candidate: str) -> bool:
    required = [qualifier for qualifier in SOURCE_QUALIFIERS if qualifier in original]
    if not required:
        return False
    return not any(qualifier in candidate for qualifier in required)


def _strip_segment_filler(text: str) -> str:
    value = text.strip()
    if re.search(r"(?:IR|FO)数据匹配(?:度)?", value):
        return "产能匹配"
    if "产能信息" in value or "产能数据" in value:
        return "产能匹配"
    while value:
        previous = value
        for prefix in [
            "重点涉及",
            "涉及",
            "目前",
            "主要是",
            "主要",
            "关于",
            "围绕",
            "针对",
            "引言部分需要突出",
            "引言部分",
            "需要突出",
            "需要",
            "突出",
            "梳理",
            "文章现在主要是",
            "文章现在",
            "现在主要是",
            "现在",
            "还要继续",
            "还要",
            "继续",
            "讨论",
            "分析",
        ]:
            if value.startswith(prefix):
                value = value[len(prefix) :].strip()
        for suffix in [
            "已经有了初步结果",
            "有了初步结果",
            "初步结果",
            "修改结构",
            "结构",
            "分享",
            "讨论",
        ]:
            if value.endswith(suffix):
                value = value[: -len(suffix)].strip()
        for marker in ["设为", "需要", "突出", "梳理", "已经", "有了", "不对", "乘以", "乘"]:
            if marker in value:
                head = value.split(marker, 1)[0].strip()
                if _contains_domain_hint(head):
                    value = head
                    break
        if value == previous:
            break
    return value


def _extract_pattern_terms(text: str) -> list[str]:
    value = text or ""
    terms: list[str] = []
    seen = set()
    for pattern, replacement in PATTERN_TERMS:
        if not pattern.search(value):
            continue
        normalized = normalize_topic_text(replacement)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        terms.append(normalized)
    return terms


def _strip_generic_edges(text: str) -> str:
    value = text.strip()
    changed = True
    while changed and value:
        changed = False
        for prefix in ["关于"]:
            if value.startswith(prefix):
                value = value[len(prefix):].strip()
                changed = True
        for suffix in ["的讨论会议", "讨论会议", "的讨论", "会议总结", "会议", "讨论"]:
            if value.endswith(suffix):
                value = value[: -len(suffix)].strip()
                changed = True
    return value
