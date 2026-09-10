import requests


class OpenLineClient:
    def __init__(self, bitrix):
        self.bitrix = bitrix

    def get_chat_id(self, deal_id):
        result = self.bitrix.call(
            "imopenlines.crm.chat.get",
            {
                "CRM_ENTITY_TYPE": "deal",
                "CRM_ENTITY": deal_id,
                "ACTIVE_ONLY": "N",
            },
        )

        if not result:
            return None

        chat_id = result[0].get("CHAT_ID")
        return int(chat_id) if chat_id else None

    def get_history(self, chat_id):
        return self.bitrix.call(
            "imopenlines.session.history.get",
            {
                "CHAT_ID": chat_id,
            },
        )

    def get_client_messages(self, deal_id, chat_id=None):
        if chat_id is None:
            chat_id = self.get_chat_id(deal_id)

        if chat_id is None:
            return []

        history = self.get_history(chat_id)

        messages = history.get("message", {})
        users = history.get("users", {})
        files = history.get("files", {})

        result = []

        for message in messages.values():
            sender_id = str(message.get("senderid", ""))
            sender = users.get(sender_id, {})

            # Берём только сообщения клиента Telegram/Open Line.
            if not sender.get("connector"):
                continue

            text = (message.get("text") or "").strip()
            params = message.get("params") or {}

            raw_file_ids = params.get("fileId", [])
            if not isinstance(raw_file_ids, list):
                raw_file_ids = [raw_file_ids]

            message_files = []

            for file_id in raw_file_ids:
                file_info = files.get(str(file_id)) or files.get(file_id)

                if file_info:
                    message_files.append(
                        {
                            "id": int(file_info.get("id", file_id)),
                            "name": file_info.get("name"),
                            "type": file_info.get("type"),
                            "extension": (
                                file_info.get("extension") or ""
                            ).lower(),
                            "urlshow": file_info.get("urlshow"),
                            "urldownload": file_info.get("urldownload"),
                        }
                    )
                else:
                    message_files.append(
                        {
                            "id": int(file_id),
                            "name": None,
                            "type": None,
                            "extension": None,
                            "urlshow": None,
                            "urldownload": None,
                        }
                    )

            has_photo = any(
                (file.get("type") == "image")
                or file.get("extension") in {
                    "jpg", "jpeg", "png", "webp", "heic"
                }
                for file in message_files
            )

            has_audio = any(
                (file.get("type") == "audio")
                or file.get("extension") in {
                    "ogg", "oga", "opus", "mp3", "wav", "m4a"
                }
                for file in message_files
            )

            # Не теряем сообщения, состоящие только из файла.
            if not text and not message_files:
                continue

            result.append(
                {
                    "id": int(message["id"]),
                    "date": message.get("date"),
                    "text": text,
                    "files": message_files,
                    "has_photo": has_photo,
                    "has_audio": has_audio,
                }
            )

        result.sort(key=lambda x: x["id"])
        return result

    def download_file(self, file_info, destination):
        """
        Скачивает файл Bitrix Disk по его ID.
        Для серверной загрузки используем disk.file.get -> DOWNLOAD_URL.
        """
        file_id = file_info["id"]

        file_data = self.bitrix.call(
            "disk.file.get",
            {"id": file_id},
        )

        download_url = (
            file_data.get("DOWNLOAD_URL")
            or file_data.get("downloadUrl")
            or file_data.get("DOWNLOAD_URL_FULL")
        )

        if not download_url:
            raise RuntimeError(
                f"Bitrix не вернул DOWNLOAD_URL для файла {file_id}"
            )

        response = requests.get(
            download_url,
            timeout=60,
        )
        response.raise_for_status()

        destination = str(destination)

        with open(destination, "wb") as f:
            f.write(response.content)

        return destination
