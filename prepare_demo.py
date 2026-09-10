from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL


DEAL_ID = 10
RESET_STAGE = "C2:NEW"

AI_FIELDS = [
    "UF_CRM_AI_OBJECT_TYPE",
    "UF_CRM_AI_MATERIAL",
    "UF_CRM_AI_OBJECT_STATE",
    "UF_CRM_AI_AREA",
    "UF_CRM_AI_GEO",
    "UF_CRM_AI_PROJECT",
    "UF_CRM_AI_PHOTOS",
    "UF_CRM_AI_DESIRED_RESULT",
    "UF_CRM_AI_EXTRA_WORKS",
    "UF_CRM_AI_TIMING",
    "UF_CRM_AI_BUDGET",
    "UF_CRM_AI_PREVIOUS_EXPERIENCE",
    "UF_CRM_AI_SCORE",
    "UF_CRM_AI_QUALITY",
    "UF_CRM_AI_SUMMARY",
    "UF_CRM_AI_REPORT",
    "UF_CRM_AI_UPDATED",
    "UF_CRM_1788381812",  # AI Next Step
]


CLIENT_COMMENT_PREFIXES = (
    "Клиент:\n",
    "Клиент:",
    "Входящий звонок — расшифровка:",
)

CALL_SUBJECT = "Входящий звонок"
CALL_DESCRIPTION = "Запись телефонного разговора с клиентом."


def get_timeline_comments(bitrix):
    result = bitrix.call(
        "crm.timeline.comment.list",
        {
            "filter": {
                "ENTITY_ID": DEAL_ID,
                "ENTITY_TYPE": "deal",
            },
            "select": ["ID", "COMMENT", "CREATED"],
        },
    )
    return result or []


def get_activities(bitrix):
    result = bitrix.call(
        "crm.activity.list",
        {
            "filter": {
                "OWNER_TYPE_ID": 2,
                "OWNER_ID": DEAL_ID,
            },
            "select": ["ID", "SUBJECT", "DESCRIPTION"],
        },
    )
    return result or []


def is_our_comment(comment):
    text = (comment.get("COMMENT") or "").strip()
    return text.startswith(CLIENT_COMMENT_PREFIXES)


def is_our_call(activity):
    subject = (activity.get("SUBJECT") or "").strip()
    description = (activity.get("DESCRIPTION") or "").strip()
    return subject == CALL_SUBJECT or description == CALL_DESCRIPTION


def delete_demo_comments(bitrix):
    comments = get_timeline_comments(bitrix)
    deleted = 0

    for comment in comments:
        if not is_our_comment(comment):
            continue

        comment_id = int(comment["ID"])
        text = (comment.get("COMMENT") or "").replace("\n", " ")
        print(f"Удаляем тестовый Timeline-комментарий #{comment_id}: {text[:100]}")

        bitrix.call(
            "crm.timeline.comment.delete",
            {
                "id": comment_id,
                "ownerTypeId": 2,
                "ownerId": DEAL_ID,
            },
        )
        deleted += 1

    return deleted


def delete_demo_calls(bitrix):
    activities = get_activities(bitrix)
    deleted = 0

    for activity in activities:
        if not is_our_call(activity):
            continue

        activity_id = int(activity["ID"])
        subject = (activity.get("SUBJECT") or "").strip()
        print(f"Удаляем тестовый звонок #{activity_id}: {subject}")

        bitrix.call("crm.activity.delete", {"id": activity_id})
        deleted += 1

    return deleted


def reset_deal_fields(bitrix):
    fields = {"STAGE_ID": RESET_STAGE}
    fields.update({field: "" for field in AI_FIELDS})

    bitrix.update_deal(DEAL_ID, fields)


def main():
    bitrix = BitrixClient(BITRIX_WEBHOOK_URL)

    deal = bitrix.get_deal(DEAL_ID)
    if not deal:
        raise RuntimeError(f"Сделка #{DEAL_ID} не найдена.")

    print(f"Подготавливаем сделку #{DEAL_ID} к записи видео")
    print(f"Название: {deal.get('TITLE')}")
    print(f"Контакт ID: {deal.get('CONTACT_ID')}")
    print(f"Текущий этап: {deal.get('STAGE_ID')}")
    print()

    print("1. Очищаем тестовые Timeline-комментарии...")
    comments_deleted = delete_demo_comments(bitrix)
    print(f"   Удалено: {comments_deleted}")
    print()

    print("2. Очищаем тестовые звонки...")
    calls_deleted = delete_demo_calls(bitrix)
    print(f"   Удалено: {calls_deleted}")
    print()

    print("3. Сбрасываем AI-поля и этап сделки...")
    reset_deal_fields(bitrix)
    print("   AI-поля очищены")
    print(f"   Этап установлен: {RESET_STAGE}")
    print()

    refreshed = bitrix.get_deal(DEAL_ID)
    print("Готово.")
    print(f"Сделка: #{DEAL_ID}")
    print(f"Этап: {refreshed.get('STAGE_ID')}")
    print(f"Контакт ID: {refreshed.get('CONTACT_ID')}")
    print()
    print("Контакт, телефон и Open Line не изменялись.")
    print("Сделка готова для записи видео.")


if __name__ == "__main__":
    main()
