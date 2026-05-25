from src.models import LiteratureItem
from src.summarize import SearchDiagnostics, render_daily_report


def test_daily_report_contains_metadata_status_and_search_diagnostics(monkeypatch):
    monkeypatch.setattr("src.summarize.generate_article_overview_with_mimo", lambda item: None)
    item = LiteratureItem(
        title="Joint attention eye-tracking battery",
        abstract="This abstract describes joint attention and gaze cueing in autistic children using eye tracking.",
        source="PubMed",
        abstract_status="full",
        abstract_source="PubMed",
        metadata_sources=["PubMed", "Crossref"],
        reading_priority="skim",
        recommendation_tier="core",
        module="A",
    )
    diagnostics = SearchDiagnostics(
        raw_candidate_count=3,
        deduped_candidate_count=2,
        abstract_full_count=1,
        abstract_missing_count=1,
    )

    report = render_daily_report(item, candidate_diagnostics=diagnostics)

    assert "## 元数据状态" in report
    assert "摘要状态" in report
    assert "摘要来源" in report
    assert "## 阅读优先级" in report
    assert "skim" in report
    assert "## 检索诊断" in report
    assert "原始候选数" in report
    assert "去重后候选数" in report
