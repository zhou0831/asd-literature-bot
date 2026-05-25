from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .models import LiteratureItem


@dataclass(frozen=True)
class SearchDiagnostics:
    raw_candidate_count: int = 0
    deduped_candidate_count: int = 0
    abstract_full_count: int = 0
    abstract_missing_count: int = 0
    source_counts: Counter = field(default_factory=Counter)
    module_counts: Counter = field(default_factory=Counter)
    tier_counts: Counter = field(default_factory=Counter)
    strong_exclusion_count: int = 0
    excluded_preview: list[LiteratureItem] = field(default_factory=list)
    high_score_not_selected_preview: list[LiteratureItem] = field(default_factory=list)


def build_search_diagnostics(
    raw_candidates: list[LiteratureItem],
    deduped_candidates: list[LiteratureItem],
    ranked_candidates: list[LiteratureItem],
    selected: LiteratureItem | None = None,
) -> SearchDiagnostics:
    selected_key = (selected.candidate_id, selected.title) if selected else None
    return SearchDiagnostics(
        raw_candidate_count=len(raw_candidates),
        deduped_candidate_count=len(deduped_candidates),
        abstract_full_count=sum(1 for item in deduped_candidates if item.abstract.strip()),
        abstract_missing_count=sum(1 for item in deduped_candidates if not item.abstract.strip()),
        source_counts=Counter((item.source or "Unknown") for item in raw_candidates),
        module_counts=Counter((item.module or "方法学") for item in ranked_candidates),
        tier_counts=Counter((item.recommendation_tier or "background") for item in ranked_candidates),
        strong_exclusion_count=sum(1 for item in ranked_candidates if item.strong_exclusion),
        excluded_preview=[item for item in ranked_candidates if item.strong_exclusion][:5],
        high_score_not_selected_preview=[
            item
            for item in ranked_candidates
            if selected_key is None or (item.candidate_id, item.title) != selected_key
        ][:5],
    )
