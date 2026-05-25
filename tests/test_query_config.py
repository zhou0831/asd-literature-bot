from src.config import load_config
from src.research_profile import load_research_profile


def test_query_config_contains_core_families():
    search = load_config()["search"]

    assert "days_back" not in search
    for pool in ["fresh_pool", "recent_pool", "evergreen_pool"]:
        assert pool in search

    families = search["query_families"]
    for family in ["A", "B", "C1", "C2", "methodology"]:
        assert family in families
        assert len(families[family]) >= 3


def test_research_profile_splits_c1_c2_modules():
    modules = load_research_profile()["modules"]

    assert "C1" in modules
    assert "C2" in modules
    assert "C" not in modules
