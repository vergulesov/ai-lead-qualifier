from app.models import (
    AIAnalysis,
    AIFieldSuggestion,
    QualificationState,
    LeadInput,
)
from app.pipeline import build_result


def test_next_step():

    lead = LeadInput(
        deal_id="6",
        title="Тестовая сделка",
        stage="QUALIFICATION",
    )

    analysis = AIAnalysis(
        fields={
            "object_type": AIFieldSuggestion(
                value="фасад",
                confidence=1.0,
                evidence=["Дом в Челябинске"],
            ),
            "material": AIFieldSuggestion(
                value="дерево",
                confidence=1.0,
                evidence=["Дом деревянный"],
            ),
            "condition": AIFieldSuggestion(
                value="плохое состояние",
                confidence=1.0,
                evidence=["Покрытие выгорело"],
            ),
            "dimensions": AIFieldSuggestion(
                value="280 м²",
                confidence=1.0,
                evidence=["Площадь фасада 280 м²"],
            ),
            "location": AIFieldSuggestion(
                value="Челябинск",
                confidence=1.0,
                evidence=["Дом в Челябинске"],
            ),
            "project_available": AIFieldSuggestion(
                value=None,
                confidence=0.0,
            ),
            "photos_available": AIFieldSuggestion(
                value=True,
                confidence=1.0,
                evidence=["Фото отправлю сегодня"],
            ),
            "desired_result": AIFieldSuggestion(
                value="подготовка поверхности и полная покраска дома",
                confidence=1.0,
            ),
            "additional_work": AIFieldSuggestion(
                value=None,
                confidence=0.0,
            ),
            "start_timing": AIFieldSuggestion(
                value="в течение ближайшего месяца",
                confidence=1.0,
            ),
            "budget": AIFieldSuggestion(
                value="700–900 тысяч рублей",
                confidence=1.0,
            ),
            "previous_experience": AIFieldSuggestion(
                value=None,
                confidence=0.0,
            ),
        },
        intent="BUYING_SOON",
        object_priority="NORMAL",
        client_summary="",
        red_flags=[],
        next_step=None,
        next_contact_date=None,
    )

    # Минимальный профиль для теста
    class TestProfile:
        required_fields = [
            "object_type",
            "material",
            "condition",
            "dimensions",
            "location",
            "project_available",
            "photos_available",
            "desired_result",
            "additional_work",
            "start_timing",
            "budget",
            "previous_experience",
        ]

        score_rules = []

        quality = {
            "medium": 50,
            "high": 75,
        }

    profile = TestProfile()

    result = build_result(
        lead,
        profile,
        analysis,
        QualificationState(),
    )

    print("\nNEXT STEP:")
    print(result.next_step)

    print("\nSCORE:")
    print(result.score)

    print("\nINTENT SCORE:")
    print(result.intent_score)

    print("\nMISSING DATA:")
    print(result.missing_data)

    assert result.next_step is not None
    assert isinstance(result.next_step, str)

    print("\nTEST PASSED")


if __name__ == "__main__":
    test_next_step()