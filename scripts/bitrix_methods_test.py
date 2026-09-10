import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

webhook_url = os.getenv("BITRIX_WEBHOOK_URL")
deal_id = int(os.getenv("BITRIX_DEAL_ID", "2"))

if not webhook_url:
    raise RuntimeError("Не найден BITRIX_WEBHOOK_URL в .env")

base_url = webhook_url.rstrip("/")


def call(method, payload):
    url = f"{base_url}/{method}.json"

    response = httpx.post(
        url,
        json=payload,
        timeout=30,
    )

    print("\n" + "=" * 60)
    print(method)
    print("HTTP:", response.status_code)

    try:
        data = response.json()
        print(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            )
        )
    except Exception:
        print(response.text)


call(
    "crm.deal.get",
    {
        "id": deal_id,
    },
)

call(
    "crm.activity.list",
    {
        "filter": {
            "OWNER_ID": deal_id,
            "OWNER_TYPE_ID": 2,
        },
        "order": {
            "ID": "ASC",
        },
    },
)