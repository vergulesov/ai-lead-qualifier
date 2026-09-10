from typing import Any

from .models import AIAnalysis
from .profile import Profile


# AI currently returns a categorical intent.
# We convert it to a deterministic 0-100 value for the CRM UI.
INTENT_SCORES = {
    "HIGH_INTENT": 90,
    "BUYING_SOON": 80,
    "CONSIDERING": 60,
    "LOW_INTENT": 25,
    "UNCERTAIN": 40,
    "unknown": 0,
}


def _value(analysis: AIAnalysis, field: str) -> Any:
    item = analysis.fields.get(field)
    return item.value if item else None


def _known(analysis: AIAnalysis, field: str) -> bool:
    item = analysis.fields.get(field)
    return (
        item is not None
        and item.value not in (None, "", [], {})
    )


def condition_matches(
    condition: dict[str, Any],
    analysis: AIAnalysis,
) -> bool:
    field = condition.get("field")
    operator = condition.get("operator", "exists")
    value = _value(analysis, field)

    if operator == "exists":
        return _known(analysis, field)

    if operator == "equals":
        return _known(analysis, field) and value == condition.get("value")

    if operator == "not_equals":
        return _known(analysis, field) and value != condition.get("value")

    if operator == "in":
        return (
            _known(analysis, field)
            and value in condition.get("values", [])
        )

    if operator == "contains":
        needle = str(condition.get("value", "")).lower()
        return (
            _known(analysis, field)
            and needle in str(value).lower()
        )

    raise ValueError(f"Unknown score operator: {operator}")


def calculate_score(
    analysis: AIAnalysis,
    profile: Profile,
) -> int:
    """
    Deterministic business score from profile rules.

    Score consists of:
    1. Base score from field rules.
    2. Intent bonus.
    3. Object priority bonus.

    Final value is limited to 0-100.
    """

    score = 0

    # =========================================================
    # 1. BASE SCORE
    # =========================================================

    for rule in profile.score_rules:
        if condition_matches(rule["condition"], analysis):
            score += int(rule["points"])

    # =========================================================
    # 2. INTENT BONUS
    # =========================================================

    intent = (analysis.intent or "unknown").strip().upper()

    intent_bonus = getattr(profile, "intent_bonus", {}).get(intent, 0)
    score += int(intent_bonus)

    # =========================================================
    # 3. OBJECT PRIORITY BONUS
    # =========================================================

    priority = (analysis.object_priority or "NORMAL").strip().upper()

    priority_bonus = getattr(profile, "object_priority_bonus", {}).get(priority, 0)
    score += int(priority_bonus)

    # =========================================================
    # 4. LIMIT
    # =========================================================

    return max(0, min(100, score))


def calculate_intent_score(analysis: AIAnalysis) -> int:
    """Convert the AI intent category to a 0-100 UI score."""
    intent = (analysis.intent or "unknown").strip().upper()
    return INTENT_SCORES.get(intent, INTENT_SCORES["unknown"])


def calculate_final_score(
    ai_score: int,
    manager_score: int | None,
) -> int:
    """
    Final commercial score.

    Without manager override: AI score.
    With manager override: AI 70% + manager 30%.
    """
    if manager_score is None:
        return max(0, min(100, ai_score))

    final_score = ai_score * 0.7 + manager_score * 0.3
    return max(0, min(100, round(final_score)))


def _object_materials_available(analysis: AIAnalysis) -> bool:
    """
    Photos and project are interchangeable evidence.

    We do NOT require both:
      photos = enough
      project = enough
      both = also enough
      neither = missing object materials
    """
    return (
        _value(analysis, "photos_available") is True
        or _value(analysis, "project_available") is True
    )


def missing_data(
    analysis: AIAnalysis,
    profile: Profile,
) -> list[str]:
    """
    Required data that is genuinely unknown.

    photos/project are treated as one logical requirement:
    OBJECT_MATERIALS.
    """
    result: list[str] = []

    for field in profile.required_fields:
        if field in {"photos_available", "project_available"}:
            continue

        if not _known(analysis, field):
            result.append(field)

    if not _object_materials_available(analysis):
        result.append("object_materials")

    return result


def _has_meaningful_data(analysis: AIAnalysis) -> bool:
    meaningful_fields = (
        "object_type",
        "dimensions",
        "location",
        "condition",
        "desired_result",
        "start_timing",
        "budget",
    )
    return any(_known(analysis, field) for field in meaningful_fields)


def _has_serious_red_flags(analysis: AIAnalysis) -> bool:
    return len(analysis.red_flags) >= 2


def quality(
    score: int,
    profile: Profile,
    analysis: AIAnalysis,
) -> str:
    """
    Quality describes commercial usability, not just score.
    """
    if not _has_meaningful_data(analysis):
        return "insufficient_data"

    if score < profile.quality["medium"]:
        return "low"

    if _has_serious_red_flags(analysis):
        return "low"

    if analysis.red_flags:
        return "medium"

    if score >= profile.quality["high"]:
        return "high"

    return "medium"
