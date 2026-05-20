from types import SimpleNamespace

from src.llm import _message_text
from src.models import LiteratureItem
from src.output_guard import is_clean_llm_output
from src.summarize import render_daily_report


def test_rejects_prompt_leakage():
    dirty = """
不要直接翻译或粘贴英文摘要。
说明研究问题、研究对象/方法、主要发现或结论。
现在，分析提供的文献信息：
步骤：
"""
    assert is_clean_llm_output(dirty) is False


def test_rejects_metadata_echo():
    dirty = """
题名：A
作者：B
年份：2026
期刊：C
DOI：D
URL：E
推荐模块：A
关键词命中：x
摘要：y
"""
    assert is_clean_llm_output(dirty) is False


def test_does_not_use_reasoning_content():
    completion = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    reasoning_content="这是不应该显示的思考过程",
                )
            )
        ]
    )
    assert _message_text(completion) == ""


def test_accepts_clean_overview():
    clean = (
        "这篇范围综述讨论了 AI 在 ASD 视觉注意和面孔识别诊断中的应用。"
        "作者主要整理了不同模型和数据来源，但摘要没有显示它直接涉及动态社会意图加工或 EEG 对齐分析，"
        "因此它更适合作为背景材料，而不是当前课题的核心文献。"
    )
    assert is_clean_llm_output(clean) is True


def test_daily_report_has_no_prompt_leak(monkeypatch):
    monkeypatch.setattr("src.summarize.generate_article_overview_with_mimo", lambda item: None)
    item = LiteratureItem(
        title="Joint attention and autism",
        abstract="Purpose This study examined joint attention in children with autism.",
        candidate_id="2026-05-20_test",
        score=70,
        topic_fit_score=70,
        recommendation_score=72,
        reason="joint attention",
        module="A",
    )
    report = render_daily_report(item)
    for phrase in ["不要直接翻译", "现在，分析", "步骤：", "作为 AI", "reasoning_content"]:
        assert phrase not in report
