import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("BITRIX_WEBHOOK_URL")
deal_id = os.getenv("BITRIX_DEAL_ID")

if not webhook_url:
    raise RuntimeError("Не найден BITRIX_WEBHOOK_URL в .env")

if not deal_id:
    raise RuntimeError("Не найден BITRIX_DEAL_ID в .env")

url = webhook_url.rstrip("/") + "/crm.timeline.item.list.json"

response = httpx.post(
    url,
    json={
        "filter": {
            "ENTITY_ID": int(deal_id),
            "ENTITY_TYPE": "deal",
        },
        "order": {
            "ID": "ASC",
        },
    },
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