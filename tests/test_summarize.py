from src.models import LiteratureItem
from src.summarize import render_daily_report, summarize_article_in_chinese


def test_daily_report_uses_chinese_overview_not_raw_english_abstract():
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
    assert "这篇文章主要讨论" in overview
    assert "共同注意" in overview
    assert "Purpose This study examined" not in report

