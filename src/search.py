from __future__ import annotations

from datetime import date, timedelta
from html import unescape
from typing import Any
import xml.etree.ElementTree as ET

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


def _get_xml(url: str, params: dict[str, Any], timeout: int = 25) -> ET.Element:
    response = requests.get(
        url,
        params=params,
        timeout=timeout,
        headers={"User-Agent": USER_AGENT},
    )
    response.raise_for_status()
    return ET.fromstring(response.text)


def search_all(config: dict[str, Any]) -> list[LiteratureItem]:
    search_cfg = config.get("search", {})
    queries = _search_queries_by_family(search_cfg)
    pools = _search_pools(search_cfg)
    items: list[LiteratureItem] = []
    for pool in pools:
        days_back = pool.get("days_back")
        max_results = int(pool.get("max_results_per_source") or search_cfg.get("max_results_per_source", 20))
        for family, query in _queries_for_pool(queries, pool):
            for searcher in (search_europe_pmc, search_openalex, search_pubmed):
                try:
                    found = searcher(query, max_results, days_back)
                    for item in found:
                        _mark_metadata_source(item, item.source)
                        item.query_family = family
                        item.module = _family_module(family) or item.module
                    items.extend(found)
                except (requests.RequestException, ET.ParseError) as exc:
                    print(f"Warning: {searcher.__name__} failed: {exc}")
    return supplement_missing_dois(items)


def search_europe_pmc(query: str, limit: int, days_back: int | None) -> list[LiteratureItem]:
    full_query = f"({query})"
    if days_back is not None:
        start = (date.today() - timedelta(days=days_back)).isoformat()
        full_query = f'{full_query} AND FIRST_PDATE:[{start} TO {date.today().isoformat()}]'
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


def search_openalex(query: str, limit: int, days_back: int | None) -> list[LiteratureItem]:
    params: dict[str, Any] = {
        "search": query,
        "sort": "publication_date:desc",
        "per-page": min(limit, 50),
    }
    if days_back is not None:
        start = (date.today() - timedelta(days=days_back)).isoformat()
        params["filter"] = f"from_publication_date:{start},to_publication_date:{date.today().isoformat()}"
    data = _get_json(
        "https://api.openalex.org/works",
        params,
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


def search_pubmed(query: str, limit: int, days_back: int | None) -> list[LiteratureItem]:
    term = f"({query})"
    if days_back is not None:
        start = (date.today() - timedelta(days=days_back)).strftime("%Y/%m/%d")
        end = date.today().strftime("%Y/%m/%d")
        term = f'{term} AND ("{start}"[Date - Publication] : "{end}"[Date - Publication])'
    ids = _get_json(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
        {"db": "pubmed", "term": term, "retmode": "json", "retmax": limit, "sort": "pub date"},
    ).get("esearchresult", {}).get("idlist", [])
    if not ids:
        return []
    return fetch_pubmed_details(ids)


def fetch_pubmed_details(pmids: list[str]) -> list[LiteratureItem]:
    if not pmids:
        return []
    root = _get_xml(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
        {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
    )
    out: list[LiteratureItem] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = _node_text(article.find("./MedlineCitation/PMID"))
        title = unescape(_node_text(article.find("./MedlineCitation/Article/ArticleTitle"))).rstrip(".")
        if not title:
            continue
        doi = ""
        pmcid = ""
        for article_id in article.findall("./PubmedData/ArticleIdList/ArticleId"):
            if article_id.attrib.get("IdType") == "doi":
                doi = _node_text(article_id)
            elif article_id.attrib.get("IdType") == "pmc":
                pmcid = _node_text(article_id)
        abstract = unescape(_pubmed_abstract(article))
        out.append(
            LiteratureItem(
                title=title,
                authors=_pubmed_authors(article),
                year=_pubmed_year(article),
                venue=_node_text(article.find("./MedlineCitation/Article/Journal/Title"))
                or _node_text(article.find("./MedlineCitation/Article/Journal/ISOAbbreviation")),
                doi=doi,
                url=f"https://doi.org/{doi}" if doi else f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                abstract=abstract,
                source="PubMed",
                pmid=pmid,
                pmcid=pmcid,
                abstract_status="full" if abstract else "missing",
                abstract_source="PubMed" if abstract else "",
                metadata_sources=["PubMed"],
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
                _mark_metadata_source(item, "Crossref")
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


def _search_queries(search_cfg: dict[str, Any]) -> list[str]:
    return [query for _, query in _search_queries_by_family(search_cfg)]


def _search_queries_by_family(search_cfg: dict[str, Any]) -> list[tuple[str, str]]:
    families = search_cfg.get("query_families") or {}
    queries: list[tuple[str, str]] = []
    for family, family_queries in families.items():
        queries.extend((str(family), str(query)) for query in (family_queries or []) if str(query).strip())
    legacy_queries = search_cfg.get("queries") or []
    queries.extend(("legacy", str(query)) for query in legacy_queries if str(query).strip())
    return list(dict.fromkeys(queries))


def _search_pools(search_cfg: dict[str, Any]) -> list[dict[str, int | None]]:
    if any(key in search_cfg for key in ["fresh_pool", "recent_pool", "evergreen_pool"]):
        out: list[dict[str, int | None]] = []
        fresh = search_cfg.get("fresh_pool") or {}
        if fresh:
            out.append(
                {
                    "name": "fresh_pool",
                    "days_back": int(fresh.get("days_back", 180)),
                    "max_results_per_source": int(fresh.get("max_results_per_source", 20)),
                }
            )
        recent = search_cfg.get("recent_pool") or {}
        if recent:
            years_back = int(recent.get("years_back", 3))
            out.append(
                {
                    "name": "recent_pool",
                    "days_back": years_back * 365,
                    "max_results_per_source": int(recent.get("max_results_per_source", 20)),
                }
            )
        evergreen = search_cfg.get("evergreen_pool") or {}
        if evergreen.get("enabled", False):
            out.append(
                {
                    "name": "evergreen_pool",
                    "days_back": None,
                    "max_results_per_source": int(evergreen.get("max_results_per_run", 20)),
                    "query_limit": int(evergreen.get("query_limit", 5)),
                }
            )
        return out
    pools = search_cfg.get("pools")
    if not pools:
        return [{"name": "legacy", "days_back": int(search_cfg.get("days_back", 21))}]
    out: list[dict[str, int | None]] = []
    for name, pool in pools.items():
        raw_days = (pool or {}).get("days_back")
        out.append({"name": str(name), "days_back": None if raw_days is None else int(raw_days)})
    return out


def _family_module(family: str) -> str:
    return {
        "A": "A",
        "B": "B",
        "C1": "C1",
        "C2": "C2",
        "methodology": "方法学",
        "review": "综述",
    }.get(family, "")


def _queries_for_pool(queries: list[tuple[str, str]], pool: dict[str, int | None]) -> list[tuple[str, str]]:
    if pool.get("name") != "evergreen_pool":
        return queries
    if not queries:
        return []
    query_limit = int(pool.get("query_limit") or 5)
    offset = date.today().toordinal() % len(queries)
    rotated = queries[offset:] + queries[:offset]
    return rotated[: min(query_limit, len(rotated))]


def _mark_metadata_source(item: LiteratureItem, source: str) -> None:
    if source and source not in item.metadata_sources:
        item.metadata_sources.append(source)
    if item.abstract and not item.abstract_status:
        item.abstract_status = "full"
    if item.abstract and not item.abstract_source:
        item.abstract_source = source


def _node_text(node: ET.Element | None) -> str:
    if node is None:
        return ""
    return unescape(" ".join("".join(node.itertext()).split()))


def _pubmed_abstract(article: ET.Element) -> str:
    parts: list[str] = []
    for node in article.findall("./MedlineCitation/Article/Abstract/AbstractText"):
        text = _node_text(node)
        if not text:
            continue
        label = node.attrib.get("Label")
        parts.append(f"{label}: {text}" if label else text)
    return " ".join(parts)


def _pubmed_authors(article: ET.Element) -> list[str]:
    authors: list[str] = []
    for author in article.findall("./MedlineCitation/Article/AuthorList/Author"):
        collective = _node_text(author.find("CollectiveName"))
        if collective:
            authors.append(collective)
            continue
        last = _node_text(author.find("LastName"))
        fore = _node_text(author.find("ForeName"))
        initials = _node_text(author.find("Initials"))
        name = " ".join(part for part in [fore or initials, last] if part)
        if name:
            authors.append(name)
    return authors


def _pubmed_year(article: ET.Element) -> str:
    for path in (
        "./MedlineCitation/Article/Journal/JournalIssue/PubDate/Year",
        "./MedlineCitation/Article/ArticleDate/Year",
    ):
        year = _node_text(article.find(path))
        if year:
            return year
    medline_date = _node_text(article.find("./MedlineCitation/Article/Journal/JournalIssue/PubDate/MedlineDate"))
    return medline_date[:4] if medline_date else ""
