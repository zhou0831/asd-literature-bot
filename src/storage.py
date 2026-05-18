from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import LiteratureItem
from .text_utils import normalize_doi, normalize_identifier, normalize_title


SCHEMA = """
CREATE TABLE IF NOT EXISTS recommendations (
    candidate_id TEXT PRIMARY KEY,
    recommended_at TEXT NOT NULL,
    title TEXT NOT NULL,
    doi TEXT,
    pmid TEXT,
    pmcid TEXT,
    normalized_title TEXT NOT NULL,
    score REAL NOT NULL,
    module TEXT NOT NULL,
    payload TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS candidates (
    candidate_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    payload TEXT NOT NULL
);
"""


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.executescript(SCHEMA)

    def close(self) -> None:
        self.conn.close()

    def seen_keys(self) -> dict[str, set[str]]:
        keys = {"doi": set(), "pmid": set(), "pmcid": set(), "title": set()}
        rows = self.conn.execute(
            "SELECT doi, pmid, pmcid, normalized_title FROM recommendations"
        ).fetchall()
        for doi, pmid, pmcid, title in rows:
            if doi:
                keys["doi"].add(normalize_doi(doi))
            if pmid:
                keys["pmid"].add(normalize_identifier(pmid))
            if pmcid:
                keys["pmcid"].add(normalize_identifier(pmcid))
            if title:
                keys["title"].add(title)
        return keys

    def save_candidate(self, item: LiteratureItem) -> None:
        self.conn.execute(
            """
            INSERT OR REPLACE INTO candidates (candidate_id, created_at, payload)
            VALUES (?, ?, ?)
            """,
            (
                item.candidate_id,
                datetime.now(timezone.utc).isoformat(),
                json.dumps(item.to_dict(), ensure_ascii=False),
            ),
        )
        self.conn.commit()

    def get_candidate(self, candidate_id: str) -> LiteratureItem | None:
        row = self.conn.execute(
            "SELECT payload FROM candidates WHERE candidate_id = ?", (candidate_id,)
        ).fetchone()
        if not row:
            return None
        return LiteratureItem.from_dict(json.loads(row[0]))

    def save_recommendation(self, item: LiteratureItem) -> None:
        payload = json.dumps(item.to_dict(), ensure_ascii=False)
        self.conn.execute(
            """
            INSERT OR REPLACE INTO recommendations
            (candidate_id, recommended_at, title, doi, pmid, pmcid, normalized_title, score, module, payload)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                item.candidate_id,
                datetime.now(timezone.utc).isoformat(),
                item.title,
                normalize_doi(item.doi),
                normalize_identifier(item.pmid),
                normalize_identifier(item.pmcid),
                normalize_title(item.title),
                item.score,
                item.module,
                payload,
            ),
        )
        self.conn.commit()

    def recent_recommendations(self, limit: int = 50) -> list[LiteratureItem]:
        rows = self.conn.execute(
            """
            SELECT payload FROM recommendations
            ORDER BY recommended_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        return [LiteratureItem.from_dict(json.loads(row[0])) for row in rows]

