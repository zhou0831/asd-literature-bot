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
    topic_fit_score: float = 0.0
    recommendation_score: float = 0.0
    reason: str = ""
    module: str = "方法学"
    penalty_reasons: list[str] = field(default_factory=list)
    strong_exclusion: bool = False
    low_confidence: bool = False
    recommendation_tier: str = "core"

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
            "topic_fit_score": self.topic_fit_score,
            "recommendation_score": self.recommendation_score,
            "reason": self.reason,
            "module": self.module,
            "penalty_reasons": self.penalty_reasons,
            "strong_exclusion": self.strong_exclusion,
            "low_confidence": self.low_confidence,
            "recommendation_tier": self.recommendation_tier,
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
            topic_fit_score=float(data.get("topic_fit_score") or data.get("score") or 0),
            recommendation_score=float(data.get("recommendation_score") or data.get("score") or 0),
            reason=data.get("reason", ""),
            module=data.get("module", "方法学"),
            penalty_reasons=list(data.get("penalty_reasons") or []),
            strong_exclusion=bool(data.get("strong_exclusion") or False),
            low_confidence=bool(data.get("low_confidence") or False),
            recommendation_tier=data.get("recommendation_tier", "core"),
        )
