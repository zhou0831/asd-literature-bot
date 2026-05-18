from __future__ import annotations

from typing import Any

from .config import env, load_dotenv
from .models import LiteratureItem


DEFAULT_MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MIMO_MODEL = "mimo-v2.5-pro"
HUMANIZED_STYLE_GUIDE = (
    "写得像一个认真读文献的人在给自己做笔记。直接说事实，少铺垫。"
    "不要用宣传腔，不要写“至关重要、显著体现、关键作用、不断演变的格局、值得注意的是、此外”。"
    "避免机械三段式和“不仅……而且……”结构。句子长短可以变化，但不要故作文学化。"
    "承认不确定性时要具体，比如“摘要没有说明样本细节，需要看全文确认”。"
    "只输出最终文本，不要输出思考过程、分析过程、自我说明或“作为 AI”之类的话。"
)


def mimo_configured() -> bool:
    load_dotenv()
    return bool(env("MIMO_API_KEY"))


def generate_article_overview_with_mimo(item: LiteratureItem) -> str | None:
    load_dotenv()
    api_key = env("MIMO_API_KEY")
    if not api_key:
        print("Mimo overview skipped: MIMO_API_KEY is not configured.")
        return None

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=env("MIMO_BASE_URL", DEFAULT_MIMO_BASE_URL),
        default_headers={"api-key": api_key},
    )
    completion = client.chat.completions.create(
        model=env("MIMO_MODEL", DEFAULT_MIMO_MODEL),
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个严谨的中文科研助理，帮助用户筛选 ASD 儿童动态社会意图加工相关文献。"
                    "只根据用户提供的题名、摘要和元数据写作，不要编造全文中没有的信息。"
                    "输出中文，不要直接粘贴英文摘要。"
                    + HUMANIZED_STYLE_GUIDE
                ),
            },
            {
                "role": "user",
                "content": _article_prompt(item),
            },
        ],
        temperature=0.2,
        top_p=0.9,
        max_tokens=900,
        stream=False,
    )
    text = _message_text(completion)
    if text and text.strip():
        print("Mimo overview generated.")
        return text.strip()
    print("Mimo overview returned empty content.")
    return None


def generate_weekly_report_with_mimo(items: list[LiteratureItem]) -> str | None:
    load_dotenv()
    api_key = env("MIMO_API_KEY")
    if not api_key:
        print("Mimo weekly summary skipped: MIMO_API_KEY is not configured.")
        return None
    if not items:
        return None

    from openai import OpenAI

    client = OpenAI(
        api_key=api_key,
        base_url=env("MIMO_BASE_URL", DEFAULT_MIMO_BASE_URL),
        default_headers={"api-key": api_key},
    )
    completion = client.chat.completions.create(
        model=env("MIMO_MODEL", DEFAULT_MIMO_MODEL),
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个严谨的中文科研助理，帮助用户做 ASD 社会认知文献周报。"
                    "用户已经用本地规则完成评分和排序；你必须尊重给定顺序，不要自行改变 Top 3。"
                    "只根据给定题名、摘要和评分信息写作，不要编造全文中没有的信息。"
                    + HUMANIZED_STYLE_GUIDE
                ),
            },
            {
                "role": "user",
                "content": _weekly_prompt(items),
            },
        ],
        temperature=0.2,
        top_p=0.9,
        max_tokens=1200,
        stream=False,
    )
    text = _message_text(completion)
    if text and text.strip():
        print("Mimo weekly summary generated.")
        return text.strip()
    print("Mimo weekly summary returned empty content.")
    return None


def _article_prompt(item: LiteratureItem) -> str:
    authors = ", ".join(item.authors[:8]) if item.authors else "未知"
    return f"""请为下面这篇文献写“文章讲了什么”部分，用 3-5 个短段落中文概述。

要求：
- 不要直接翻译或粘贴英文摘要。
- 说明研究问题、研究对象/方法、主要发现或结论。
- 如果摘要证据不足，请明确说需要打开全文复核。
- 最后一段说明它和我的课题“ASD 儿童动态社会意图加工，EEG + 眼动，动态社会互动视频”有什么关系。
- 不要写标题，不要写列表编号。

题名：{item.title}
作者：{authors}
年份：{item.year or "未知"}
期刊或平台：{item.venue or item.source or "未知"}
DOI：{item.doi or "无"}
URL：{item.url or "无"}
推荐模块：{item.module}
关键词命中：{item.reason}
摘要：{item.abstract or "检索源没有返回摘要。"}
"""


def _weekly_prompt(items: list[LiteratureItem]) -> str:
    rows = []
    for idx, item in enumerate(items[:3], 1):
        rows.append(
            f"""Top {idx}
candidate_id：{item.candidate_id}
题名：{item.title}
年份：{item.year or "未知"}
期刊或平台：{item.venue or item.source or "未知"}
评分：{item.score}
推荐模块：{item.module}
关键词命中：{item.reason}
DOI：{item.doi or "无"}
URL：{item.url or "无"}
摘要：{item.abstract or "检索源没有返回摘要。"}"""
        )
    count = len(items[:3])
    return f"""下面是本周已按本地评分排序后的 Top {count} 候选文献。请严格保持这个顺序，不要重新排名。

请输出中文 Markdown，只写“本周最值得读的 {count} 篇”这个部分：
- 严格按已给出的 Top 顺序逐篇写。只写输入里出现的文献，不要补不存在的 Top。
- 每篇包含 candidate_id、为什么值得读、对我的课题有什么启发。
- 每篇 2-4 句话，语言简洁。
- 不要写总标题，因为外层报告已经有标题。
- 不要使用粗体，不要用“为什么值得读：”“对我的课题有什么启发：”这类机械标签。
- 可以用“### Top 1”这种小标题，然后接自然段。
- 不要写“用户要求”“我应该”“作为 AI”“下面我将”等思考过程或自我说明。

不要编造全文信息；如果摘要不足，请明确说需要看全文复核。

{chr(10).join(rows)}
"""


def _message_text(completion: Any) -> str:
    choice = completion.choices[0]
    message = choice.message
    content = getattr(message, "content", None)
    if content:
        return _strip_visible_reasoning(content)
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        return _strip_visible_reasoning(reasoning_content)
    if isinstance(message, dict):
        return _strip_visible_reasoning(message.get("content") or message.get("reasoning_content") or "")
    return ""


def _strip_visible_reasoning(text: str) -> str:
    text = (text or "").strip()
    if not text:
        return ""
    markers = ["### Top 1", "Top 1", "## Top 1"]
    for marker in markers:
        idx = text.find(marker)
        if idx > 0:
            text = text[idx:].strip()
            break
    banned_prefixes = ("用户", "作为 AI", "作为AI", "我应该", "我会", "让我", "首先", "所以，我", "再看")
    lines = [line for line in text.splitlines() if not line.strip().startswith(banned_prefixes)]
    return "\n".join(lines).strip()
