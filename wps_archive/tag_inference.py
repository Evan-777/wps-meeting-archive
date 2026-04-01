from __future__ import annotations


DEFAULT_TAGS = ["方案设计"]

TAG_RULES = [
    ("论文修改", ["论文修改", "修改意见", "审稿意见", "返修"]),
    ("文献综述", ["文献综述", "引言", "综述"]),
    ("论文撰写", ["论文", "摘要", "撰写", "投稿", "本子", "基金申请"]),
    ("数据收集", ["数据整理", "数据分类", "数据收集", "清单", "产能", "匹配", "汇总", "缺失数据"]),
    ("数据分析", ["分析", "对比", "阈值", "差异", "源汇", "识别", "健康影响", "暴露", "不平等", "量级", "反演"]),
    ("模式模拟", ["模型", "伴随", "模拟", "情景", "预测", "优化函数", "参数设置"]),
    ("研究方向及假设", ["科学问题", "研究方向", "假设", "机制", "驱动力", "空间异质性"]),
    ("方案设计", ["方案", "设计"]),
]


def infer_tags(title: str = "", topic: str = "") -> list[str]:
    text = f"{title} {topic}".strip()
    if not text:
        return list(DEFAULT_TAGS)

    tags: list[str] = []
    for tag, keywords in TAG_RULES:
        if any(keyword in text for keyword in keywords):
            tags.append(tag)

    deduped: list[str] = []
    for tag in tags:
        if tag not in deduped:
            deduped.append(tag)

    if not deduped:
        return list(DEFAULT_TAGS)

    return deduped[:2]
