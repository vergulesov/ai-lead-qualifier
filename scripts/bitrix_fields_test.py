import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("BITRIX_WEBHOOK_URL")

if not webhook_url:
    raise RuntimeError("Не найден BITRIX_WEBHOOK_URL в .env")

url = webhook_url.rstrip("/") + "/crm.deal.fields.json"

response = httpx.post(
    url,
    json={},
    timeout=30,
)

print("HTTP:", response.status_code)

response.raise_for_status()

data = response.json()

print(
    json.dumps(
        data,
        ensure_ascii=False,
        indent=2,
    )
)