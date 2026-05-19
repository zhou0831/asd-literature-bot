from src.models import LiteratureItem
from src.storage import Store


def test_has_recommendation_for_date(tmp_path):
    store = Store(tmp_path / "recommended.sqlite")
    try:
        assert store.has_recommendation_for_date("2026-05-19") is False
        store.save_recommendation(
            LiteratureItem(
                title="A paper",
                candidate_id="2026-05-19_abc123",
                score=1,
            )
        )
        assert store.has_recommendation_for_date("2026-05-19") is True
        assert store.has_recommendation_for_date("2026-05-20") is False
    finally:
        store.close()
