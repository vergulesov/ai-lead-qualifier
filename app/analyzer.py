import json
import re
import time
import uuid

import httpx

from .models import AIAnalysis, LeadInput
from .profile import Profile


class AnalyzerError(RuntimeError):
    pass


SYSTEM_PROMPT = """
Ты — AI-модуль извлечения фактов из лида.

Твоя задача — извлечь факты только из предоставленного текста.

КРИТИЧЕСКИЕ ПРАВИЛА:

1. НИЧЕГО НЕ ПРИДУМЫВАЙ.
   Не используй внешние знания и типичные сценарии.

2. UNKNOWN и FALSE — разные значения.

   Если клиент сказал:
   "проекта нет"
   → project_available = false

   Если клиент ничего не сказал о проекте:
   → project_available = null

   Если клиент сказал:
   "фотографий нет"
   → photos_available = false

   Если клиент ничего не сказал о фотографиях:
   → photos_available = null

3. Для неизвестного поля:

   value = null
   confidence = 0
   evidence = []

4. Для известного поля:

   value = фактическое значение
   confidence = число от 0 до 1
   evidence = короткая цитата из исходного текста

5. Если значение нельзя подтвердить цитатой,
   оно считается неизвестным.

6. Не интерпретируй отсутствие информации как false.

7. Не рассчитывай score.

8. Не придумывай intent и object_priority.
   Они должны следовать только из текста.

9. Не добавляй поля, которых нет в PROFILE.

10. Для boolean-полей используй только:
    true
    false
    null

11. Все значения полей должны соответствовать
    фактическому содержанию текста.

12. Если в тексте сказано "материал пока не определён",
    это означает:
    material = null

13. Не заменяй неизвестное значение фразами:
    "не определён",
    "неизвестно",
    "нет данных".
    Используй JSON null.

14. Верни ТОЛЬКО JSON.
    Никакого markdown.
    Никаких ```json.
    Никаких пояснений.

ФОРМАТ:

{
  "fields": {
    "field_name": {
      "value": null,
      "confidence": 0,
      "evidence": []
    }
  },
  "intent": "UNCERTAIN",
  "object_priority": "NORMAL",
  "client_summary": "",
  "client_pain": null,
  "contractor_expectations": null,
  "red_flags": [],
  "next_step": null,
  "next_contact_date": null
}

ТОЛЬКО элементы внутри "fields" имеют:
value / confidence / evidence.

Все остальные поля являются обычными значениями.
"""


class GigaChatAnalyzer:

    def __init__(
        self,
        credentials,
        model,
        api_url,
        auth_url,
        scope="GIGACHAT_API_PERS",
        timeout=90,
        retries=2,
    ):
        if not credentials:
            raise AnalyzerError(
                "GIGACHAT_CREDENTIALS не указан"
            )

        self.credentials = credentials
        self.model = model
        self.api_url = api_url
        self.auth_url = auth_url
        self.scope = scope
        self.timeout = timeout
        self.retries = retries

        self.access_token = None

    # =========================================================
    # AUTH
    # =========================================================

    def _get_access_token(self) -> str:

        rq_uid = str(uuid.uuid4())

        headers = {
            "Authorization": (
                f"Basic {self.credentials}"
            ),
            "RqUID": rq_uid,
            "Content-Type": (
                "application/x-www-form-urlencoded"
            ),
        }

        data = {
            "scope": self.scope,
        }

        try:
            with httpx.Client(
                timeout=self.timeout,
                verify=False,
            ) as client:

                response = client.post(
                    self.auth_url,
                    headers=headers,
                    data=data,
                )

            if response.status_code >= 400:

                print(
                    "GIGACHAT AUTH STATUS:",
                    response.status_code,
                )

                print(
                    "GIGACHAT AUTH RESPONSE:",
                    response.text,
                )

            response.raise_for_status()

            result = response.json()

            token = result.get(
                "access_token"
            )

            if not token:
                raise AnalyzerError(
                    "GigaChat не вернул access_token"
                )

            self.access_token = token

            return token

        except Exception as exc:

            raise AnalyzerError(
                f"GigaChat authorization error: {exc}"
            ) from exc

    # =========================================================
    # ANALYZE
    # =========================================================

    def analyze(
        self,
        lead: LeadInput,
        profile: Profile,
    ) -> AIAnalysis:

        prompt = self._build_prompt(
            lead,
            profile,
        )

        last_error = None

        for attempt in range(
            self.retries + 1
        ):

            try:

                if not self.access_token:
                    self._get_access_token()

                payload = {
                    "model": self.model,
                    "temperature": 0.1,
                    "top_p": 0.1,
                    "max_tokens": 4000,
                    "messages": [
                        {
                            "role": "system",
                            "content": SYSTEM_PROMPT,
                        },
                        {
                            "role": "user",
                            "content": prompt,
                        },
                    ],
                }

                headers = {
                    "Authorization": (
                        f"Bearer "
                        f"{self.access_token}"
                    ),
                    "Content-Type": (
                        "application/json"
                    ),
                }

                with httpx.Client(
                    timeout=self.timeout,
                    verify=False,
                ) as client:

                    response = client.post(
                        self.api_url,
                        headers=headers,
                        json=payload,
                    )

                # Если токен протух —
                # получаем новый и повторяем попытку.
                if response.status_code == 401:

                    self.access_token = None

                    if attempt < self.retries:
                        print(
                            "GIGACHAT TOKEN EXPIRED, "
                            "REFRESHING..."
                        )
                        continue

                if response.status_code >= 400:

                    print(
                        "GIGACHAT STATUS:",
                        response.status_code,
                    )

                    print(
                        "GIGACHAT RESPONSE:",
                        response.text,
                    )

                response.raise_for_status()

                data = response.json()

                text = self._extract_text(
                    data
                )

                print()
                print(
                    "=" * 70
                )
                print(
                    f"GIGACHAT RAW RESPONSE "
                    f"ATTEMPT {attempt + 1}"
                )
                print(
                    "=" * 70
                )
                print(
                    repr(text)
                )
                print(
                    "=" * 70
                )
                print()

                raw_analysis = (
                    self._extract_json(
                        text
                    )
                )

                normalized = (
                    self._normalize_response(
                        raw_analysis
                    )
                )

                analysis = (
                    AIAnalysis.model_validate(
                        normalized
                    )
                )

                return self._sanitize_unknowns(
                    analysis
                )

            except Exception as exc:

                last_error = exc

                print(
                    f"GIGACHAT ANALYZER ATTEMPT "
                    f"{attempt + 1}/"
                    f"{self.retries + 1} FAILED:"
                )

                print(
                    str(exc)
                )

                if attempt < self.retries:
                    time.sleep(
                        1 + attempt
                    )

        raise AnalyzerError(
            f"GigaChat error: {last_error}"
        ) from last_error

    # =========================================================
    # RESPONSE
    # =========================================================

    @staticmethod
    def _extract_text(
        data: dict,
    ) -> str:

        try:

            return (
                data["choices"][0]
                ["message"]["content"]
            )

        except (
            KeyError,
            IndexError,
            TypeError,
        ) as exc:

            raise AnalyzerError(
                "Не удалось получить текст "
                "из ответа GigaChat"
            ) from exc

    # =========================================================
    # PROMPT
    # =========================================================

    @staticmethod
    def _build_prompt(
        lead: LeadInput,
        profile: Profile,
    ) -> str:

        fields = {}

        for name, definition in (
            profile.data
            .get("fields", {})
            .items()
        ):

            fields[name] = {
                "description": definition.get(
                    "description",
                    "",
                )
            }

        context_parts = []

        # CRM-данные
        if lead.crm_fields:

            context_parts.append(
                "CRM FIELDS:\n"
                + json.dumps(
                    lead.crm_fields,
                    ensure_ascii=False,
                    indent=2,
                )
            )

        # Сообщения
        if lead.messages:

            messages = []

            for message in lead.messages:

                messages.append(
                    f"{message.role}: "
                    f"{message.text}"
                )

            context_parts.append(
                "MESSAGES:\n"
                + "\n".join(messages)
            )

        # Расшифровки звонков
        transcripts = []

        for call in lead.calls:

            if call.transcript:

                transcripts.append(
                    call.transcript
                )

        if transcripts:

            context_parts.append(
                "CALL TRANSCRIPTS:\n"
                + "\n\n".join(
                    transcripts
                )
            )

        context = (
            "\n\n".join(
                context_parts
            )
            or "(no context)"
        )

        return f"""
PROFILE FIELDS:

{json.dumps(
    fields,
    ensure_ascii=False,
    indent=2,
)}

LEAD CONTEXT:

{context}

Задача:

Извлеки значения ТОЛЬКО для полей,
указанных в PROFILE FIELDS.

Для каждого поля:

Факт есть:
- value = фактическое значение
- confidence = 0..1
- evidence = короткая точная цитата из контекста

Факт явно отрицательный:
- value = false
- confidence = 1
- evidence = подтверждающая цитата

Факта нет:
- value = null
- confidence = 0
- evidence = []

ОТСУТСТВИЕ ИНФОРМАЦИИ НЕ РАВНО FALSE.

Отдельно определи:

intent:
- BUYING_SOON
- HIGH_INTENT_LATER
- LOW_INTENT
- UNCERTAIN

object_priority:
- HIGH
- NORMAL
- LOW

Но используй только информацию,
которая есть в контексте.

Не рассчитывай score.

Верни только JSON.
""".strip()

    # =========================================================
    # NORMALIZE
    # =========================================================

    @staticmethod
    def _normalize_response(
        data: dict,
    ) -> dict:

        if not isinstance(
            data,
            dict,
        ):
            raise AnalyzerError(
                "LLM JSON root must be object"
            )

        result = dict(data)

        fields = result.get(
            "fields",
            {},
        )

        if not isinstance(
            fields,
            dict,
        ):
            fields = {}

        clean_fields = {}

        for name, value in fields.items():

            if isinstance(
                value,
                dict,
            ):

                raw_confidence = value.get(
                    "confidence",
                    0,
                )

                try:

                    confidence = float(
                        raw_confidence
                    )

                except (
                    TypeError,
                    ValueError,
                ):

                    confidence = 0.0

                confidence = max(
                    0.0,
                    min(
                        1.0,
                        confidence,
                    ),
                )

                evidence = value.get(
                    "evidence",
                    [],
                )

                if not isinstance(
                    evidence,
                    list,
                ):
                    evidence = []

                clean_fields[name] = {
                    "value": value.get(
                        "value"
                    ),
                    "confidence": confidence,
                    "evidence": [
                        str(item)
                        for item in evidence
                    ],
                }

            else:

                clean_fields[name] = {
                    "value": value,
                    "confidence": 0.0,
                    "evidence": [],
                }

        result["fields"] = clean_fields

        scalar_fields = [
            "intent",
            "object_priority",
            "client_summary",
            "client_pain",
            "contractor_expectations",
            "next_step",
            "next_contact_date",
        ]

        for field_name in scalar_fields:

            value = result.get(
                field_name
            )

            if isinstance(
                value,
                dict,
            ):

                result[field_name] = (
                    value.get("value")
                )

        red_flags = result.get(
            "red_flags"
        )

        if isinstance(
            red_flags,
            dict,
        ):

            red_flags = red_flags.get(
                "value"
            )

        if red_flags is None:

            result["red_flags"] = []

        elif isinstance(
            red_flags,
            list,
        ):

            result["red_flags"] = red_flags

        else:

            result["red_flags"] = [
                str(red_flags)
            ]

        return result

    # =========================================================
    # UNKNOWN / FALSE PROTECTION
    # =========================================================

    @staticmethod
    def _sanitize_unknowns(
        analysis: AIAnalysis,
    ) -> AIAnalysis:

        """
        false без evidence превращаем в UNKNOWN.

        false + evidence
            = подтверждённый FALSE

        false + no evidence
            = UNKNOWN
        """

        for field in analysis.fields.values():

            if (
                field.value is False
                and not field.evidence
            ):

                field.value = None
                field.confidence = 0.0
                field.evidence = []

        return analysis

    # =========================================================
    # JSON EXTRACTION
    # =========================================================

    @staticmethod
    def _extract_json(
        text: str,
    ) -> dict:

        if not isinstance(
            text,
            str,
        ):
            raise AnalyzerError(
                "LLM response is not text"
            )

        cleaned = text.strip()

        # Убираем markdown fence
        cleaned = re.sub(
            r"^```json\s*",
            "",
            cleaned,
            flags=re.IGNORECASE,
        )

        cleaned = re.sub(
            r"^```\s*",
            "",
            cleaned,
        )

        cleaned = re.sub(
            r"\s*```$",
            "",
            cleaned,
        )

        start = cleaned.find("{")
        end = cleaned.rfind("}")

        if start == -1:
            raise AnalyzerError(
                "LLM did not return JSON"
            )

        if end <= start:
            raise AnalyzerError(
                "LLM returned incomplete JSON"
            )

        json_text = cleaned[
            start:end + 1
        ]

        try:

            result = json.loads(
                json_text
            )

        except json.JSONDecodeError as exc:

            raise AnalyzerError(
                "LLM returned invalid JSON: "
                f"{exc}"
            ) from exc

        if not isinstance(
            result,
            dict,
        ):
            raise AnalyzerError(
                "LLM JSON root must be object"
            )

        return result