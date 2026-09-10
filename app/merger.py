from datetime import datetime, timezone

from .models import (
    AIAnalysis,
    FieldSource,
    QualificationField,
    QualificationState,
)


def merge_ai_analysis(
    state: QualificationState,
    analysis: AIAnalysis,
) -> tuple[QualificationState, list[str]]:
    now = datetime.now(timezone.utc)
    alerts = list(state.alerts)

    for name, suggestion in analysis.fields.items():

        # null означает:
        # "в текущем сообщении информации по этому полю нет".
        #
        # Это НЕ означает, что ранее известное значение нужно удалить.
        if suggestion.value is None:
            continue

        current = state.fields.get(name)

        # Если поле закреплено менеджером, AI не имеет права
        # автоматически его менять.
        if current and current.source == FieldSource.MANAGER:
            if (
                current.value != suggestion.value
            ):
                alerts.append(
                    f"AI предлагает изменить '{name}' "
                    f"с '{current.value}' на '{suggestion.value}', "
                    "но поле закреплено менеджером."
                )
            continue

        # Новое подтверждённое значение обновляет накопленное состояние.
        state.fields[name] = QualificationField(
            value=suggestion.value,
            source=FieldSource.AI,
            confidence=suggestion.confidence,
            updated_at=now,
            evidence=suggestion.evidence,
        )

    state.alerts = list(dict.fromkeys(alerts))

    return state, state.alerts