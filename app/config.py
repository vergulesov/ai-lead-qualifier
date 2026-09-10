from pathlib import Path
import os

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")


PROFILES_DIR = BASE_DIR / "profiles"
DATA_DIR = BASE_DIR / "data"


# ============================================================
# GigaChat
# ============================================================

GIGACHAT_CREDENTIALS = os.getenv(
    "GIGACHAT_CREDENTIALS",
)

GIGACHAT_MODEL = os.getenv(
    "GIGACHAT_MODEL",
    "GigaChat-2-Max",
)

GIGACHAT_API_URL = os.getenv(
    "GIGACHAT_API_URL",
    "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
)

GIGACHAT_AUTH_URL = os.getenv(
    "GIGACHAT_AUTH_URL",
    "https://ngw.devices.sberbank.ru:9443/api/v2/oauth",
)

GIGACHAT_SCOPE = os.getenv(
    "GIGACHAT_SCOPE",
    "GIGACHAT_API_PERS",
)

GIGACHAT_TIMEOUT = float(
    os.getenv(
        "GIGACHAT_TIMEOUT",
        "90",
    )
)

GIGACHAT_RETRIES = int(
    os.getenv(
        "GIGACHAT_RETRIES",
        "2",
    )
)


# ============================================================
# Bitrix24
# ============================================================

BITRIX_WEBHOOK_URL = os.getenv(
    "BITRIX_WEBHOOK_URL",
)

# ============================================================
# Yandex SpeechKit
# ============================================================

YANDEX_API_KEY = os.getenv(
    "YANDEX_API_KEY",
)

YANDEX_FOLDER_ID = os.getenv(
    "YANDEX_FOLDER_ID",
)

SPEECHKIT_HOST = "stt.api.cloud.yandex.net:443"

CHUNK_SIZE = 4096