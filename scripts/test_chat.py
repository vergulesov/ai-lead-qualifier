from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL

bitrix = BitrixClient(BITRIX_WEBHOOK_URL)

result = bitrix.call(
    "imopenlines.crm.chat.get",
    {
        "CRM_ENTITY_TYPE": "deal",
        "CRM_ENTITY": 10,
        "ACTIVE_ONLY": "N",
    },
)

print(result)