from datetime import datetime, timedelta

from app.bitrix import BitrixClient


DEAL_ID = 10


def main():
    client = BitrixClient()

    # Получаем сделку и контакт
    deal = client.call(
        "crm.deal.get",
        {"id": DEAL_ID}
    )

    contact_id = deal.get("CONTACT_ID")

    if not contact_id:
        print("❌ У сделки нет привязанного контакта.")
        return

    # Получаем телефон контакта
    contact = client.call(
        "crm.contact.get",
        {"id": contact_id}
    )

    phones = contact.get("PHONE", [])

    if not phones:
        print("❌ У контакта нет телефона.")
        return

    phone = phones[0].get("VALUE")

    now = datetime.now()
    end = now + timedelta(minutes=5)

    activity_id = client.call(
        "crm.activity.add",
        {
            "fields": {
                "OWNER_TYPE_ID": 2,
                "OWNER_ID": DEAL_ID,
                "TYPE_ID": 2,

                "COMMUNICATIONS": [
                    {
                        "VALUE": phone,
                        "ENTITY_ID": contact_id,
                        "ENTITY_TYPE_ID": 3,
                    }
                ],

                "SUBJECT": "Звонок клиенту",
                "START_TIME": now.isoformat(timespec="seconds"),
                "END_TIME": end.isoformat(timespec="seconds"),
                "COMPLETED": "Y",
                "PRIORITY": 2,
                "RESPONSIBLE_ID": 1,
                "DESCRIPTION": (
                    "Демонстрационный звонок по сделке. "
                    "Имитация результата телефонного контакта."
                ),
                "DESCRIPTION_TYPE": 3,
                "DIRECTION": 2,
            }
        },
    )

    print(f"✅ Звонок создан. Activity ID: {activity_id}")


if __name__ == "__main__":
    main()