from src.models import LiteratureItem
from src.summarize import render_daily_report, render_weekly_report, summarize_article_in_chinese
from src.llm import _strip_visible_reasoning


def test_daily_report_uses_chinese_overview_not_raw_english_abstract(monkeypatch):
    monkeypatch.setattr("src.summarize.generate_article_overview_with_mimo", lambda item: None)
    item = LiteratureItem(
        title="Joint attention and autism",
        abstract=(
            "Purpose This study examined joint attention in children with autism. "
            "Methods Data were collected from n = 40 children using eye-tracking. "
            "Results Findings suggested group differences in gaze cueing."
        ),
        candidate_id="2026-05-18_test",
        score=12,
        reason="joint attention；autism；eye-tracking",
        module="A",
    )
    overview = summarize_article_in_chinese(item)
    report = render_daily_report(item)
    assert "这篇文章主要讨论" in overview.text
    assert "共同注意" in overview.text
    assert overview.ai_generated is False
    assert "Purpose This study examined" not in report
    assert "AI 生成提醒" not in report


def test_daily_report_marks_ai_generated_overview(monkeypatch):
    monkeypatch.setattr(
        "src.summarize.generate_article_overview_with_mimo",
        lambda item: {
            "overview": "这是 MiMo 生成的中文概述。",
            "learning_points": ["学习点一"],
            "relevance": "与模块 A 相关。",
            "limitations": "仍需看全文。",
        },
    )
    item = LiteratureItem(
        title="Joint attention and autism",
        abstract="Purpose This study examined joint attention in children with autism.",
        candidate_id="2026-05-18_test",
        score=12,
        reason="joint attention；autism",
        module="A",
    )
    overview = summarize_article_in_chinese(item)
    report = render_daily_report(item)
    assert overview.ai_generated is True
    assert "这是 MiMo 生成的中文概述。" in report
    assert "学习点一" in report
    assert "AI 生成提醒" in report


def test_weekly_report_uses_score_order_and_marks_ai_content(monkeypatch):
    monkeypatch.setattr("src.summarize.generate_weekly_report_with_mimo", lambda items: "### Top 1\n\nAI 周报解读。")
    low = LiteratureItem(title="Low score", candidate_id="low", score=1, module="A")
    high = LiteratureItem(title="High score", candidate_id="high", score=10, module="C")
    report = render_weekly_report([low, high])
    assert "- 1. High score" in report
    assert "- 2. Low score" in report
    assert "AI 周报解读。" in report
    assert "AI 生成提醒" in report


def test_strip_visible_reasoning_keeps_final_weekly_text():
    raw = "用户期望我解释 Top 3。\n我应该先分析。\n### Top 1\n\n正式解读。"
    assert _strip_visible_reasoning(raw) == "### Top 1\n\n正式解读。"
