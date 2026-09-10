import base64
import sys
from datetime import datetime, timedelta

from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL


DEAL_ID = 10


def main():
    if len(sys.argv) < 2:
        print("Использование:")
        print("python test_call_activity.py путь_к_ogg")
        return

    audio_path = sys.argv[1]

    bitrix = BitrixClient(BITRIX_WEBHOOK_URL)

    # ---------------------------------------------------------
    # Получаем сделку
    # ---------------------------------------------------------

    deal = bitrix.get_deal(DEAL_ID)

    responsible_id = int(
        deal.get("ASSIGNED_BY_ID") or 1
    )

    contact_id = deal.get("CONTACT_ID")

    print(f"Сделка: #{DEAL_ID}")
    print(f"Ответственный: {responsible_id}")
    print(f"Контакт: {contact_id}")

    # ---------------------------------------------------------
    # Читаем OGG
    # ---------------------------------------------------------

    with open(audio_path, "rb") as f:
        content = base64.b64encode(
            f.read()
        ).decode("ascii")

    filename = audio_path.split("\\")[-1]
    filename = filename.split("/")[-1]

    print(f"Файл: {filename}")

    # ---------------------------------------------------------
    # Время звонка
    # ---------------------------------------------------------

    end_time = datetime.now().astimezone()
    start_time = end_time - timedelta(minutes=2)

    # ---------------------------------------------------------
    # Создаём завершённый ВХОДЯЩИЙ звонок
    # ---------------------------------------------------------

    fields = {
        "OWNER_TYPE_ID": 2,
        "OWNER_ID": DEAL_ID,

        # 2 = Call
        "TYPE_ID": 2,

        # Клиент позвонил нам
        # 1 = incoming
        "DIRECTION": 1,

        # Уже состоялся
        "COMPLETED": "Y",
        "STATUS": 2,

        "SUBJECT": "Входящий звонок",

        "START_TIME": start_time.isoformat(
            timespec="seconds"
        ),

        "END_TIME": end_time.isoformat(
            timespec="seconds"
        ),

        "RESPONSIBLE_ID": responsible_id,

        "DESCRIPTION": (
            "Запись телефонного разговора "
            "с клиентом."
        ),

        "DESCRIPTION_TYPE": 1,

        "FILES": [
            {
                "fileData": [
                    filename,
                    content,
                ]
            }
        ],
    }

    # Если у сделки есть контакт —
    # привязываем звонок к нему тоже.
    if contact_id:
        contact = bitrix.call(
            "crm.contact.get",
            {
                "id": int(contact_id),
            },
        )

        phones = contact.get(
            "PHONE",
            [],
        )

        if phones:
            fields["COMMUNICATIONS"] = [
                {
                    "VALUE": phones[0]["VALUE"],
                    "ENTITY_ID": int(contact_id),
                    "ENTITY_TYPE_ID": 3,
                }
            ]

    print()
    print("Создаём входящий звонок...")

    result = bitrix.call(
        "crm.activity.add",
        {
            "fields": fields,
        },
    )

    print()
    print("✅ Результат:")
    print(result)


if __name__ == "__main__":
    main()