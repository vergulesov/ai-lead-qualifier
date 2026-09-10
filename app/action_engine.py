from app.models import LeadInput, AIAnalysis


def _known(analysis: AIAnalysis, field: str) -> bool:
    item = analysis.fields.get(field)
    return (
        item is not None
        and item.value not in (None, "", [], {})
    )


def _value(analysis: AIAnalysis, field: str):
    item = analysis.fields.get(field)
    return item.value if item else None


def _has_object_materials(analysis: AIAnalysis) -> bool:
    """
    Для предварительной оценки достаточно:
    - фото ИЛИ
    - проекта.

    Фото + проект одновременно не требуются.
    """
    return (
        _value(analysis, "photos_available") is True
        or _value(analysis, "project_available") is True
    )


def _action(
    action: str,
    label: str,
    reason: str,
    priority: str = "normal",
) -> dict:
    return {
        "action": action,
        "label": label,
        "reason": reason,
        "priority": priority,
    }


def determine_next_step(
    lead: LeadInput,
    analysis: AIAnalysis,
    missing: list[str],
) -> dict:
    """
    Deterministic Action Engine.

    AI отвечает за анализ клиента.
    Action Engine отвечает за следующее бизнес-действие.

    Отправка сообщений здесь НЕ выполняется.
    """

    stage = (lead.stage or "").strip().upper()

    # Bitrix24 может передавать стадию вместе с ID воронки:
    # например C2:NEW.
    # Для бизнес-логики используем только код стадии.
    if ":" in stage:
        stage = stage.split(":")[-1]

    # =========================================================
    # 1. КРИТИЧЕСКАЯ КВАЛИФИКАЦИЯ
    # =========================================================

    core_fields = (
        "object_type",
        "material",
        "dimensions",
        "location",
        "desired_result",
        "start_timing",
    )

    missing_core = [
        field
        for field in core_fields
        if not _known(analysis, field)
    ]

    if missing_core:
        return _action(
            "CONTINUE_QUALIFICATION",
            "Продолжить квалификацию.",
            "Не заполнены обязательные данные: "
            + ", ".join(missing_core),
            "high",
        )

    # =========================================================
    # 2. ФОТО ИЛИ ПРОЕКТ
    # =========================================================

    # Проверяем только до предварительной оценки.
    # После подготовки предварительного КП это условие
    # больше не должно блокировать дальнейшее движение.
    pre_estimation_stages = {
        "",
        "NEW",
        "QUALIFICATION",
        "PREQUALIFICATION",
        "PREPARATION",
        "ESTIMATION",
        "PRE_ESTIMATION",
        "PRELIMINARY_ESTIMATION",
        "UC_ESTIMATION",
    }

    if stage in pre_estimation_stages and not _has_object_materials(analysis):
        return _action(
            "REQUEST_OBJECT_MATERIALS",
            "Запросить фото объекта или проект.",
            "Для предварительной оценки нужен хотя бы один "
            "материал объекта: фото или проект.",
            "high",
        )

    # =========================================================
    # 3. БЮДЖЕТ
    # =========================================================

    if stage in pre_estimation_stages and not _known(analysis, "budget"):
        return _action(
            "CLARIFY_BUDGET",
            "Уточнить ориентировочный бюджет.",
            "Бюджет клиента пока не определён.",
            "normal",
        )

    # =========================================================
    # 4. RED FLAGS
    # =========================================================

    if analysis.red_flags:
        return _action(
            "REVIEW_RED_FLAGS",
            "Проверить Red Flags.",
            "AI обнаружил факторы, требующие решения менеджера.",
            "high",
        )

    # =========================================================
    # 5. КВАЛИФИКАЦИЯ → ПРЕДВАРИТЕЛЬНАЯ ОЦЕНКА
    # =========================================================

    if stage in {
        "",
        "NEW",
        "QUALIFICATION",
        "PREQUALIFICATION",
        "PREPARATION",
    }:
        return _action(
            "PREPARE_PRELIMINARY_ESTIMATION",
            "Передать объект на предварительную оценку.",
            "Квалификация завершена и есть фото или проект.",
            "high",
        )

    # =========================================================
    # 6. ПРЕДВАРИТЕЛЬНАЯ ОЦЕНКА
    # =========================================================

    if stage in {
        "ESTIMATION",
        "PRE_ESTIMATION",
        "PRELIMINARY_ESTIMATION",
        "UC_ESTIMATION",
    }:
        return _action(
            "PREPARE_PRELIMINARY_KP",
            "Подготовить предварительное КП.",
            "Предварительная оценка выполнена.",
            "high",
        )

    # =========================================================
    # 7. ПРЕДВАРИТЕЛЬНОЕ КП ОТПРАВЛЕНО
    # =========================================================

    if stage in {
        "PRELIMINARY_KP",
        "PRELIMINARY_PROPOSAL",
        "UC_PRELIMINARY_KP",
    }:
        return _action(
            "GET_PRELIMINARY_KP_FEEDBACK",
            "Получить обратную связь по предварительному КП.",
            "Нужно понять, устраивают ли клиента предварительные условия.",
            "high",
        )

    # =========================================================
    # 8. ПРЕДВАРИТЕЛЬНОЕ КП ОДОБРЕНО → ЗАМЕР
    # =========================================================

    if stage in {
        "PRELIMINARY_KP_APPROVED",
        "PRELIMINARY_APPROVED",
        "READY_FOR_MEASUREMENT",
        "UC_READY_FOR_MEASUREMENT",
    }:
        return _action(
            "SCHEDULE_MEASUREMENT",
            "Назначить замер.",
            "Клиент одобрил предварительное КП.",
            "high",
        )

    # =========================================================
    # 9. ЗАМЕР
    # =========================================================

    if stage in {
        "MEASUREMENT",
        "MEASUREMENT_APPOINTMENT",
        "UC_MEASUREMENT",
    }:
        return _action(
            "COMPLETE_MEASUREMENT",
            "Провести замер.",
            "Сделка перешла на этап замера.",
            "high",
        )

    # =========================================================
    # 10. ЗАМЕР ПРОВЕДЁН → ФИНАЛЬНОЕ КП
    # =========================================================

    if stage in {
        "MEASUREMENT_COMPLETED",
        "READY_FOR_FINAL_KP",
        "UC_READY_FOR_FINAL_KP",
    }:
        return _action(
            "PREPARE_FINAL_KP",
            "Подготовить финальное КП.",
            "Замер проведён, можно формировать итоговые цифры.",
            "high",
        )

    # =========================================================
    # 11. ФИНАЛЬНОЕ КП
    # =========================================================

    if stage in {
        "FINAL_KP",
        "FINAL_PROPOSAL",
        "UC_FINAL_KP",
    }:
        return _action(
            "GET_FINAL_KP_FEEDBACK",
            "Получить решение клиента по финальному КП.",
            "Финальное КП отправлено клиенту.",
            "high",
        )

    # =========================================================
    # 12. ДОГОВОР
    # =========================================================

    if stage in {
        "FINAL_KP_APPROVED",
        "READY_FOR_CONTRACT",
        "CONTRACT_PREPARATION",
        "CONTRACT",
        "UC_CONTRACT",
    }:
        return _action(
            "PREPARE_CONTRACT",
            "Подготовить договор.",
            "Клиент согласовал финальные условия.",
            "high",
        )

    # =========================================================
    # 13. ПРЕДОПЛАТА
    # =========================================================

    if stage in {
        "CONTRACT_SIGNED",
        "READY_FOR_PREPAYMENT",
        "PREPAYMENT",
        "PREPAYMENT_INVOICE",
        "UC_PREPAYMENT",
    }:
        return _action(
            "CONTROL_PREPAYMENT",
            "Контролировать получение предоплаты.",
            "Договор согласован, ожидается предоплата.",
            "high",
        )

    # =========================================================
    # 14. FALLBACK
    # =========================================================

    return _action(
        "REVIEW_DEAL",
        "Проверить следующий шаг по сделке.",
        "Для текущего этапа нет специального правила.",
        "normal",
    )