from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL


DEAL_ID = 10


client = BitrixClient(BITRIX_WEBHOOK_URL)

print(f"Ищем Open Line для сделки #{DEAL_ID}...")

chats = client.call(
    "imopenlines.crm.chat.get",
    {
        "CRM_ENTITY_TYPE": "deal",
        "CRM_ENTITY": DEAL_ID,
        "ACTIVE_ONLY": "N",
    },
)

print("\nРЕЗУЛЬТАТ:")
print(chats)