from __future__ import annotations

import re


PROMPT_LEAK_PHRASES = [
    "不要直接翻译",
    "不要直接粘贴",
    "说明研究问题",
    "如果摘要证据不足",
    "最后一段说明",
    "不要写标题",
    "不要写列表编号",
    "输出中文",
    "只输出最终文本",
    "不要输出思考过程",
    "不要输出分析过程",
    "不要输出自我说明",
    "写得像一个认真读文献的人",
]

ANALYSIS_PHRASES = [
    "现在，分析",
    "现在分析",
    "分析提供的文献信息",
    "步骤：",
    "第一步",
    "第二步",
    "我应该",
    "我可以",
    "我的任务是",
    "用户要求",
    "作为 AI",
    "作为AI",
    "下面我将",
]

LEAK_PHRASES = [
    "system prompt",
    "developer",
    "prompt",
    "reasoning_content",
    "scratchpad",
    "chain of thought",
    "思考过程",
    "分析过程",
]

METADATA_LABELS = [
    "题名：",
    "作者：",
    "年份：",
    "期刊：",
    "期刊或平台：",
    "DOI：",
    "URL：",
    "推荐模块：",
    "关键词命中：",
    "摘要：",
]


def sanitize_llm_output(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json|markdown|md)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    cleaned = cleaned.strip().strip(">")
    marker = "最终文本："
    if marker in cleaned:
        cleaned = cleaned.split(marker, 1)[1].strip()
    return cleaned.replace("**", "").strip()


def is_clean_llm_output(text: str) -> bool:
    cleaned = sanitize_llm_output(text)
    if not cleaned:
        return False
    lowered = cleaned.lower()
    if any(phrase.lower() in lowered for phrase in PROMPT_LEAK_PHRASES):
        return False
    if any(phrase.lower() in lowered for phrase in ANALYSIS_PHRASES):
        return False
    if any(phrase.lower() in lowered for phrase in LEAK_PHRASES):
        return False
    if sum(1 for label in METADATA_LABELS if label in cleaned) >= 3:
        return False
    first_lines = [line.strip() for line in cleaned.splitlines()[:10]]
    task_like = sum(
        1
        for line in first_lines
        if line.startswith(("- 不要", "- 说明", "- 如果", "- 输出"))
    )
    if task_like >= 3:
        return False
    return True
