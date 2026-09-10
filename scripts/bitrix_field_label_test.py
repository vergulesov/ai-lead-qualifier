import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("BITRIX_WEBHOOK_URL")

url = webhook_url.rstrip("/") + "/crm.deal.userfield.get.json"

response = httpx.post(
    url,
    json={
        "id": 234
    },
    timeout=30,
)

print("HTTP:", response.status_code)

response.raise_for_status()

print(
    json.dumps(
        response.json(),
        ensure_ascii=False,
        indent=2,
    )
)