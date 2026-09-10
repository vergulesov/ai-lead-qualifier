from .bitrix import BitrixClient


QUALIFICATION_FIELDS = {
    "object_type": "Тип объекта",
    "material": "Материал дома",
    "condition": "Состояние дома",
    "dimensions": "Размеры",
    "location": "Локация",
    "project_available": "Проект",
    "photos_available": "Фотографии",
    "desired_result": "Желаемый результат",
    "additional_work": "Дополнительные работы",
    "start_timing": "Срок начала работ",
    "budget": "Бюджет",
    "previous_experience": "Предыдущий опыт",
}


AI_FIELDS = {
    "ai_score": "AI Score",
    "ai_quality": "AI Quality",
    "ai_summary": "AI Summary",
    "ai_report": "AI Report",
    "ai_updated": "AI Updated",
}


def normalize_name(value: str) -> str:
    return (
        value.upper()
        .replace("-", "_")
        .replace(" ", "_")
    )


def main():
    client = BitrixClient()

    print("Получаем пользовательские поля Bitrix...")

    user_fields = client.get_deal_user_fields()

    print(
        f"Получено пользовательских полей: "
        f"{len(user_fields)}"
    )

    # FIELD_NAME -> данные поля
    existing = {
        field["FIELD_NAME"]: field
        for field in user_fields
    }

    all_fields = {
        **QUALIFICATION_FIELDS,
        **AI_FIELDS,
    }

    for key, title in all_fields.items():

        field_name = (
            f"UF_CRM_AI_{normalize_name(key)}"
        )

        # Поле уже существует
        if field_name in existing:

            field = existing[field_name]

            field_id = field.get("ID")

            print(
                f"[EXISTS] {title} -> "
                f"{field_name} (ID={field_id})"
            )

            if field_id:
                client.update_deal_field_labels(
                    field_id=int(field_id),
                    label=title,
                )

            continue

        # Поля ещё нет
        print(
            f"[CREATE] {title} -> "
            f"{field_name}"
        )

        field_id = client.create_deal_field(
            field_name=field_name,
            label=title,
            field_type="string",
        )

        print(
            f"         создано, ID={field_id}"
        )

    print()
    print("Готово.")


if __name__ == "__main__":
    main()