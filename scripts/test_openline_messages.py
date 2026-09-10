from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL
from app.openline import OpenLineClient


DEAL_ID = 10

bitrix = BitrixClient(BITRIX_WEBHOOK_URL)
openline = OpenLineClient(bitrix)

print(f"Сообщения клиента по сделке #{DEAL_ID}:\n")

messages = openline.get_client_messages(DEAL_ID)

for message in messages:
    print(
        f"[{message['id']}] "
        f"{message['date']} — "
        f"{message['text']}"
    )

print(f"\nВсего сообщений клиента: {len(messages)}")