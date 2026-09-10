from app.action_engine import determine_next_step
from app.models import LeadInput, AIAnalysis, AIFieldSuggestion


def field(value):
    return AIFieldSuggestion(
        value=value,
        confidence=1.0,
        evidence=["demo"],
    )


def make_analysis():
    return AIAnalysis(
        fields={
            "object_type": field("фасад"),
            "material": field("дерево"),
            "dimensions": field("280 м²"),
            "location": field("Челябинск"),
            "condition": field("плохое состояние"),
            "desired_result": field("подготовка + покраска"),
            "start_timing": field("в течение месяца"),
            "budget": field("700–900 тысяч"),
            "photos_available": field(True),
        },
        intent="BUYING_SOON",
        object_priority="NORMAL",
        client_summary="Деревянный дом, требуется покраска.",
        red_flags=[],
    )


def make_lead(stage):
    return LeadInput(
        deal_id="6",
        title="Демонстрационная сделка",
        stage=stage,
    )


def check(stage, expected_action):
    result = determine_next_step(
        make_lead(stage),
        make_analysis(),
        [],
    )

    print(f"{stage:30} → {result['action']}")

    assert result["action"] == expected_action


def test_deal_lifecycle():

    print()
    print("=" * 70)
    print("ACTION ENGINE — DEAL LIFECYCLE")
    print("=" * 70)

    check(
        "NEW",
        "PREPARE_PRELIMINARY_ESTIMATION",
    )

    check(
        "ESTIMATION",
        "PREPARE_PRELIMINARY_KP",
    )

    check(
        "PRELIMINARY_KP",
        "GET_PRELIMINARY_KP_FEEDBACK",
    )

    check(
        "PRELIMINARY_KP_APPROVED",
        "SCHEDULE_MEASUREMENT",
    )

    check(
        "MEASUREMENT",
        "COMPLETE_MEASUREMENT",
    )

    check(
        "MEASUREMENT_COMPLETED",
        "PREPARE_FINAL_KP",
    )

    check(
        "FINAL_KP",
        "GET_FINAL_KP_FEEDBACK",
    )

    check(
        "FINAL_KP_APPROVED",
        "PREPARE_CONTRACT",
    )

    check(
        "CONTRACT_SIGNED",
        "CONTROL_PREPAYMENT",
    )

    print()
    print("=" * 70)
    print("ALL LIFECYCLE TESTS PASSED")
    print("=" * 70)


if __name__ == "__main__":
    test_deal_lifecycle()