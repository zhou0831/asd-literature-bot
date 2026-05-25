from __future__ import annotations

from html import unescape
from typing import Any

import requests

from .models import LiteratureItem
from .search import _get_json, _openalex_abstract, fetch_pubmed_details


MIN_ABSTRACT_LENGTH = 80


def enrich_metadata(items: list[LiteratureItem]) -> list[LiteratureItem]:
    for item in items:
        _normalize_metadata_state(item)
        if _needs_abstract(item) and item.pmid:
            _apply_pubmed(item)
        if _needs_abstract(item) and (item.pmid or item.pmcid or item.doi):
            _apply_europe_pmc(item)
        if _needs_abstract(item) and item.doi:
            _apply_openalex_by_doi(item)
        if item.doi or item.title:
            _apply_crossref(item)
        _normalize_metadata_state(item)
    return items


def _needs_abstract(item: LiteratureItem) -> bool:
    return len((item.abstract or "").strip()) < MIN_ABSTRACT_LENGTH


def _normalize_metadata_state(item: LiteratureItem) -> None:
    if item.abstract and not item.abstract_source:
        item.abstract_source = item.source or ""
    if item.source and item.source not in item.metadata_sources:
        item.metadata_sources.append(item.source)
    if len((item.abstract or "").strip()) >= MIN_ABSTRACT_LENGTH:
        item.abstract_status = "full"
    elif item.abstract.strip():
        item.abstract_status = "metadata_only"
    elif item.title and any([item.year, item.venue, item.doi, item.url, item.authors]):
        item.abstract_status = "metadata_only"
    elif item.title:
        item.abstract_status = "title_only"
    else:
        item.abstract_status = "missing"


def _apply_pubmed(item: LiteratureItem) -> None:
    try:
        details = fetch_pubmed_details([item.pmid])
    except requests.RequestException:
        return
    if details:
        _merge_item(item, details[0], "PubMed")


def _apply_europe_pmc(item: LiteratureItem) -> None:
    query = ""
    if item.pmcid:
        query = f"PMCID:{item.pmcid}"
    elif item.pmid:
        query = f"EXT_ID:{item.pmid}"
    elif item.doi:
        query = f'DOI:"{item.doi}"'
    if not query:
        return
    try:
        data = _get_json(
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
            {"query": query, "format": "json", "pageSize": 1},
        )
    except requests.RequestException:
        return
    rows = data.get("resultList", {}).get("result", [])
    if not rows:
        return
    row = rows[0]
    abstract = unescape(row.get("abstractText") or "")
    if abstract and _needs_abstract(item):
        item.abstract = abstract
        item.abstract_source = "Europe PMC"
    item.doi = item.doi or row.get("doi") or ""
    item.pmid = item.pmid or row.get("pmid") or ""
    item.pmcid = item.pmcid or row.get("pmcid") or ""
    item.venue = item.venue or row.get("journalTitle") or ""
    item.year = item.year or str(row.get("pubYear") or "")
    _mark_source(item, "Europe PMC")


def _apply_openalex_by_doi(item: LiteratureItem) -> None:
    doi = item.doi.replace("https://doi.org/", "").strip()
    if not doi:
        return
    try:
        data = _get_json("https://api.openalex.org/works/https://doi.org/" + doi, {})
    except requests.RequestException:
        return
    abstract = unescape(_openalex_abstract(data.get("abstract_inverted_index") or {}))
    if abstract and _needs_abstract(item):
        item.abstract = abstract
        item.abstract_source = "OpenAlex"
    item.year = item.year or str(data.get("publication_year") or "")
    item.url = item.url or data.get("doi") or data.get("id") or ""
    venue = data.get("primary_location", {}).get("source", {}) or {}
    item.venue = item.venue or venue.get("display_name", "")
    _mark_source(item, "OpenAlex")


def _apply_crossref(item: LiteratureItem) -> None:
    params: dict[str, Any]
    url: str
    if item.doi:
        url = "https://api.crossref.org/works/" + item.doi
        params = {}
    else:
        url = "https://api.crossref.org/works"
        params = {"query.title": item.title, "rows": 1}
    try:
        data = _get_json(url, params)
    except requests.RequestException:
        return
    message = data.get("message", {})
    row = message if item.doi else (message.get("items") or [{}])[0]
    doi = row.get("DOI") or ""
    if doi:
        item.doi = item.doi or doi
        item.url = item.url or f"https://doi.org/{doi}"
    titles = row.get("container-title") or []
    if titles:
        item.venue = item.venue or titles[0]
    published = row.get("published-print") or row.get("published-online") or {}
    date_parts = published.get("date-parts") or []
    if date_parts and date_parts[0]:
        item.year = item.year or str(date_parts[0][0])
    _mark_source(item, "Crossref")


def _merge_item(target: LiteratureItem, source: LiteratureItem, source_name: str) -> None:
    if source.abstract and _needs_abstract(target):
        target.abstract = source.abstract
        target.abstract_source = source_name
    target.title = target.title or source.title
    target.authors = target.authors or source.authors
    target.year = target.year or source.year
    target.venue = target.venue or source.venue
    target.doi = target.doi or source.doi
    target.url = target.url or source.url
    target.pmid = target.pmid or source.pmid
    target.pmcid = target.pmcid or source.pmcid
    _mark_source(target, source_name)


def _mark_source(item: LiteratureItem, source: str) -> None:
    if source and source not in item.metadata_sources:
        item.metadata_sources.append(source)
