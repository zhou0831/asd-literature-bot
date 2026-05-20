from __future__ import annotations

import json
from typing import Any

from .config import env, load_dotenv
from .models import LiteratureItem
from .output_guard import is_clean_llm_output, sanitize_llm_output


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


def generate_article_overview_with_mimo(item: LiteratureItem) -> dict[str, Any] | None:
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
    completion = _create_chat_completion(
        client,
        messages=[
            {
                "role": "system",
                "content": (
                    "你是中文科研助理。只返回 JSON 对象。不要返回 Markdown、解释、写作要求或推理过程。"
                    + HUMANIZED_STYLE_GUIDE
                ),
            },
            {"role": "user", "content": _article_prompt(item)},
        ],
        max_tokens=1000,
        json_mode=True,
    )
    text = _message_text(completion)
    summary = _parse_article_summary_json(text)
    if summary:
        print("Mimo overview generated.")
        return summary
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
    completion = _create_chat_completion(
        client,
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
        max_tokens=1200,
        json_mode=False,
    )
    text = _message_text(completion)
    if text and text.strip():
        print("Mimo weekly summary generated.")
        return text.strip()
    print("Mimo weekly summary returned empty content.")
    return None


def _article_prompt(item: LiteratureItem) -> str:
    authors = ", ".join(item.authors[:8]) if item.authors else "未知"
    return f"""你将收到一篇文献的元数据。只返回一个 JSON 对象，不返回 Markdown，不返回解释。
JSON schema:
{{"overview": string, "learning_points": string[], "relevance": string, "limitations": string}}

写作约束：
overview 用中文写 3-5 个短段落，只根据题名、摘要和元数据写。如果摘要不足，写“仅根据摘要判断，仍需打开全文复核”。
relevance 说明它与 ASD 儿童动态社会意图加工、A/B/C 模块、EEG/眼动、动态社会互动视频的具体关系。
如果文章只是泛泛 ASD 诊断、AI 分类、面孔识别或静态视觉注意综述，写“不属于当前课题核心文献”。

metadata:
title={item.title}
authors={authors}
year={item.year or "未知"}
venue={item.venue or item.source or "未知"}
doi={item.doi or "无"}
url={item.url or "无"}
module={item.module}
matched_terms={item.reason}
topic_fit_score={getattr(item, "topic_fit_score", item.score)}
recommendation_score={getattr(item, "recommendation_score", item.score)}
penalty_reasons={", ".join(getattr(item, "penalty_reasons", []))}
abstract={item.abstract or "检索源没有返回摘要。"}
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
        text = sanitize_llm_output(content)
        return text if is_clean_llm_output(text) else ""
    if isinstance(message, dict):
        content = message.get("content")
        if not content:
            return ""
        text = sanitize_llm_output(content)
        return text if is_clean_llm_output(text) else ""
    return ""


def _create_chat_completion(client: Any, messages: list[dict[str, str]], max_tokens: int, json_mode: bool) -> Any:
    kwargs: dict[str, Any] = {
        "model": env("MIMO_MODEL", DEFAULT_MIMO_MODEL),
        "messages": messages,
        "temperature": 0.2,
        "top_p": 0.9,
        "max_tokens": max_tokens,
        "stream": False,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}
    try:
        return client.chat.completions.create(**kwargs)
    except TypeError:
        kwargs.pop("response_format", None)
        return client.chat.completions.create(**kwargs)
    except Exception as exc:
        if json_mode and "response_format" in str(exc):
            kwargs.pop("response_format", None)
            return client.chat.completions.create(**kwargs)
        raise


def _parse_article_summary_json(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    cleaned = sanitize_llm_output(text)
    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        cleaned = cleaned[start : end + 1]
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    overview = sanitize_llm_output(str(data.get("overview") or ""))
    if not is_clean_llm_output(overview):
        return None
    learning_points = [
        sanitize_llm_output(str(point))
        for point in (data.get("learning_points") or [])
        if isinstance(point, str) and is_clean_llm_output(str(point))
    ][:4]
    relevance = sanitize_llm_output(str(data.get("relevance") or ""))
    limitations = sanitize_llm_output(str(data.get("limitations") or ""))
    return {
        "overview": overview,
        "learning_points": learning_points,
        "relevance": relevance if is_clean_llm_output(relevance) else "",
        "limitations": limitations if is_clean_llm_output(limitations) else "",
    }
