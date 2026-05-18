from __future__ import annotations

from .models import LiteratureItem
from .text_utils import normalize_doi, normalize_identifier, normalize_title, title_similarity


def filter_duplicates(
    items: list[LiteratureItem],
    history_keys: dict[str, set[str]],
    zotero_items: list[dict[str, str]] | None = None,
    title_threshold: float = 0.92,
) -> list[LiteratureItem]:
    zotero_items = zotero_items or []
    seen_doi = set(history_keys.get("doi", set()))
    seen_pmid = set(history_keys.get("pmid", set()))
    seen_pmcid = set(history_keys.get("pmcid", set()))
    seen_titles = set(history_keys.get("title", set()))
    for item in zotero_items:
        if item.get("doi"):
            seen_doi.add(normalize_doi(item["doi"]))
        if item.get("pmid"):
            seen_pmid.add(normalize_identifier(item["pmid"]))
        if item.get("title"):
            seen_titles.add(normalize_title(item["title"]))

    unique: list[LiteratureItem] = []
    for item in items:
        doi = normalize_doi(item.doi)
        pmid = normalize_identifier(item.pmid)
        pmcid = normalize_identifier(item.pmcid)
        title = normalize_title(item.title)
        if doi and doi in seen_doi:
            continue
        if pmid and pmid in seen_pmid:
            continue
        if pmcid and pmcid in seen_pmcid:
            continue
        if any(title_similarity(title, existing) >= title_threshold for existing in seen_titles):
            continue
        unique.append(item)
        if doi:
            seen_doi.add(doi)
        if pmid:
            seen_pmid.add(pmid)
        if pmcid:
            seen_pmcid.add(pmcid)
        if title:
            seen_titles.add(title)
    return unique

