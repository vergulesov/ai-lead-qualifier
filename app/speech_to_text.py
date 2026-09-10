from pathlib import Path

from app.speechkit import speech_to_text


def transcribe_audio(audio_file: str | Path) -> str:
    """
    Расшифровывает OGG/Opus-файл через Yandex SpeechKit.
    """

    audio_path = Path(audio_file)

    if not audio_path.exists():
        raise FileNotFoundError(
            f"Audio file not found: {audio_path}"
        )

    audio_data = audio_path.read_bytes()

    if not audio_data:
        raise ValueError(
            f"Audio file is empty: {audio_path}"
        )

    return speech_to_text(audio_data)