import json
import os
from datetime import datetime, timezone
from typing import Any

import httpx
from dotenv import load_dotenv

from .models import (
    FieldSource,
    QualificationField,
    QualificationState,
)


load_dotenv()


class BitrixError(RuntimeError):
    pass


class BitrixClient:

    def __init__(
        self,
        webhook_url: str | None = None,
    ):
        self.webhook_url = (
            webhook_url
            or os.getenv("BITRIX_WEBHOOK_URL")
        )

        if not self.webhook_url:
            raise BitrixError(
                "BITRIX_WEBHOOK_URL не найден в .env"
            )

        self.base_url = (
            self.webhook_url.rstrip("/")
        )

    # =========================================================
    # LOW LEVEL REST
    # =========================================================

    def call(
        self,
        method: str,
        payload: dict[str, Any] | None = None,
    ) -> Any:

        url = (
            f"{self.base_url}/{method}.json"
        )

        response = httpx.post(
            url,
            json=payload or {},
            timeout=30,
        )

        if response.status_code >= 400:

            raise BitrixError(
                f"HTTP {response.status_code}: "
                f"{response.text}"
            )

        data = response.json()

        if "error" in data:

            raise BitrixError(
                f"Bitrix error: "
                f"{data.get('error')}: "
                f"{data.get('error_description')}"
            )

        return data.get("result")

    # =========================================================
    # DEAL
    # =========================================================

    def get_deal(
        self,
        deal_id: str | int,
    ) -> dict[str, Any]:

        result = self.call(
            "crm.deal.get",
            {
                "id": int(deal_id),
            },
        )

        if not result:
            raise BitrixError(
                f"Сделка #{deal_id} не найдена"
            )

        return result

    # =========================================================
    # QUALIFICATION STATE
    # =========================================================

    def get_qualification_state(
        self,
        deal: dict[str, Any],
    ) -> QualificationState:
        """
        Восстанавливает накопленное состояние квалификации
        из AI-полей текущей сделки Bitrix24.
        """

        field_map = {
            "object_type":
                "UF_CRM_AI_OBJECT_TYPE",

            "material":
                "UF_CRM_AI_MATERIAL",

            "condition":
                "UF_CRM_AI_OBJECT_STATE",

            "dimensions":
                "UF_CRM_AI_AREA",

            "location":
                "UF_CRM_AI_GEO",

            "project_available":
                "UF_CRM_AI_PROJECT",

            "photos_available":
                "UF_CRM_AI_PHOTOS",

            "desired_result":
                "UF_CRM_AI_DESIRED_RESULT",

            "additional_work":
                "UF_CRM_AI_EXTRA_WORKS",

            "start_timing":
                "UF_CRM_AI_TIMING",

            "budget":
                "UF_CRM_AI_BUDGET",

            "previous_experience":
                "UF_CRM_AI_PREVIOUS_EXPERIENCE",
        }

        state = QualificationState()

        updated_at_raw = deal.get(
            "UF_CRM_AI_UPDATED"
        )

        if updated_at_raw:
            try:
                updated_at = datetime.fromisoformat(
                    str(updated_at_raw).replace(
                        "Z",
                        "+00:00",
                    )
                )
            except ValueError:
                updated_at = datetime.now(
                    timezone.utc
                )
        else:
            updated_at = datetime.now(
                timezone.utc
            )

        for field_name, bitrix_field in field_map.items():

            value = deal.get(
                bitrix_field
            )

            if value in (
                None,
                "",
                [],
                {},
            ):
                continue

            # "Нет" в текстовых AI-полях означает,
            # что значение ещё не определено.
            if (
                field_name not in (
                    "project_available",
                    "photos_available",
                )
                and str(value).strip().lower() in (
                    "нет",
                    "нету",
                )
            ):
                continue

            # Bitrix string-поля хранят boolean как текст.
            if field_name in (
                "project_available",
                "photos_available",
            ):
                normalized = (
                    str(value)
                    .strip()
                    .lower()
                )

                if normalized in (
                    "да",
                    "есть",
                    "true",
                    "1",
                ):
                    value = True

                elif normalized in (
                    "нет",
                    "нету",
                    "false",
                    "0",
                ):
                    value = False

            # Bitrix string-поля хранят boolean как текст.
            if field_name in (
                "project_available",
                "photos_available",
            ):
                normalized = (
                    str(value)
                    .strip()
                    .lower()
                )

                if normalized in (
                    "да",
                    "есть",
                    "true",
                    "1",
                ):
                    value = True

                elif normalized in (
                    "нет",
                    "нету",
                    "false",
                    "0",
                ):
                    value = False

            state.fields[field_name] = QualificationField(
                value=value,
                source=FieldSource.AI,
                confidence=1.0,
                updated_at=updated_at,
                evidence=[],
            )

        score = deal.get(
            "UF_CRM_AI_SCORE"
        )

        if score not in (
            None,
            "",
        ):
            try:
                state.ai_score = int(
                    score
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return state

    # =========================================================
    # TIMELINE
    # =========================================================

    def get_timeline_comments(
        self,
        deal_id: str | int,
    ) -> list[dict[str, Any]]:

        result = self.call(
            "crm.timeline.comment.list",
            {
                "filter": {
                    "ENTITY_ID": int(deal_id),
                    "ENTITY_TYPE": "deal",
                },
                "order": {
                    "ID": "ASC",
                },
            },
        )

        if not result:
            return []

        return result

    # =========================================================
    # DEAL FIELDS
    # =========================================================

    def get_deal_fields(
        self,
    ) -> dict[str, Any]:

        return self.call(
            "crm.deal.fields"
        )

    def get_deal_user_fields(
        self,
    ) -> list[dict[str, Any]]:

        return self.call(
            "crm.deal.userfield.list",
            {
                "filter": {
                    "ENTITY_ID": "CRM_DEAL",
                }
            },
        )

    # =========================================================
    # CREATE CUSTOM FIELD
    # =========================================================

    def create_deal_field(
        self,
        field_name: str,
        label: str,
        field_type: str = "string",
        multiple: bool = False,
    ) -> str:

        result = self.call(
            "crm.deal.userfield.add",
            {
                "fields": {
                    "FIELD_NAME": field_name,
                    "LABEL": label,
                    "USER_TYPE_ID": field_type,
                    "MULTIPLE": (
                        "Y"
                        if multiple
                        else "N"
                    ),
                    "SHOW_IN_LIST": "Y",
                    "EDIT_IN_LIST": "Y",
                }
            },
        )

        return str(result)

    # =========================================================
    # UPDATE FIELD LABELS
    # =========================================================

    def update_deal_field_labels(
        self,
        field_id: int,
        label: str,
    ) -> None:

        result = self.call(
            "crm.deal.userfield.update",
            {
                "id": field_id,
                "fields": {
                    "EDIT_FORM_LABEL": label,
                    "LIST_COLUMN_LABEL": label,
                    "LIST_FILTER_LABEL": label,
                },
            },
        )

        print(
            f"         label update result: "
            f"{result}"
        )

    # =========================================================
    # UPDATE DEAL
    # =========================================================

    def update_deal(
        self,
        deal_id: str | int,
        fields: dict[str, Any],
    ) -> Any:

        return self.call(
            "crm.deal.update",
            {
                "id": int(deal_id),
                "fields": fields,
            },
        )

    # =========================================================
    # WRITE QUALIFICATION RESULT
    # =========================================================

    def write_qualification_result(
        self,
        deal_id: str | int,
        result,
    ) -> dict[str, Any]:

        field_map = {
            "object_type":
                "UF_CRM_AI_OBJECT_TYPE",

            "material":
                "UF_CRM_AI_MATERIAL",

            "condition":
                "UF_CRM_AI_OBJECT_STATE",

            "dimensions":
                "UF_CRM_AI_AREA",

            "location":
                "UF_CRM_AI_GEO",

            "project_available":
                "UF_CRM_AI_PROJECT",

            "photos_available":
                "UF_CRM_AI_PHOTOS",

            "desired_result":
                "UF_CRM_AI_DESIRED_RESULT",

            "additional_work":
                "UF_CRM_AI_EXTRA_WORKS",

            "start_timing":
                "UF_CRM_AI_TIMING",

            "budget":
                "UF_CRM_AI_BUDGET",

            "previous_experience":
                "UF_CRM_AI_PREVIOUS_EXPERIENCE",

            "next_step":
                "UF_CRM_1788381812",
        }

        fields = {}
        updated = []

        # -----------------------------------------------------
        # AI fields
        #
        # Важно:
        # result.fields содержит уже накопленное состояние,
        # поэтому существующие AI-поля можно обновлять.
        # Иначе Continuous Qualification не сможет
        # дополнять или уточнять ранее полученные данные.
        # -----------------------------------------------------

        for field_name, bitrix_field in field_map.items():

            qualification_field = (
                result.fields.get(
                    field_name
                )
            )

            if not qualification_field:
                # Поле неизвестно — очищаем его в Bitrix,
                # чтобы "Нет" не выглядело как установленное значение.
                fields[bitrix_field] = ""
                updated.append(
                    {
                        "field": field_name,
                        "value": None,
                    }
                )
                continue

            value = qualification_field.value

            if value is None:
                fields[bitrix_field] = ""
                updated.append(
                    {
                        "field": field_name,
                        "value": None,
                    }
                )
                continue

            # Boolean переводим в понятный
            # для текущего string-поля Bitrix формат.
            if isinstance(
                value,
                bool,
            ):
                value = (
                    "Да"
                    if value
                    else "Нет"
                )

            fields[bitrix_field] = str(
                value
            )

            updated.append(
                {
                    "field": field_name,
                    "value": value,
                }
            )

        # -----------------------------------------------------
        # NEXT STEP
        # -----------------------------------------------------

        fields[
            "UF_CRM_1788381812"
        ] = result.next_step or ""

        # -----------------------------------------------------
        # SCORE
        # -----------------------------------------------------

        fields[
            "UF_CRM_AI_SCORE"
        ] = str(
            result.score
        )

        # -----------------------------------------------------
        # QUALITY
        # -----------------------------------------------------

        fields[
            "UF_CRM_AI_QUALITY"
        ] = result.quality

        # -----------------------------------------------------
        # SUMMARY
        # -----------------------------------------------------

        if result.client_summary:
            fields[
                "UF_CRM_AI_SUMMARY"
            ] = result.client_summary

        # -----------------------------------------------------
        # REPORT
        # -----------------------------------------------------

        report = {
            "deal_id": str(
                result.deal_id
            ),
            "score": result.score,
            "intent_score": result.intent_score,
            "quality": result.quality,
            "intent": result.intent,
            "object_priority": result.object_priority,
            "missing_data": result.missing_data,
            "red_flags": result.red_flags,
            "alerts": result.alerts,
            "next_step": result.next_step,
            "next_contact_date": (
                result.next_contact_date
            ),
            "explanation": result.explanation,
        }

        fields[
            "UF_CRM_AI_REPORT"
        ] = json.dumps(
            report,
            ensure_ascii=False,
            default=str,
        )

        # -----------------------------------------------------
        # UPDATED
        # -----------------------------------------------------

        fields[
            "UF_CRM_AI_UPDATED"
        ] = datetime.now(
            timezone.utc
        ).isoformat()

        # -----------------------------------------------------
        # WRITE
        # -----------------------------------------------------

        if fields:

            self.update_deal(
                deal_id,
                fields,
            )

        return {
            "deal_id": str(
                deal_id
            ),
            "updated": updated,
            "ai_score": result.score,
            "ai_quality": result.quality,
        }