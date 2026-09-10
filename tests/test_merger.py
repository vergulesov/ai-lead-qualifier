from datetime import datetime, timezone
from app.merger import merge_ai_analysis
from app.models import (
    AIAnalysis, AIFieldSuggestion, FieldSource,
    QualificationField, QualificationState
)


def test_manager_value_is_not_overwritten():
    state = QualificationState(fields={
        "budget": QualificationField(
            value=600000,
            source=FieldSource.MANAGER,
            confidence=None,
            updated_at=datetime.now(timezone.utc),
        )
    })

    analysis = AIAnalysis(fields={
        "budget": AIFieldSuggestion(
            value=500000,
            confidence=0.9,
            evidence=["рассчитываем на 500 тысяч"],
        )
    })

    state, alerts = merge_ai_analysis(state, analysis)

    assert state.fields["budget"].value == 600000
    assert state.fields["budget"].source == FieldSource.MANAGER
    assert alerts
