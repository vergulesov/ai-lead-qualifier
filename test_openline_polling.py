import tempfile
import time
import traceback
from pathlib import Path

from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL
from app.openline import OpenLineClient
from app.speech_to_text import transcribe_audio


DEAL_ID = 10
CHAT_ID = 10
INTERVAL = 5


bitrix = BitrixClient(BITRIX_WEBHOOK_URL)
openline = OpenLineClient(bitrix)

last_message_id = 0


def add_client_message_to_timeline(text: str) -> None:
    result = bitrix.call(
        "crm.timeline.comment.add",
        {
            "fields": {
                "ENTITY_ID": DEAL_ID,
                "ENTITY_TYPE": "deal",
                "COMMENT": f"Клиент:\n{text}",
            }
        },
    )

    print(
        f"Сообщение добавлено в Timeline. ID комментария: {result}"
    )


print(f"Слушаем Open Line сделки #{DEAL_ID}")
print(f"Чат: #{CHAT_ID}")
print(f"Проверка каждые {INTERVAL} секунд.")
print()


while True:
    try:
        messages = openline.get_client_messages(
            DEAL_ID,
            chat_id=CHAT_ID,
        )

        if messages:
            newest = messages[-1]

            if newest["id"] > last_message_id:
                if last_message_id != 0:
                    print()
                    print(
                        f"Новое сообщение клиента! ID: {newest['id']}"
                    )

                    text = (newest.get("text") or "").strip()

                    if text:
                        print(f"Текст: {text}")

                        if newest.get("has_photo"):
                            print(
                                "В сообщении также есть фотография."
                            )

                        add_client_message_to_timeline(text)

                    elif newest.get("has_photo"):
                        print("Клиент отправил фотографию.")
                        add_client_message_to_timeline(
                            "Клиент отправил фотографию объекта."
                        )

                    if newest.get("has_audio"):
                        print("Клиент отправил аудио.")

                        audio_file = next(
                            (
                                file_info
                                for file_info in newest["files"]
                                if (
                                    file_info.get("type") == "audio"
                                    or file_info.get("extension")
                                    in {"ogg", "oga", "opus"}
                                )
                            ),
                            None,
                        )

                        if audio_file is None:
                            raise RuntimeError(
                                "Аудио обнаружено, но файл не найден."
                            )

                        extension = (
                            audio_file.get("extension") or "ogg"
                        ).lower()

                        if extension not in {"ogg", "oga", "opus"}:
                            print(
                                f"Формат {extension} не отправляем в SpeechKit."
                            )
                        else:
                            with tempfile.TemporaryDirectory() as temp_dir:
                                audio_path = (
                                    Path(temp_dir) / f"audio.{extension}"
                                )

                                print("Скачиваем аудио из Bitrix...")
                                openline.download_file(
                                    audio_file,
                                    audio_path,
                                )

                                print("Распознаём через SpeechKit...")
                                transcript = transcribe_audio(audio_path)

                            print()
                            print("РАСПОЗНАННЫЙ ТЕКСТ:")
                            print(transcript)

                            add_client_message_to_timeline(
                                f"Входящий звонок — расшифровка:\n{transcript}"
                            )

                    print("Ждём обработку через Bitrix webhook...")

                else:
                    print(
                        f"Текущий последний ID: {newest['id']}"
                    )

                last_message_id = newest["id"]

    except Exception:
        print()
        print("ОШИБКА:")
        traceback.print_exc()

    time.sleep(INTERVAL)
