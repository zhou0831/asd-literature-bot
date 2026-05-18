from __future__ import annotations

from datetime import date, timedelta
from html import unescape
from typing import Any

import requests

from .models import LiteratureItem


USER_AGENT = "asd-literature-bot/0.1 (literature recommendation workflow)"


def _get_json(url: str, params: dict[str, Any], timeout: int = 25) -> dict[str, Any]:
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return response.json()


def search_all(config: dict[str, Any]) -> list[LiteratureItem]:
    search_cfg = config.get("search", {})
    queries = search_cfg.get("queries") or []
    max_results = int(search_cfg.get("max_results_per_source", 20))
    days_back = int(search_cfg.get("days_back", 21))
    items: list[LiteratureItem] = []
    for query in queries:
        for searcher in (search_europe_pmc, search_openalex, search_pubmed):
            try:
                items.extend(searcher(query, max_results, days_back))
            except requests.RequestException as exc:
                print(f"Warning: {searcher.__name__} failed: {exc}")
    return supplement_missing_dois(items)


def search_europe_pmc(query: str, limit: int, days_back: int) -> list[LiteratureItem]:
    start = (date.today() - timedelta(days=days_back)).isoformat()
    full_query = f'({query}) AND FIRST_PDATE:[{start} TO {date.today().isoformat()}]'
    data = _get_json(
        "https://www.ebi.ac.uk/europepmc/webservices/rest/search",
        {
            "query": full_query,
            "format": "json",
            "pageSize": limit,
            "sort": "FIRST_PDATE_D desc",
        },
    )
    out: list[LiteratureItem] = []
    for row in data.get("resultList", {}).get("result", []):
        title = unescape(row.get("title") or "")
        if not title:
            continue
        doi = row.get("doi") or ""
        full_urls = row.get("fullTextUrlList", {}).get("fullTextUrl") or [{}]
        url = f"https://doi.org/{doi}" if doi else full_urls[0].get("url", "")
        out.append(
            LiteratureItem(
                title=title,
                authors=_split_authors(row.get("authorString", "")),
                year=str(row.get("pubYear") or ""),
                venue=row.get("journalTitle") or row.get("bookOrReportDetails") or "",
                doi=doi,
                url=url or f"https://europepmc.org/article/{row.get('source', 'MED')}/{row.get('id', '')}",
                abstract=unescape(row.get("abstractText") or ""),
                source="Europe PMC",
                pmid=row.get("pmid") or "",
                pmcid=row.get("pmcid") or "",
            )
        )
    return out


def search_openalex(query: str, limit: int, days_back: int) -> list[LiteratureItem]:
    start = (date.today() - timedelta(days=days_back)).isoformat()
    data = _get_json(
        "https://api.openalex.org/works",
        {
            "search": query,
            "filter": f"from_publication_date:{start},to_publication_date:{date.today().isoformat()}",
            "sort": "publication_date:desc",
            "per-page": min(limit, 50),
        },
    )
    out: list[LiteratureItem] = []
    for row in data.get("results", []):
        title = unescape(row.get("title") or row.get("display_name") or "")
        if not title:
            continue
        doi = (row.get("doi") or "").replace("https://doi.org/", "")
        authors = [
            authorship.get("author", {}).get("display_name", "")
            for authorship in row.get("authorships", [])
            if authorship.get("author", {}).get("display_name")
        ]
        venue = row.get("primary_location", {}).get("source", {}) or {}
        out.append(
            LiteratureItem(
                title=title,
                authors=authors,
                year=str(row.get("publication_year") or ""),
                venue=venue.get("display_name", ""),
                doi=doi,
                url=row.get("doi") or row.get("id") or "",
                abstract=unescape(_openalex_abstract(row.get("abstract_inverted_index") or {})),
                source="OpenAlex",
            )
        )
    return out


def search_pubmed(query: str, limit: int, days_back: int) -> list[LiteratureItem]:
    start = (date.today() - timedelta(days=days_back)).strftime("%Y/%m/%d")
    end = date.today().strftime("%Y/%m/%d")
    term = f'({query}) AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'
    ids = _get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        {"db": "pubmed", "term": term, "retmode": "json", "retmax": limit, "sort": "pub date"},
    ).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    data = _get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi",
        {"db": "pubmed", "id": ",".join(ids), "retmode": "json"},
    )
    out: list[LiteratureItem] = []
    result = data.get("result", {})
    for pmid in ids:
        row = result.get(pmid, {})
        title = unescape(row.get("title") or "")
        if not title:
            continue
        article_ids = {item.get("idtype"): item.get("value") for item in row.get("articleids", [])}
        doi = article_ids.get("doi", "")
        out.append(
            LiteratureItem(
                title=title.rstrip("."),
                authors=[a.get("name", "") for a in row.get("authors", []) if a.get("name")],
                year=(row.get("pubdate") or "")[:4],
                venue=row.get("fulljournalname") or row.get("source") or "",
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                abstract="",
                source="PubMed",
                pmid=pmid,
            )
        )
    return out


def supplement_missing_dois(items: list[LiteratureItem]) -> list[LiteratureItem]:
    for item in items:
        if item.doi or not item.title:
            continue
        try:
            data = _get_json("https://api.crossref.org/works", {"query.title": item.title, "rows": 1})
            hits = data.get("message", {}).get("items", [])
            if hits and hits[0].get("DOI"):
                item.doi = hits[0]["DOI"]
                item.url = item.url or f"https://doi.org/{item.doi}"
        except requests.RequestException:
            continue
    return items


def _split_authors(value: str) -> list[str]:
    value = value.replace(" and ", ", ")
    return [part.strip() for part in value.split(",") if part.strip()]


def _openalex_abstract(index: dict[str, list[int]]) -> str:
    if not index:
        return ""
    pairs: list[tuple[int, str]] = []
    for word, positions in index.items():
        pairs.extend((pos, word) for pos in positions)
    return " ".join(word for _, word in sorted(pairs))
