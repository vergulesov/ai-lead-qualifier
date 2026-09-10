from .models import (
    AIAnalysis,
    AIFieldSuggestion,
    LeadInput,
    QualificationResult,
    QualificationState,
)
from .profile import Profile
from .merger import merge_ai_analysis
from .scorer import (
    calculate_score,
    calculate_final_score,
    calculate_intent_score,
    missing_data,
    quality,
)
from .action_engine import determine_next_step


def _state_to_analysis(
    state: QualificationState,
    current_analysis: AIAnalysis,
) -> AIAnalysis:
    """
    Builds a cumulative AIAnalysis from the current
    analysis and the already accumulated qualification state.

    The state contains the complete knowledge about the deal.
    New AI analysis contains the latest intent/context data.
    """

    fields = {}

    for name, field in state.fields.items():
        fields[name] = AIFieldSuggestion(
            value=field.value,
            confidence=field.confidence or 1.0,
            evidence=field.evidence,
        )

    return AIAnalysis(
        fields=fields,
        intent=current_analysis.intent,
        object_priority=current_analysis.object_priority,
        client_summary=current_analysis.client_summary,
        client_pain=current_analysis.client_pain,
        contractor_expectations=(
            current_analysis.contractor_expectations
        ),
        red_flags=current_analysis.red_flags,
        next_step=current_analysis.next_step,
        next_contact_date=current_analysis.next_contact_date,
    )


def build_result(
    lead: LeadInput,
    profile: Profile,
    analysis: AIAnalysis,
    state: QualificationState,
) -> QualificationResult:

    # --------------------------------------------------------
    # 1. Merge new AI data into cumulative deal state
    # --------------------------------------------------------

    state, alerts = merge_ai_analysis(
        state,
        analysis,
    )

    # --------------------------------------------------------
    # 2. Build cumulative analysis
    #
    # IMPORTANT:
    # From this point on ALL qualification calculations
    # use the accumulated deal state, not only the latest event.
    # --------------------------------------------------------

    cumulative_analysis = _state_to_analysis(
        state,
        analysis,
    )

    # --------------------------------------------------------
    # 3. Qualification
    # --------------------------------------------------------

    missing = missing_data(
        cumulative_analysis,
        profile,
    )

    score = calculate_score(
        cumulative_analysis,
        profile,
    )

    final_score = calculate_final_score(
        score,
        state.manager_score,
    )

    intent_score = calculate_intent_score(
        cumulative_analysis,
    )

    q = quality(
        score,
        profile,
        cumulative_analysis,
    )

    # --------------------------------------------------------
    # 4. Determine next action
    # --------------------------------------------------------

    action = determine_next_step(
        lead,
        cumulative_analysis,
        missing,
    )

    next_step = action["label"]

    # --------------------------------------------------------
    # 5. Explanation
    # --------------------------------------------------------

    explanation_parts = [
        f"AI score: {score}/100.",
        f"Intent: {cumulative_analysis.intent}.",
        f"Intent score: {intent_score}/100.",
        (
            "Приоритет объекта: "
            f"{cumulative_analysis.object_priority}."
        ),
    ]

    if missing:
        explanation_parts.append(
            "Не хватает данных: "
            + ", ".join(missing)
            + "."
        )

    if cumulative_analysis.red_flags:
        explanation_parts.append(
            "Red flags: "
            + "; ".join(
                cumulative_analysis.red_flags
            )
            + "."
        )

    # --------------------------------------------------------
    # 6. Result
    # --------------------------------------------------------

    return QualificationResult(
        deal_id=lead.deal_id,

        score=score,

        manager_score=state.manager_score,
        manager_reason=state.manager_reason,

        final_score=final_score,

        intent_score=intent_score,

        quality=q,

        intent=cumulative_analysis.intent,

        object_priority=(
            cumulative_analysis.object_priority
        ),

        client_summary=(
            cumulative_analysis.client_summary
        ),

        fields=state.fields,

        red_flags=(
            cumulative_analysis.red_flags
        ),

        alerts=alerts,

        missing_data=missing,

        next_step=next_step,

        next_contact_date=(
            cumulative_analysis.next_contact_date
        ),

        explanation=" ".join(
            explanation_parts
        ),
    )