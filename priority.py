"""Rule-based, explainable priority scoring.

P = 0.4*Sc + 0.3*Su + 0.2*Sa + 0.1*St, each component scaled to 0-1.
"""
import config
from preprocess import contains_keyword


def urgency_score(text: str) -> float:
    if contains_keyword(text, config.URGENCY_CRITICAL):
        return 1.0
    if contains_keyword(text, config.URGENCY_HIGH):
        return 0.6
    return 0.0


def area_score(text: str, area: str = "") -> float:
    combined = f"{text or ''} {area or ''}"
    if contains_keyword(combined, config.SENSITIVE_LOCATIONS):
        return 1.0
    if contains_keyword(combined, config.WIDE_AREA):
        return 0.6
    return 0.0


def ageing_score(days_open: float) -> float:
    return max(0.0, min(days_open / config.AGEING_FULL_DAYS, 1.0))


def label_for(score: float) -> str:
    for label, lower in config.PRIORITY_THRESHOLDS:
        if score >= lower:
            return label
    return "Low"


def score_complaint(text: str, category: str, area: str = "", days_open: float = 0.0) -> dict:
    """Return the score, label and every component so the result can be explained."""
    parts = {
        "severity": config.CATEGORY_SEVERITY.get(category, 0.5),
        "urgency": urgency_score(text),
        "area": area_score(text, area),
        "ageing": ageing_score(days_open),
    }
    score = round(sum(config.WEIGHTS[k] * v for k, v in parts.items()), 3)
    return {"score": score, "label": label_for(score), "components": parts}
