from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class LiteratureItem:
    title: str
    authors: list[str] = field(default_factory=list)
    year: str = ""
    venue: str = ""
    doi: str = ""
    url: str = ""
    abstract: str = ""
    source: str = ""
    pmid: str = ""
    pmcid: str = ""
    candidate_id: str = ""
    score: float = 0.0
    reason: str = ""
    module: str = "方法学"

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "authors": self.authors,
            "year": self.year,
            "venue": self.venue,
            "doi": self.doi,
            "url": self.url,
            "abstract": self.abstract,
            "source": self.source,
            "pmid": self.pmid,
            "pmcid": self.pmcid,
            "candidate_id": self.candidate_id,
            "score": self.score,
            "reason": self.reason,
            "module": self.module,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "LiteratureItem":
        return cls(
            title=data.get("title", ""),
            authors=list(data.get("authors") or []),
            year=str(data.get("year") or ""),
            venue=data.get("venue", ""),
            doi=data.get("doi", ""),
            url=data.get("url", ""),
            abstract=data.get("abstract", ""),
            source=data.get("source", ""),
            pmid=data.get("pmid", ""),
            pmcid=data.get("pmcid", ""),
            candidate_id=data.get("candidate_id", ""),
            score=float(data.get("score") or 0),
            reason=data.get("reason", ""),
            module=data.get("module", "方法学"),
        )

