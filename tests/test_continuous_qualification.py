from datetime import datetime

from app.models import (
    AIAnalysis,
    AIFieldSuggestion,
    Client,
    LeadInput,
    Message,
    QualificationState,
)
from app.pipeline import build_result
from app.profile import load_profile
from app.config import PROFILES_DIR


DEAL_ID = "DEMO-001"


# ============================================================
# HELPERS
# ============================================================

def make_field(value, evidence):
    return AIFieldSuggestion(
        value=value,
        confidence=1.0,
        evidence=[evidence],
    )


def make_analysis(
    fields,
    summary,
    intent="BUYING_SOON",
    red_flags=None,
):
    return AIAnalysis(
        fields={
            name: make_field(value, evidence)
            for name, (value, evidence) in fields.items()
        },
        intent=intent,
        object_priority="NORMAL",
        client_summary=summary,
        red_flags=red_flags or [],
    )


def make_message(number, role, text):
    return Message(
        id=f"msg-{number}",
        timestamp=datetime.now(),
        role=role,
        text=text,
        source="demo",
    )


def make_lead(
    stage="NEW",
    messages=None,
    calls=None,
):
    return LeadInput(
        deal_id=DEAL_ID,
        title="Дом в Челябинске — демонстрационная сделка",
        stage=stage,
        client=Client(
            name="Иван Петров",
        ),
        crm_fields={},
        messages=messages or [],
        calls=calls or [],
    )


def update_state(result, previous_state):
    return QualificationState(
        fields=result.fields,
        ai_score=result.score,
        manager_score=previous_state.manager_score,
        manager_reason=previous_state.manager_reason,
        alerts=result.alerts,
    )


def show_result(event, result):
    print()
    print("=" * 70)
    print(event)
    print("=" * 70)

    print("NEXT STEP:")
    print(result.next_step)

    print()
    print("SCORE:")
    print(result.score)

    print()
    print("INTENT:")
    print(result.intent)

    print()
    print("MISSING DATA:")
    print(result.missing_data)

    print()
    print("KNOWN FIELDS:")

    for name, item in result.fields.items():
        print(f"  {name}: {item.value}")


# ============================================================
# TEST
# ============================================================

def test_continuous_qualification():

    profile = load_profile(
        PROFILES_DIR,
        "best_paints",
    )

    state = QualificationState()

    # ========================================================
    # EVENT 1
    # ПЕРВИЧНЫЙ ЗВОНОК
    # ========================================================

    lead = make_lead(
        stage="NEW",
        messages=[
            make_message(
                1,
                "client",
                (
                    "Дом деревянный, Челябинск. "
                    "Фасад примерно 280 квадратов. "
                    "Покрытие сильно выгорело, местами отслаивается. "
                    "Хотим подготовить поверхность и покрасить. "
                    "Начать хотим в течение месяца. "
                    "По бюджету ориентируемся на 700–900 тысяч."
                ),
            )
        ],
    )

    current_analysis = make_analysis(
        {
            "object_type": (
                "фасад",
                "Из разговора с клиентом",
            ),
            "material": (
                "дерево",
                "Из разговора с клиентом",
            ),
            "dimensions": (
                "280 м²",
                "Клиент назвал площадь",
            ),
            "location": (
                "Челябинск",
                "Клиент назвал город",
            ),
            "condition": (
                "плохое состояние",
                "Клиент описал отслаивание покрытия",
            ),
            "desired_result": (
                "подготовка поверхности + покраска",
                "Клиент описал желаемый результат",
            ),
            "start_timing": (
                "в течение месяца",
                "Клиент назвал срок",
            ),
            "budget": (
                "700–900 тысяч рублей",
                "Клиент назвал ориентировочный бюджет",
            ),
        },
        "Первичный анализ клиента.",
    )

    result = build_result(
        lead,
        profile,
        current_analysis,
        state,
    )

    state = update_state(
        result,
        state,
    )

    show_result(
        "EVENT 1 — ПЕРВИЧНЫЙ ЗВОНОК",
        result,
    )

    # На первом этапе фото/проект ещё отсутствуют.
    assert result.next_step == (
        "Запросить фото объекта или проект."
    )

    assert "object_materials" in result.missing_data

    # Проверяем, что первичные данные сохранились.
    assert result.fields["material"].value == "дерево"
    assert result.fields["dimensions"].value == "280 м²"
    assert result.fields["location"].value == "Челябинск"
    assert result.fields["budget"].value == "700–900 тысяч рублей"


    # ========================================================
    # EVENT 2
    # КЛИЕНТ ПРИСЛАЛ ФОТО
    # ========================================================

    lead.messages.append(
        make_message(
            2,
            "client",
            (
                "Василий, отправляю фотографии дома. "
                "На фасаде деревянная окрашенная обшивка, "
                "старое покрытие местами отслаивается."
            ),
        )
    )

    current_analysis = make_analysis(
        {
            "photos_available": (
                True,
                "Клиент прислал фотографии объекта",
            ),
            "object_materials": (
                "деревянная окрашенная обшивка",
                "Определено по фотографиям объекта",
            ),
        },
        "Получены фотографии и уточнены материалы объекта.",
    )

    result = build_result(
        lead,
        profile,
        current_analysis,
        state,
    )

    state = update_state(
        result,
        state,
    )

    show_result(
        "EVENT 2 — ПОЛУЧЕНЫ ФОТОГРАФИИ",
        result,
    )

    # Новые данные появились.
    assert result.fields["photos_available"].value is True

    assert result.fields["object_materials"].value == (
        "деревянная окрашенная обшивка"
    )

    # Старые данные НЕ потерялись.
    assert result.fields["material"].value == "дерево"
    assert result.fields["dimensions"].value == "280 м²"
    assert result.fields["location"].value == "Челябинск"
    assert result.fields["condition"].value == "плохое состояние"
    assert result.fields["budget"].value == "700–900 тысяч рублей"

    # Теперь объект должен быть готов к следующему этапу.
    assert result.next_step == (
    "Передать объект на предварительную оценку."
    )


    # ========================================================
    # EVENT 3
    # ВЫЯВИЛАСЬ ДОПОЛНИТЕЛЬНАЯ РАБОТА
    # ========================================================

    lead.messages.append(
        make_message(
            3,
            "client",
            (
                "Ещё нужно заменить несколько элементов "
                "обшивки, они совсем плохие."
            ),
        )
    )

    current_analysis = make_analysis(
        {
            "additional_work": (
                "замена отдельных элементов обшивки",
                "Клиент сообщил о дополнительной работе",
            ),
        },
        "Выявлена дополнительная работа по обшивке.",
    )

    result = build_result(
        lead,
        profile,
        current_analysis,
        state,
    )

    state = update_state(
        result,
        state,
    )

    show_result(
        "EVENT 3 — ДОПОЛНИТЕЛЬНАЯ РАБОТА",
        result,
    )

    assert result.fields["additional_work"].value == (
        "замена отдельных элементов обшивки"
    )

    # Проверяем непрерывность состояния.
    assert result.fields["material"].value == "дерево"
    assert result.fields["object_materials"].value == (
        "деревянная окрашенная обшивка"
    )
    assert result.fields["photos_available"].value is True
    assert result.fields["dimensions"].value == "280 м²"
    assert result.fields["budget"].value == "700–900 тысяч рублей"


    # ========================================================
    # EVENT 4
    # ПРЕДВАРИТЕЛЬНОЕ КП ОТПРАВЛЕНО
    # ========================================================

    lead.stage = "PRELIMINARY_KP"

    lead.messages.append(
        make_message(
            4,
            "manager",
            "Отправили клиенту предварительное КП.",
        )
    )

    current_analysis = make_analysis(
        {},
        "Предварительное КП отправлено клиенту.",
    )

    result = build_result(
        lead,
        profile,
        current_analysis,
        state,
    )

    state = update_state(
        result,
        state,
    )

    show_result(
        "EVENT 4 — ПРЕДВАРИТЕЛЬНОЕ КП",
        result,
    )

    assert result.next_step == (
        "Получить обратную связь по предварительному КП."
    )

    # Данные объекта всё ещё существуют.
    assert result.fields["material"].value == "дерево"
    assert result.fields["object_materials"].value == (
        "деревянная окрашенная обшивка"
    )
    assert result.fields["additional_work"].value == (
        "замена отдельных элементов обшивки"
    )


    # ========================================================
    # EVENT 5
    # КЛИЕНТ ОДОБРИЛ ПРЕДВАРИТЕЛЬНОЕ КП
    # ========================================================

    lead.stage = "PRELIMINARY_KP_APPROVED"

    lead.messages.append(
        make_message(
            5,
            "client",
            (
                "По предварительному расчёту всё устраивает. "
                "Давайте назначим замер."
            ),
        )
    )

    current_analysis = make_analysis(
        {},
        "Клиент одобрил предварительное КП.",
    )

    result = build_result(
        lead,
        profile,
        current_analysis,
        state,
    )

    state = update_state(
        result,
        state,
    )

    show_result(
        "EVENT 5 — ПРЕДВАРИТЕЛЬНОЕ КП ОДОБРЕНО",
        result,
    )

    assert result.next_step == (
        "Назначить замер."
    )

    # ========================================================
    # FINAL ASSERTIONS
    # ========================================================

    assert result.fields["material"].value == "дерево"

    assert result.fields["object_materials"].value == (
        "деревянная окрашенная обшивка"
    )

    assert result.fields["dimensions"].value == "280 м²"

    assert result.fields["photos_available"].value is True

    assert result.fields["additional_work"].value == (
        "замена отдельных элементов обшивки"
    )

    print()
    print("=" * 70)
    print("CONTINUOUS QUALIFICATION TEST PASSED")
    print("=" * 70)


if __name__ == "__main__":
    test_continuous_qualification()