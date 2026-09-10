from app.models import AIAnalysis, AIFieldSuggestion
from app.profile import load_profile
from app.scorer import calculate_score
from pathlib import Path


def test_score_is_calculated_from_rules():
    profile = load_profile(Path("profiles"), "best_paints")
    analysis = AIAnalysis(
        fields={
            "object_type": AIFieldSuggestion(value="house", confidence=1, evidence=[]),
            "material": AIFieldSuggestion(value="glued timber", confidence=1, evidence=[]),
            "location": AIFieldSuggestion(value="Istra", confidence=1, evidence=[]),
            "dimensions": AIFieldSuggestion(value="10x12", confidence=1, evidence=[]),
            "project_available": AIFieldSuggestion(value=True, confidence=1, evidence=[]),
            "photos_available": AIFieldSuggestion(value=True, confidence=1, evidence=[]),
            "desired_result": AIFieldSuggestion(value="visible wood texture", confidence=1, evidence=[]),
            "start_timing": AIFieldSuggestion(value="November", confidence=1, evidence=[]),
            "budget": AIFieldSuggestion(value=500000, confidence=1, evidence=[]),
            "previous_experience": AIFieldSuggestion(value="none", confidence=1, evidence=[]),
        },
        intent="BUYING_SOON",
        object_priority="HIGH",
    )
    assert calculate_score(analysis, profile) == 100
