import hashlib
import re

NOISE = {
    "ок", "ага", "понял", "поняла", "спасибо", "хорошо", "ясно",
    "да", "нет", "👍", "👌", "спс"
}

def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def message_should_process(text: str, known_hashes: set[str] | None = None) -> bool:
    value = normalize_text(text)
    if not value or value in NOISE or len(value) < 12:
        return False
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    if known_hashes and digest in known_hashes:
        return False
    return True


def call_should_process(duration_seconds: int, transcript: str | None = None) -> bool:
    if duration_seconds < 15:
        return False
    if transcript is not None and not message_should_process(transcript):
        return False
    return True
