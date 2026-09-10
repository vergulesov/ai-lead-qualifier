import tempfile
import time
import traceback
from pathlib import Path

from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL
from app.openline import OpenLineClient
from app.qualification_service import process_deal
from app.speech_to_text import transcribe_audio


DEAL_ID = 10
INTERVAL = 5


bitrix = BitrixClient(BITRIX_WEBHOOK_URL)
openline = OpenLineClient(bitrix)

last_message_id = 0

print(f"Слушаем Open Line сделки #{DEAL_ID}")
print(f"Проверка каждые {INTERVAL} секунд.\n")


while True:
    try:
        messages = openline.get_client_messages(DEAL_ID)

        if messages:
            newest = messages[-1]

            if newest["id"] > last_message_id:
                if last_message_id != 0:
                    print(
                        f"🔔 Новое сообщение клиента!\n"
                        f"ID: {newest['id']}\n"
                        f"Дата: {newest['date']}\n"
                    )

                    # =========================
                    # 🎤 ГОЛОСОВОЕ СООБЩЕНИЕ
                    # =========================
                    if newest.get("has_audio"):
                        audio_file = next(
                            (
                                file_info
                                for file_info in newest["files"]
                                if (
                                    file_info.get("type") == "audio"
                                    or file_info.get("extension") in {
                                        "ogg",
                                        "oga",
                                        "opus",
                                    }
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

                        print(
                            f"🎤 Найдено аудио: "
                            f"{audio_file.get('name')}"
                        )

                        # SpeechKit сейчас настроен на OGG/Opus.
                        if extension not in {
                            "ogg",
                            "oga",
                            "opus",
                        }:
                            print(
                                f"⚠️ Формат {extension.upper()} "
                                f"пока не поддерживается текущей "
                                f"настройкой SpeechKit."
                            )

                        else:
                            with tempfile.TemporaryDirectory() as temp_dir:
                                audio_path = (
                                    Path(temp_dir)
                                    / f"audio.{extension}"
                                )

                                print(
                                    "📥 Скачиваем аудио из Bitrix..."
                                )

                                openline.download_file(
                                    audio_file,
                                    audio_path,
                                )

                                print(
                                    "🎤 Отправляем аудио "
                                    "в SpeechKit..."
                                )

                                transcript = transcribe_audio(
                                    audio_path
                                )

                            print()
                            print(
                                "📝 Распознанный текст:"
                            )
                            print(transcript)
                            print()

                            print(
                                "🤖 Запускаем квалификацию..."
                            )

                            result = process_deal(
                                DEAL_ID,
                                input_text=transcript,
                            )

                            print(
                                "✅ Квалификация завершена"
                            )
                            print(result)

                    # =========================
                    # 📷 ФОТО / ОБЫЧНЫЙ ТЕКСТ
                    # =========================
                    else:
                        text = newest["text"]

                        if newest.get("has_photo"):
                            if text:
                                text += (
                                    "\n"
                                    "[К сообщению прикреплена "
                                    "фотография объекта.]"
                                )
                            else:
                                text = (
                                    "[Клиент отправил "
                                    "фотографию объекта.]"
                                )

                        print(f"Текст: {text}\n")

                        print(
                            "🤖 Запускаем квалификацию..."
                        )

                        result = process_deal(
                            DEAL_ID,
                            input_text=text,
                        )

                        print(
                            "✅ Квалификация завершена"
                        )
                        print(result)

                else:
                    print(
                        f"Текущий последний ID: "
                        f"{newest['id']}\n"
                        f"Текст: {newest['text']}\n"
                    )

                last_message_id = newest["id"]

    except Exception:
        print("❌ Ошибка:")
        traceback.print_exc()

    time.sleep(INTERVAL)