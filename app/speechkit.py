import grpc

import yandex.cloud.ai.stt.v3.stt_pb2 as stt_pb2
import yandex.cloud.ai.stt.v3.stt_service_pb2_grpc as stt_service_pb2_grpc

from app.config import (
    YANDEX_API_KEY,
    YANDEX_FOLDER_ID,
    SPEECHKIT_HOST,
    CHUNK_SIZE,
)


def speech_to_text(audio_data):
    print()
    print("🎤 Отправляем голос в Yandex SpeechKit...")
    print()

    def generate_requests():
        recognize_options = stt_pb2.StreamingOptions(
            recognition_model=stt_pb2.RecognitionModelOptions(
                model="general",
                audio_format=stt_pb2.AudioFormatOptions(
                    container_audio=stt_pb2.ContainerAudio(
                        container_audio_type=stt_pb2.ContainerAudio.OGG_OPUS
                    )
                ),
                language_restriction=stt_pb2.LanguageRestrictionOptions(
                    restriction_type=stt_pb2.LanguageRestrictionOptions.WHITELIST,
                    language_code=["ru-RU"],
                ),
                audio_processing_type=(
                    stt_pb2.RecognitionModelOptions.REAL_TIME
                ),
            )
        )

        yield stt_pb2.StreamingRequest(
            session_options=recognize_options
        )

        for i in range(0, len(audio_data), CHUNK_SIZE):
            chunk = audio_data[i:i + CHUNK_SIZE]

            yield stt_pb2.StreamingRequest(
                chunk=stt_pb2.AudioChunk(
                    data=chunk
                )
            )

        yield stt_pb2.StreamingRequest(
            eou=stt_pb2.Eou()
        )

    try:
        credentials = grpc.ssl_channel_credentials()

        channel = grpc.secure_channel(
            SPEECHKIT_HOST,
            credentials
        )

        stub = stt_service_pb2_grpc.RecognizerStub(channel)

        responses = stub.RecognizeStreaming(
            generate_requests(),
            metadata=(
            (
                "authorization",
                f"Api-Key {YANDEX_API_KEY}"
            ),
        )
        )

        final_text = None
        refined_text = None
        final_parts = []

        for response in responses:
            event_type = response.WhichOneof("Event")

            print(
                "SpeechKit EVENT:",
                event_type
            )

            if event_type == "final":

                if response.final.alternatives:
                    text = (
                        response
                        .final
                        .alternatives[0]
                        .text
                    )

                    if text:
                        print(
                            "  FINAL:",
                            text
                        )

                        final_text = text.strip()
                        final_parts.append(final_text)

            elif event_type == "final_refinement":

                if (
                    response
                    .final_refinement
                    .normalized_text
                    .alternatives
                ):
                    text = (
                        response
                        .final_refinement
                        .normalized_text
                        .alternatives[0]
                        .text
                    )

                    if text:
                        print(
                            "  REFINED:",
                            text
                        )

                        refined_text = text.strip()

            elif event_type == "status_code":

                print(
                    "  STATUS:",
                    response.status_code
                )

        if refined_text:
            result_text = refined_text

        elif final_text:
            result_text = final_text

        elif final_parts:
            result_text = " ".join(final_parts)

        else:
            raise RuntimeError(
                "SpeechKit не вернул распознанный текст"
            )

        print()
        print(
            "📝 РАСПОЗНАНО:",
            result_text
        )
        print()

        return result_text

    except grpc.RpcError as e:
        print()
        print("❌ SpeechKit gRPC ошибка")
        print("Код:", e.code())
        print("Сообщение:", e.details())
        raise


print("API KEY LENGTH:", len(YANDEX_API_KEY))
print("FOLDER ID:", YANDEX_FOLDER_ID)
print("HOST:", SPEECHKIT_HOST)