from app.bitrix import BitrixClient
from app.openline import OpenLineClient


DEAL_ID = 10


def main():
    client = BitrixClient()
    openline = OpenLineClient(client)

    messages = openline.get_client_messages(DEAL_ID)

    print(f"Сообщения клиента по сделке #{DEAL_ID}:")
    print()

    for message in messages:
        print(f"[{message['id']}] {message['date']}")

        if message["text"]:
            print("  Текст:", message["text"])

        if message["files"]:
            for file_info in message["files"]:
                print(
                    "  Файл:",
                    file_info["name"],
                    "| type:", file_info["type"],
                    "| extension:", file_info["extension"],
                )

        print("  Фото:", "ДА" if message["has_photo"] else "нет")
        print()

    photo_messages = [
        message for message in messages
        if message["has_photo"]
    ]

    print(
        "Найдено сообщений с фотографиями:",
        len(photo_messages),
    )


if __name__ == "__main__":
    main()
