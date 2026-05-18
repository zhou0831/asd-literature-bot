from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher


def normalize_doi(value: str | None) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"^https?://(dx\.)?doi\.org/", "", value)
    value = re.sub(r"^doi:\s*", "", value)
    return value.strip().rstrip(".")


def normalize_identifier(value: str | None) -> str:
    return re.sub(r"\s+", "", (value or "").strip().lower())


def normalize_title(value: str | None) -> str:
    text = unicodedata.normalize("NFKD", value or "").lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def title_similarity(left: str, right: str) -> float:
    a = normalize_title(left)
    b = normalize_title(right)
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def short_hash(text: str) -> str:
    import hashlib

    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:10]

