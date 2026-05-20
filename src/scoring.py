from __future__ import annotations

import re

from .models import LiteratureItem
from .research_profile import load_research_profile


CORE_TERMS = {
    "dynamic social": 16,
    "social intention": 18,
    "social attribution": 18,
    "frith": 14,
    "happe": 14,
    "moving shapes": 18,
    "animated shapes": 16,
    "theory of mind": 16,
    "mentalizing": 15,
    "false belief": 20,
    "false-belief": 20,
    "anticipatory looking": 14,
    "action prediction": 16,
    "goal directed": 14,
    "goal-directed": 14,
    "joint attention": 22,
    "gaze cueing": 14,
    "gaze following": 14,
    "biological motion": 12,
    "social cue": 10,
    "naturalistic": 10,
    "ecological": 6,
    "interactive": 4,
    "video": 8,
    "dynamic stimuli": 12,
    "eeg": 12,
    "erp": 8,
    "eye tracking": 8,
    "eye-tracking": 8,
}

MODULE_TERMS = {
    "A": ["joint attention", "gaze cueing", "gaze following", "agent", "biological motion", "social cue"],
    "B": ["action prediction", "goal directed", "goal-directed", "intention", "movement", "gesture"],
    "C": ["theory of mind", "mentalizing", "false belief", "false-belief", "social attribution", "frith", "happe"],
    "方法学": ["eeg", "erp", "eye tracking", "eye-tracking", "video", "dynamic stimuli", "naturalistic"],
    "综述": ["review", "meta-analysis", "scoping review", "model"],
}

PENALTY_PATTERNS = {
    "generic_ai_diagnosis": [
        r"\bai\b.*diagnos",
        r"artificial intelligence.*diagnos",
        r"machine learning.*diagnos",
        r"classification.*diagnos",
    ],
    "facial_recognition_only": [
        r"facial recognition",
        r"face recognition",
        r"facial emotion recognition",
        r"static facial",
    ],
    "broad_visual_attention_diagnosis": [
        r"visual attention.*diagnos",
        r"diagnos.*visual attention",
    ],
    "generic_classification": [
        r"machine learning classification",
        r"\bclassification\b",
    ],
    "non_core_biomedical": [
        r"genetic",
        r"microbiome",
        r"medication",
        r"structural mri",
    ],
    "intervention_only": [
        r"intervention",
        r"therapy",
        r"treatment trial",
    ],
}

EXCLUSION_REASONS = {
    "generic_ai_diagnosis",
    "facial_recognition_only",
    "broad_visual_attention_diagnosis",
    "generic_classification",
    "non_core_biomedical",
    "intervention_only",
}

_PROFILE = load_research_profile()
_THRESHOLDS = _PROFILE.get("thresholds", {})
MIN_TOPIC_FIT = float(_THRESHOLDS.get("min_topic_fit_score", 50))
MIN_RECOMMENDATION_SCORE = float(_THRESHOLDS.get("min_recommendation_score", 55))


def score_items(items: list[LiteratureItem]) -> list[LiteratureItem]:
    for item in items:
        score_item(item)
    return sorted(items, key=lambda row: row.recommendation_score, reverse=True)


def score_item(item: LiteratureItem) -> LiteratureItem:
    text = _normalize(f"{item.title} {item.abstract}")
    matched: list[str] = []
    score = 0.0

    for term, weight in CORE_TERMS.items():
        if _contains_term(text, term):
            matched.append(term)
            score += weight

    # Avoid child/children duplicate inflation; child sample matters, but it is not a topic by itself.
    if re.search(r"\b(children|child|pediatric|paediatric)\b", text):
        matched.append("children")
        score += 5
    if re.search(r"\b(autism|autistic|asd)\b", text):
        matched.append("autism/asd")
        score += 7

    if _contains_any(text, ["eye tracking", "eye-tracking"]):
        if _has_core_social_context(text):
            score += 6
            matched.append("eye tracking with social-cognitive context")
        else:
            matched.append("eye tracking without core social-cognitive context")

    if item.doi:
        score += 1
    if item.abstract:
        score += 2

    penalties = _penalty_reasons(text)
    penalty_value = _penalty_value(penalties, text)
    topic_fit = max(0.0, min(100.0, score - penalty_value))
    recommendation_score = max(0.0, min(100.0, topic_fit + _module_bonus(text)))
    strong_exclusion = _is_strong_exclusion(penalties, text)

    if strong_exclusion:
        recommendation_score = min(recommendation_score, 35.0)
        topic_fit = min(topic_fit, 35.0)

    item.topic_fit_score = round(topic_fit, 2)
    item.recommendation_score = round(recommendation_score, 2)
    item.score = item.recommendation_score
    item.module = choose_module(text)
    item.penalty_reasons = penalties
    item.strong_exclusion = strong_exclusion
    item.low_confidence = not is_recommendable(item)
    item.reason = "；".join(matched[:10]) if matched else "主题词匹配较少，需要人工复核"
    if penalties:
        item.reason = f"{item.reason}；降权：{'，'.join(penalties)}"
    return item


def is_recommendable(item: LiteratureItem) -> bool:
    return (
        item.topic_fit_score >= MIN_TOPIC_FIT
        and item.recommendation_score >= MIN_RECOMMENDATION_SCORE
        and not item.strong_exclusion
    )


def choose_module(text: str) -> str:
    scores: dict[str, int] = {}
    for module, terms in MODULE_TERMS.items():
        scores[module] = sum(1 for term in terms if _contains_term(text, term))
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "方法学"


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").lower()).strip()


def _contains_term(text: str, term: str) -> bool:
    pattern = r"(?<![a-z0-9])" + re.escape(term.lower()).replace(r"\ ", r"\s+") + r"(?![a-z0-9])"
    return re.search(pattern, text) is not None


def _contains_any(text: str, terms: list[str]) -> bool:
    return any(_contains_term(text, term) for term in terms)


def _has_core_social_context(text: str) -> bool:
    return _contains_any(
        text,
        [
            "social cognition",
            "social intention",
            "joint attention",
            "action prediction",
            "theory of mind",
            "mentalizing",
            "social attribution",
            "dynamic stimuli",
            "naturalistic",
            "video",
            "gaze cueing",
            "false belief",
        ],
    )


def _penalty_reasons(text: str) -> list[str]:
    reasons: list[str] = []
    for reason, patterns in PENALTY_PATTERNS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            reasons.append(reason)
    if "scoping review" in text and any(reason in reasons for reason in ["generic_ai_diagnosis", "facial_recognition_only", "broad_visual_attention_diagnosis"]):
        reasons.append("diagnostic_scoping_review")
    return reasons


def _penalty_value(reasons: list[str], text: str) -> float:
    value = 0.0
    for reason in reasons:
        value += {
            "generic_ai_diagnosis": 24,
            "facial_recognition_only": 18,
            "broad_visual_attention_diagnosis": 18,
            "generic_classification": 14,
            "non_core_biomedical": 30,
            "intervention_only": 18,
            "diagnostic_scoping_review": 18,
        }.get(reason, 10)
    if "review" in text and not _has_core_social_context(text):
        value += 10
    return value


def _module_bonus(text: str) -> float:
    bonus = 0.0
    if _contains_any(text, ["social attribution", "false belief", "theory of mind", "mentalizing"]):
        bonus += 12
    if _contains_any(text, ["joint attention", "gaze cueing", "gaze following"]):
        bonus += 8
    if _contains_any(text, ["dynamic", "video", "moving shapes", "animated shapes", "naturalistic"]):
        bonus += 8
    if _contains_any(text, ["eeg", "erp"]) and _has_core_social_context(text):
        bonus += 6
    return bonus


def _is_strong_exclusion(reasons: list[str], text: str) -> bool:
    if not any(reason in EXCLUSION_REASONS or reason == "diagnostic_scoping_review" for reason in reasons):
        return False
    return not _contains_any(
        text,
        [
            "dynamic social",
            "social intention",
            "joint attention",
            "gaze cueing",
            "gaze following",
            "theory of mind",
            "mentalizing",
            "social attribution",
            "false belief",
            "action prediction",
            "moving shapes",
            "animated shapes",
            "naturalistic video",
            "eeg",
        ],
    )
