from src.dedupe import filter_duplicates
from src.models import LiteratureItem


def test_dedupe_excludes_same_doi():
    items = [
        LiteratureItem(title="A new ASD social cognition paper", doi="10.1000/test"),
        LiteratureItem(title="Another paper", doi="10.2000/keep"),
    ]
    history = {"doi": {"10.1000/test"}, "pmid": set(), "pmcid": set(), "title": set()}
    kept = filter_duplicates(items, history)
    assert [item.doi for item in kept] == ["10.2000/keep"]


def test_dedupe_excludes_similar_title():
    items = [LiteratureItem(title="Social cognition in autistic children")]
    history = {"doi": set(), "pmid": set(), "pmcid": set(), "title": {"social cognition in autistic children"}}
    assert filter_duplicates(items, history) == []

