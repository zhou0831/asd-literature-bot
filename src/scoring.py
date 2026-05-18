from __future__ import annotations

from .models import LiteratureItem


WEIGHTS = {
    "dynamic": 4.0,
    "video": 3.0,
    "social intention": 5.0,
    "social cognition": 4.0,
    "theory of mind": 4.0,
    "mentalizing": 4.0,
    "action prediction": 4.0,
    "goal directed": 4.0,
    "biological motion": 3.5,
    "joint attention": 3.0,
    "gaze cueing": 3.0,
    "social attribution": 4.0,
    "autism": 3.0,
    "autistic": 3.0,
    "children": 2.0,
    "child": 1.5,
    "eeg": 3.0,
    "eye tracking": 3.0,
    "eye-tracking": 3.0,
    "low-level visual": 2.0,
}


MODULE_TERMS = {
    "A": ["gaze", "cue", "joint attention", "agent", "biological motion"],
    "B": ["action", "goal", "prediction", "intention", "movement"],
    "C": ["theory of mind", "mentalizing", "mind", "implicit", "social attribution"],
    "方法学": ["eeg", "eye tracking", "video", "stimuli", "low-level visual"],
    "综述": ["review", "meta-analysis", "model"],
}


def score_items(items: list[LiteratureItem]) -> list[LiteratureItem]:
    for item in items:
        score_item(item)
    return sorted(items, key=lambda row: row.score, reverse=True)


def score_item(item: LiteratureItem) -> LiteratureItem:
    haystack = f"{item.title} {item.abstract}".lower()
    score = 0.0
    matched: list[str] = []
    for term, weight in WEIGHTS.items():
        if term in haystack:
            score += weight
            matched.append(term)
    if item.doi:
        score += 0.5
    if item.abstract:
        score += 1.0
    item.score = round(score, 2)
    item.module = choose_module(haystack)
    item.reason = "；".join(matched[:8]) if matched else "主题词匹配较少，需要人工复核"
    return item


def choose_module(text: str) -> str:
    scores: dict[str, int] = {}
    for module, terms in MODULE_TERMS.items():
        scores[module] = sum(1 for term in terms if term in text)
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "方法学"

