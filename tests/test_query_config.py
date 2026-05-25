from src.config import load_config


def test_query_config_contains_core_families():
    search = load_config()["search"]

    assert "days_back" not in search
    for pool in ["fresh_pool", "recent_pool", "evergreen_pool"]:
        assert pool in search

    families = search["query_families"]
    for family in ["A", "B", "C1", "C2", "methodology"]:
        assert family in families
        assert len(families[family]) >= 3
