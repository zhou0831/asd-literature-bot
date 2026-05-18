from __future__ import annotations

from typing import Any

import requests

from .config import env
from .models import LiteratureItem
from .text_utils import normalize_doi, normalize_identifier, normalize_title


class ZoteroClient:
    def __init__(self) -> None:
        self.api_key = env("ZOTERO_API_KEY")
        self.user_id = env("ZOTERO_USER_ID")
        self.library_type = env("ZOTERO_LIBRARY_TYPE", "user")
        self.collection_key = env("ZOTERO_COLLECTION_KEY", "Z7SCP3DE")
        self.base_url = f"https://api.zotero.org/{self.library_type}s/{self.user_id}"

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.user_id and self.collection_key)

    def existing_items(self) -> list[dict[str, str]]:
        if not self.configured:
            return []
        items: list[dict[str, str]] = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/collections/{self.collection_key}/items",
                params={"format": "json", "limit": 100, "start": start},
                headers={"Zotero-API-Key": self.api_key},
                timeout=25,
            )
            response.raise_for_status()
            batch = response.json()
            if not batch:
                break
            for record in batch:
                data = record.get("data", {})
                items.append(
                    {
                        "title": normalize_title(data.get("title", "")),
                        "doi": normalize_doi(data.get("DOI", "")),
                        "pmid": normalize_identifier(data.get("extra", "")),
                    }
                )
            start += len(batch)
        return items

    def import_item(self, item: LiteratureItem, tag: str = "GPT推荐") -> dict[str, Any]:
        if not self.configured:
            raise RuntimeError("Zotero is not configured. Set ZOTERO_API_KEY, ZOTERO_USER_ID, and ZOTERO_COLLECTION_KEY.")
        payload = [
            {
                "itemType": "journalArticle",
                "title": item.title,
                "creators": [{"creatorType": "author", "name": name} for name in item.authors[:20]],
                "date": item.year,
                "publicationTitle": item.venue,
                "DOI": item.doi,
                "url": item.url,
                "abstractNote": item.abstract,
                "collections": [self.collection_key],
                "tags": [{"tag": tag}],
                "extra": "\n".join(part for part in [f"PMID: {item.pmid}" if item.pmid else "", f"PMCID: {item.pmcid}" if item.pmcid else ""] if part),
            }
        ]
        response = requests.post(
            f"{self.base_url}/items",
            json=payload,
            headers={"Zotero-API-Key": self.api_key, "Content-Type": "application/json"},
            timeout=25,
        )
        response.raise_for_status()
        return response.json()

