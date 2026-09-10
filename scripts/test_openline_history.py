from app.bitrix import BitrixClient
from app.config import BITRIX_WEBHOOK_URL


CHAT_ID = 10

client = BitrixClient(BITRIX_WEBHOOK_URL)

print(f"Получаем историю чата #{CHAT_ID}...")

history = client.call(
    "imopenlines.session.history.get",
    {
        "CHAT_ID": CHAT_ID,
    },
)

print("\nРЕЗУЛЬТАТ:")
print(history)