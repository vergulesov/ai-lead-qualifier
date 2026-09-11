from .analyzer import GigaChatAnalyzer, AnalyzerError
from .bitrix import BitrixClient
from .config import (
    BITRIX_WEBHOOK_URL,
    GIGACHAT_CREDENTIALS,
    GIGACHAT_MODEL,
    GIGACHAT_API_URL,
    GIGACHAT_AUTH_URL,
    GIGACHAT_SCOPE,
    GIGACHAT_TIMEOUT,
    GIGACHAT_RETRIES,
    PROFILES_DIR,
)
from .models import (
    AIFieldSuggestion,
    Client,
    LeadInput,
    Message,
)
from .pipeline import build_result
from .profile import load_profile


def process_deal(
    deal_id: str | int,
    client: BitrixClient | None = None,
    input_text: str | None = None,
    has_photo: bool | None = None,
) -> dict:
    """
    Полный цикл квалификации сделки.

    Может запускаться:
    - из Timeline webhook;
    - из Open Line polling.

    has_photo — детерминированный факт наличия фотографии
    во входящем сообщении Open Line. Если значение известно,
    оно имеет приоритет над интерпретацией текста AI.
    """

    deal_id = str(deal_id)

    if client is None:
        client = BitrixClient(BITRIX_WEBHOOK_URL)

    print(f"[QUALIFIER] Получаем сделку #{deal_id}...")
    deal = client.get_deal(deal_id)
    print(f"[QUALIFIER] Сделка: {deal.get('TITLE')}")
    print(f"[QUALIFIER] Стадия: {deal.get('STAGE_ID')}")

    if input_text is not None:
        text = input_text.strip()
        print("[QUALIFIER] Источник: Open Line")
        print(f"[QUALIFIER] Новое сообщение: {text}")

        if not text:
            print("[QUALIFIER] Пустое сообщение.")
            return {"status": "skipped", "reason": "empty_input", "deal_id": deal_id}

        message_source = "bitrix_openline"
        message_id = f"openline-{deal_id}"

    else:
        comments = client.get_timeline_comments(deal_id)
        print(f"[QUALIFIER] Timeline comments: {len(comments)}")
        text_parts = []
        for comment in comments:
            comment_text = comment.get("COMMENT")
            if comment_text:
                text_parts.append(comment_text)

        text = "\n\n".join(text_parts).strip()
        if not text:
            print("[QUALIFIER] Нет текста для анализа.")
            return {"status": "skipped", "reason": "no_timeline_text", "deal_id": deal_id}

        message_source = "bitrix_timeline"
        message_id = f"timeline-{deal_id}"

    client_data = Client(name=deal.get("TITLE"))

    message = Message(
        id=message_id,
        timestamp=deal.get("DATE_MODIFY") or deal.get("DATE_CREATE"),
        role="client" if input_text is not None else "unknown",
        text=text,
        source=message_source,
    )

    lead = LeadInput(
        deal_id=deal_id,
        title=deal.get("TITLE"),
        stage=deal.get("STAGE_ID"),
        client=client_data,
        crm_fields=deal,
        messages=[message],
        calls=[],
    )

    profile = load_profile(PROFILES_DIR, "best_paints")

    print("[QUALIFIER] Запускаем AI-анализ...")

    analyzer = GigaChatAnalyzer(
        credentials=GIGACHAT_CREDENTIALS,
        model=GIGACHAT_MODEL,
        api_url=GIGACHAT_API_URL,
        auth_url=GIGACHAT_AUTH_URL,
        scope=GIGACHAT_SCOPE,
        timeout=GIGACHAT_TIMEOUT,
        retries=GIGACHAT_RETRIES,
    )

    try:
        analysis = analyzer.analyze(lead, profile)
    except AnalyzerError:
        print("[QUALIFIER] AI-анализ завершился ошибкой.")
        raise

    # =========================================================
    # DETERMINISTIC ATTACHMENT FACTS
    # =========================================================

    # Для фотографии источник истины — вложение Open Line,
    # а не текст клиента.
    #
    # True: фотография реально приложена.
    # False: в текущем сообщении фотографии нет.
    # False здесь НЕ записывается в накопленное состояние:
    # это только защита от ложного вывода AI.
    if has_photo is not None:
        photo_field = analysis.fields.get("photos_available")

        if photo_field is None:
            photo_field = AIFieldSuggestion()
            analysis.fields["photos_available"] = photo_field

        if has_photo:
            photo_field.value = True
            photo_field.confidence = 1.0
            photo_field.evidence = [
                "Фактическое вложение изображения в Open Line."
            ]
        else:
            # Важно: null позволяет merge_ai_analysis сохранить
            # ранее подтверждённое значение, но не позволяет AI
            # установить true по фразе "Фото сейчас скину".
            photo_field.value = None
            photo_field.confidence = 0.0
            photo_field.evidence = []

        print(
            f"[QUALIFIER] Фото по факту вложения Open Line: "
            f"{'Да' if has_photo else 'Нет'}"
        )

    state = client.get_qualification_state(deal)

    result = build_result(
        lead,
        profile,
        analysis,
        state,
    )

    print(
        "[QUALIFIER] "
        f"Score={result.score}, "
        f"Quality={result.quality}, "
        f"Intent={result.intent}"
    )
    print(f"[QUALIFIER] Next Step={result.next_step}")

    write_result = client.write_qualification_result(
        deal_id=deal_id,
        result=result,
    )

    print("[QUALIFIER] Результат записан в Bitrix24.")

    return {
        "status": "processed",
        "deal_id": deal_id,
        "score": result.score,
        "quality": result.quality,
        "intent": result.intent,
        "next_step": result.next_step,
        "missing_data": result.missing_data,
        "bitrix": write_result,
    }
