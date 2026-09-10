from app.action_engine import determine_next_step
from app.models import LeadInput, AIAnalysis, AIFieldSuggestion


def make_analysis(
    photos=False,
    project=False,
    budget="700–900 тысяч рублей",
    red_flags=None,
):
    return AIAnalysis(
        fields={
            "object_type": AIFieldSuggestion(
                value="фасад",
                confidence=1.0,
                evidence=[],
            ),
            "material": AIFieldSuggestion(
                value="дерево",
                confidence=1.0,
                evidence=[],
            ),
            "condition": AIFieldSuggestion(
                value="плохое состояние",
                confidence=1.0,
                evidence=[],
            ),
            "dimensions": AIFieldSuggestion(
                value="280 м²",
                confidence=1.0,
                evidence=[],
            ),
            "location": AIFieldSuggestion(
                value="Челябинск",
                confidence=1.0,
                evidence=[],
            ),
            "project_available": AIFieldSuggestion(
                value=project,
                confidence=1.0 if project else 0.0,
                evidence=[],
            ),
            "photos_available": AIFieldSuggestion(
                value=photos,
                confidence=1.0 if photos else 0.0,
                evidence=[],
            ),
            "desired_result": AIFieldSuggestion(
                value="подготовка поверхности и полная покраска дома",
                confidence=1.0,
                evidence=[],
            ),
            "additional_work": AIFieldSuggestion(
                value=None,
                confidence=0.0,
                evidence=[],
            ),
            "start_timing": AIFieldSuggestion(
                value="в течение ближайшего месяца",
                confidence=1.0,
                evidence=[],
            ),
            "budget": AIFieldSuggestion(
                value=budget,
                confidence=1.0 if budget else 0.0,
                evidence=[],
            ),
            "previous_experience": AIFieldSuggestion(
                value=None,
                confidence=0.0,
                evidence=[],
            ),
        },
        intent="BUYING_SOON",
        object_priority="NORMAL",
        client_summary="",
        red_flags=red_flags or [],
        next_step=None,
        next_contact_date=None,
    )


def make_lead(stage):
    return LeadInput(
        deal_id="6",
        title="Тестовая сделка",
        stage=stage,
    )


def test_photos_are_enough():

    result = determine_next_step(
        make_lead("QUALIFICATION"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "PREPARE_PRELIMINARY_ESTIMATION"

    print("✓ Фото достаточно")


def test_project_is_enough():

    result = determine_next_step(
        make_lead("QUALIFICATION"),
        make_analysis(project=True),
        [],
    )

    assert result["action"] == "PREPARE_PRELIMINARY_ESTIMATION"

    print("✓ Проекта достаточно")


def test_no_photos_and_no_project():

    result = determine_next_step(
        make_lead("QUALIFICATION"),
        make_analysis(),
        [],
    )

    assert result["action"] == "REQUEST_OBJECT_MATERIALS"

    print("✓ Без фото и проекта запрашиваем материалы")


def test_preliminary_estimation():

    result = determine_next_step(
        make_lead("ESTIMATION"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "PREPARE_PRELIMINARY_KP"

    print("✓ После оценки → предварительное КП")


def test_preliminary_kp_feedback():

    result = determine_next_step(
        make_lead("PRELIMINARY_KP"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "GET_PRELIMINARY_KP_FEEDBACK"

    print("✓ После предварительного КП → обратная связь")


def test_measurement():

    result = determine_next_step(
        make_lead("PRELIMINARY_KP_APPROVED"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "SCHEDULE_MEASUREMENT"

    print("✓ После одобрения КП → замер")


def test_final_kp():

    result = determine_next_step(
        make_lead("MEASUREMENT_COMPLETED"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "PREPARE_FINAL_KP"

    print("✓ После замера → финальное КП")


def test_contract():

    result = determine_next_step(
        make_lead("FINAL_KP_APPROVED"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "PREPARE_CONTRACT"

    print("✓ После финального КП → договор")


def test_prepayment():

    result = determine_next_step(
        make_lead("CONTRACT_SIGNED"),
        make_analysis(photos=True),
        [],
    )

    assert result["action"] == "CONTROL_PREPAYMENT"

    print("✓ После договора → предоплата")


def test_red_flags():

    result = determine_next_step(
        make_lead("QUALIFICATION"),
        make_analysis(
            photos=True,
            red_flags=["Клиент не подтверждает бюджет"],
        ),
        [],
    )

    assert result["action"] == "REVIEW_RED_FLAGS"

    print("✓ Red Flags имеют приоритет")


def main():
    print("\n" + "=" * 60)
    print("ACTION ENGINE TESTS")
    print("=" * 60 + "\n")

    test_photos_are_enough()
    test_project_is_enough()
    test_no_photos_and_no_project()
    test_preliminary_estimation()
    test_preliminary_kp_feedback()
    test_measurement()
    test_final_kp()
    test_contract()
    test_prepayment()
    test_red_flags()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()