from datetime import datetime, timezone
import json
from typing import Any

from .bitrix import BitrixClient
from .models import QualificationResult


FIELD_MAP = {
    "object_type": "UF_CRM_AI_OBJECT_TYPE",
    "material": "UF_CRM_AI_MATERIAL",
    "condition": "UF_CRM_AI_CONDITION",
    "dimensions": "UF_CRM_AI_DIMENSIONS",
    "location": "UF_CRM_AI_LOCATION",
    "project_available": "UF_CRM_AI_PROJECT_AVAILABLE",
    "photos_available": "UF_CRM_AI_PHOTOS_AVAILABLE",
    "desired_result": "UF_CRM_AI_DESIRED_RESULT",
    "additional_work": "UF_CRM_AI_ADDITIONAL_WORK",
    "start_timing": "UF_CRM_AI_START_TIMING",
    "budget": "UF_CRM_AI_BUDGET",
    "previous_experience": "UF_CRM_AI_PREVIOUS_EXPERIENCE",
}


class BitrixWriter:

    def __init__(self, client: BitrixClient):
        self.client = client

    def write_result(
        self,
        result: QualificationResult,
    ) -> dict[str, Any]:

        deal = self.client.call(
            "crm.deal.get",
            {
                "id": result.deal_id,
            },
        )

        fields_to_update = {}

        updated = []
        skipped = []

        for key, bitrix_field in FIELD_MAP.items():

            qualification_field = result.fields.get(key)

            if not qualification_field:
                continue

            value = qualification_field.value

            if value is None:
                continue

            current_value = deal.get(bitrix_field)

            # Не перезаписываем данные менеджера.
            if current_value not in (None, "", False):

                skipped.append({
                    "field": key,
                    "reason": "already_filled",
                    "current_value": current_value,
                })

                continue

            fields_to_update[bitrix_field] = self._prepare_value(
                value
            )

            updated.append({
                "field": key,
                "value": value,
            })

        # AI-служебные поля.
        fields_to_update.update({
            "UF_CRM_AI_AI_SCORE": str(result.score),
            "UF_CRM_AI_AI_QUALITY": result.quality,
            "UF_CRM_AI_AI_SUMMARY": result.client_summary,
            "UF_CRM_AI_AI_REPORT": json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            "UF_CRM_AI_AI_UPDATED": datetime.now(
                timezone.utc
            ).isoformat(),
        })

        if fields_to_update:

            self.client.call(
                "crm.deal.update",
                {
                    "id": result.deal_id,
                    "fields": fields_to_update,
                },
            )

        return {
            "deal_id": result.deal_id,
            "updated": updated,
            "skipped": skipped,
            "ai_score": result.score,
            "ai_quality": result.quality,
        }

    @staticmethod
    def _prepare_value(value: Any) -> str:

        if isinstance(value, bool):
            return "Да" if value else "Нет"

        if isinstance(value, (dict, list)):
            return json.dumps(
                value,
                ensure_ascii=False,
            )

        return str(value)