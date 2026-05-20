from src.models import LiteratureItem
from scripts.run_daily import select_daily_item
from src.summarize import render_daily_report


def test_daily_always_saves_one_recommendation_when_ranked_not_empty():
    item = LiteratureItem(title="Core", topic_fit_score=70, recommendation_score=80, recommendation_tier="core")
    selected, tier = select_daily_item([item])
    assert selected is item
    assert tier == "core"
    assert selected.recommendation_tier == "core"


def test_selects_high_match_candidate_first():
    low = LiteratureItem(title="Low", topic_fit_score=40, recommendation_score=45, strong_exclusion=False)
    high = LiteratureItem(title="High", topic_fit_score=70, recommendation_score=80, strong_exclusion=False)
    selected, tier = select_daily_item([low, high])
    assert selected is high
    assert tier == "core"


def test_selects_non_strong_exclusion_when_no_core():
    excluded = LiteratureItem(title="Excluded", topic_fit_score=10, recommendation_score=35, strong_exclusion=True)
    exploratory = LiteratureItem(title="Exploratory", topic_fit_score=42, recommendation_score=48, strong_exclusion=False)
    selected, tier = select_daily_item([excluded, exploratory])
    assert selected is exploratory
    assert tier == "exploratory"
    assert selected.low_confidence is True


def test_selects_very_low_confidence_when_all_strong_exclusion():
    item = LiteratureItem(title="Excluded", topic_fit_score=10, recommendation_score=20, strong_exclusion=True)
    selected, tier = select_daily_item([item])
    assert selected is item
    assert tier == "very_low_confidence"
    assert selected.recommendation_tier == "very_low_confidence"
    report = render_daily_report(selected, low_confidence=True)
    assert "不建议直接导入 Zotero" in report


def test_empty_ranked_selects_none():
    selected, tier = select_daily_item([])
    assert selected is None
    assert tier == "none"


def test_low_confidence_recommendation_enters_weekly_pool(tmp_path):
    from src.storage import Store

    store = Store(tmp_path / "recommended.sqlite")
    try:
        item = LiteratureItem(title="Exploratory", candidate_id="2026-05-20_x", recommendation_score=45, recommendation_tier="exploratory")
        store.save_recommendation(item)
        rows = store.recent_recommendations(limit=7)
        assert rows[0].recommendation_tier == "exploratory"
    finally:
        store.close()
