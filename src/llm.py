from __future__ import annotations

from typing import Any

from .config import env, load_dotenv
from .models import LiteratureItem


DEFAULT_MIMO_BASE_URL = "https://api.xiaomimimo.com/v1"
DEFAULT_MIMO_MODEL = "mimo-v2.5-pro"


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
                ),
            },
            {
                "role": "user",
                "content": _article_prompt(item),
            },
        ],
        temperature=0.2,
        top_p=0.9,
        max_completion_tokens=900,
        stream=False,
    )
    text = _message_text(completion)
    if text and text.strip():
        print("Mimo overview generated.")
        return text.strip()
    print("Mimo overview returned empty content.")
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


def _message_text(completion: Any) -> str:
    choice = completion.choices[0]
    message = choice.message
    content = getattr(message, "content", None)
    if content:
        return content
    reasoning_content = getattr(message, "reasoning_content", None)
    if reasoning_content:
        return reasoning_content
    if isinstance(message, dict):
        return message.get("content") or message.get("reasoning_content") or ""
    return ""
