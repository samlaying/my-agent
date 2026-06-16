"""context.router -- keyword-based intent classifier (Phase 1)"""

INTENT_KEYWORDS: dict[str, list[str]] = {
    "复盘":  ["花了", "消费", "买了", "支出", "付款", "花费", "多少钱", "开销"],
    "变帅":  ["吃了", "喝水", "卡路里", "饮食", "健康", "提醒喝水", "体重", "喝了多少"],
    "英语":  ["单词", "听力", "语法", "翻译", "四六级", "发音", "阅读理解"],
    "工作":  ["会议", "复盘会", "周报", "月报", "客户", "竞品", "汇报"],
    "社交":  ["人情", "情商", "聊天", "维护群", "话术"],
}


def classify_intent(text: str) -> list[str]:
    """Analyze user input and return a list of matched intent labels.

    First version: keyword + pattern matching (no LLM token cost).
    Returns e.g. ["复盘"] or ["复盘", "变帅"] or [].
    """
    if not text or not text.strip():
        return []

    matched = []
    for label, keywords in INTENT_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            matched.append(label)
    return matched
