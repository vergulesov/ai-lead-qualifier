import asyncio
import json
from threading import Lock
from urllib.parse import parse_qs

from fastapi import FastAPI, HTTPException, Request

from .config import PROFILES_DIR
from .profile import list_profiles, load_profile, ProfileError
from .qualification_service import process_deal
from .bitrix import BitrixClient
from .openline import OpenLineClient


app = FastAPI(
    title="AI Lead Qualifier",
    version="1.0.0",
)


# =========================================================
# WEBHOOK PROCESSING LOCK
# =========================================================

_processing_deals: set[str] = set()
_processing_lock = Lock()


def _try_lock_deal(
    deal_id: str,
) -> bool:

    with _processing_lock:

        if deal_id in _processing_deals:
            return False

        _processing_deals.add(
            deal_id
        )

        return True


def _unlock_deal(
    deal_id: str,
) -> None:

    with _processing_lock:

        _processing_deals.discard(
            deal_id
        )


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():

    return {
        "status": "ok"
    }


# =========================================================
# PROFILES
# =========================================================

@app.get("/profiles")
def profiles():

    return {
        "profiles": list_profiles(
            PROFILES_DIR
        )
    }


@app.get("/profiles/{name}")
def profile(name: str):

    try:

        p = load_profile(
            PROFILES_DIR,
            name,
        )

        return {
            "name": p.name,
            "version": p.version,
            "fields": p.fields,
            "required_fields": p.required_fields,
        }

    except ProfileError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )


# =========================================================
# BITRIX WEBHOOK HELPERS
# =========================================================

async def _read_webhook_payload(
    request: Request,
) -> dict:

    body = await request.body()

    if not body:
        return {}

    content_type = (
        request.headers
        .get("content-type", "")
        .lower()
    )

    # JSON
    if "application/json" in content_type:

        try:

            return json.loads(
                body.decode("utf-8")
            )

        except json.JSONDecodeError:

            return {}

    # Bitrix обычно присылает form-urlencoded.
    try:

        parsed = parse_qs(
            body.decode(
                "utf-8",
                errors="replace",
            )
        )

        return {
            key: (
                value[0]
                if len(value) == 1
                else value
            )
            for key, value in parsed.items()
        }

    except Exception:

        return {}


def _extract_deal_id(
    payload: dict,
) -> str | None:

    for key in (
        "data[FIELDS][ID]",
        "data[FIELDS][ID][]",
        "FIELDS[ID]",
        "deal_id",
        "DEAL_ID",
    ):

        value = payload.get(
            key
        )

        if value:

            return str(
                value
            )

    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        dict,
    ):

        fields = data.get(
            "FIELDS"
        )

        if isinstance(
            fields,
            dict,
        ):

            deal_id = fields.get(
                "ID"
            )

            if deal_id:

                return str(
                    deal_id
                )

        deal_id = data.get(
            "deal_id"
        )

        if deal_id:

            return str(
                deal_id
            )

    return None


def _extract_comment_id(
    payload: dict,
) -> str | None:

    # Реальный Bitrix24 event:
    #
    # data[FIELDS][ID] = ID комментария
    #
    for key in (
        "data[FIELDS][ID]",
        "data[FIELDS][ID][]",
        "FIELDS[ID]",
        "comment_id",
        "COMMENT_ID",
    ):

        value = payload.get(
            key
        )

        if value:

            return str(
                value
            )

    # JSON-варианты
    data = payload.get(
        "data"
    )

    if isinstance(
        data,
        dict,
    ):

        fields = data.get(
            "FIELDS"
        )

        if isinstance(
            fields,
            dict,
        ):

            comment_id = fields.get(
                "ID"
            )

            if comment_id:

                return str(
                    comment_id
                )

        comment_id = data.get(
            "comment_id"
        )

        if comment_id:

            return str(
                comment_id
            )

    return None


# =========================================================
# OPEN LINE ATTACHMENT FACTS
# =========================================================


def _get_latest_openline_photo_fact(
    deal_id: str,
) -> bool | None:
    """
    Получает фактическое наличие фотографии из Open Line.

    Это намеренно не извлекается из текста: фраза
    "Фото сейчас скину" не является фактом получения фото.
    "Да" выставляется только если последнее сообщение
    клиента действительно содержит image-вложение.
    "Нет" возвращается только для явного отсутствия фото
    в сообщении, когда это сообщение является источником
    текущего события.
    """

    try:
        client = BitrixClient()
        openline = OpenLineClient(client)
        messages = openline.get_client_messages(deal_id)

        if not messages:
            return None

        newest = messages[-1]
        return bool(newest.get("has_photo"))

    except Exception as exc:
        print(
            "[ACTIVITY WEBHOOK] Не удалось получить "
            f"факт вложения фото из Open Line: {exc}"
        )
        return None


# =========================================================
# DEAL PROCESSING
# =========================================================

async def _process_deal_background(
    deal_id: str,
    has_photo: bool | None = None,
) -> None:

    try:

        # AI/GigaChat/HTTP — блокирующий код.
        # Выполняем его не в event loop FastAPI.
        await asyncio.to_thread(
            process_deal,
            deal_id,
            None,
            None,
            has_photo,
        )

    except Exception as exc:

        print(
            f"[WEBHOOK] Ошибка обработки "
            f"сделки #{deal_id}: {exc}"
        )

    finally:

        _unlock_deal(
            deal_id
        )


# =========================================================
# BITRIX DEAL WEBHOOK
# =========================================================

@app.post("/webhook/bitrix")
async def bitrix_webhook(
    request: Request,
):

    payload = await _read_webhook_payload(
        request
    )

    print()
    print(
        "=" * 60
    )
    print(
        "[WEBHOOK] Получено событие Bitrix24"
    )
    print(
        "=" * 60
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    deal_id = _extract_deal_id(
        payload
    )

    if not deal_id:

        print(
            "[WEBHOOK] ID сделки не найден."
        )

        return {
            "status": "ignored",
            "reason": "deal_id_not_found",
        }

    if not _try_lock_deal(
        deal_id
    ):

        print(
            f"[WEBHOOK] Сделка #{deal_id} "
            f"уже обрабатывается."
        )

        return {
            "status": "ignored",
            "reason": "deal_already_processing",
            "deal_id": deal_id,
        }

    asyncio.create_task(
        _process_deal_background(
            deal_id
        )
    )

    return {
        "status": "accepted",
        "deal_id": deal_id,
    }


# =========================================================
# BITRIX TIMELINE COMMENT WEBHOOK
# =========================================================

@app.post("/webhook/bitrix/activity")
async def bitrix_activity_webhook(
    request: Request,
):

    payload = await _read_webhook_payload(
        request
    )

    print()
    print(
        "=" * 60
    )
    print(
        "[ACTIVITY WEBHOOK] Получено событие Bitrix24"
    )
    print(
        "=" * 60
    )

    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )
    )

    event = payload.get(
        "event"
    )

    if event != "ONCRMTIMELINECOMMENTADD":

        print(
            f"[ACTIVITY WEBHOOK] "
            f"Событие не является добавлением "
            f"комментария: {event}"
        )

        return {
            "status": "ignored",
            "reason": "unsupported_event",
            "event": event,
        }

    comment_id = _extract_comment_id(
        payload
    )

    if not comment_id:

        print(
            "[ACTIVITY WEBHOOK] "
            "ID комментария не найден."
        )

        return {
            "status": "ignored",
            "reason": "comment_id_not_found",
        }

    print(
        f"[ACTIVITY WEBHOOK] "
        f"Получен комментарий #{comment_id}"
    )

    try:

        client = BitrixClient()

        response = await asyncio.to_thread(
            client.call,
            "crm.timeline.comment.get",
            {
                "id": comment_id,
            },
        )

        print()
        print(
            "[ACTIVITY WEBHOOK] "
            "Ответ crm.timeline.comment.get:"
        )

        print(
            json.dumps(
                response,
                ensure_ascii=False,
                indent=2,
            )
        )

        result = response

        if not isinstance(
            result,
            dict,
        ):

            print(
                "[ACTIVITY WEBHOOK] "
                "Не удалось получить данные комментария."
            )

            return {
                "status": "error",
                "comment_id": comment_id,
                "reason": "invalid_comment_response",
            }

        entity_id = (
            result.get("ENTITY_ID")
            or result.get("entity_id")
        )

        entity_type = (
            result.get("ENTITY_TYPE")
            or result.get("entity_type")
        )

        comment = (
            result.get("COMMENT")
            or result.get("comment")
        )

        author_id = (
            result.get("AUTHOR_ID")
            or result.get("author_id")
        )

        print()
        print(
            "-" * 60
        )
        print(
            "[ACTIVITY WEBHOOK] "
            "Распознанные данные:"
        )
        print(
            f"Comment ID : {comment_id}"
        )
        print(
            f"Entity ID  : {entity_id}"
        )
        print(
            f"Entity type: {entity_type}"
        )
        print(
            f"Author ID  : {author_id}"
        )
        print(
            f"Comment    : {comment}"
        )
        print(
            "-" * 60
        )

        if entity_type != "deal":

            print(
                "[ACTIVITY WEBHOOK] "
                "Комментарий не относится к сделке."
            )

            return {
                "status": "ignored",
                "reason": "entity_is_not_deal",
                "comment_id": comment_id,
                "entity_type": entity_type,
                "entity_id": entity_id,
            }

        if not entity_id:

            print(
                "[ACTIVITY WEBHOOK] "
                "ID сделки не найден."
            )

            return {
                "status": "ignored",
                "reason": "deal_id_not_found",
                "comment_id": comment_id,
            }

        deal_id = str(
            entity_id
        )

        if not _try_lock_deal(
            deal_id
        ):

            print(
                f"[ACTIVITY WEBHOOK] "
                f"Сделка #{deal_id} "
                f"уже обрабатывается."
            )

            return {
                "status": "ignored",
                "reason": "deal_already_processing",
                "deal_id": deal_id,
            }

        # -------------------------------------------------
        # Источник истины для фотографии — Open Line.
        # -------------------------------------------------
        # Текст "Фото сейчас скину" не даёт права
        # выставить photos_available=true.
        # true появляется только при реальном image-вложении.
        has_photo = await asyncio.to_thread(
            _get_latest_openline_photo_fact,
            deal_id,
        )

        print(
            "[ACTIVITY WEBHOOK] "
            "Факт фотографии из Open Line: "
            + (
                "Да"
                if has_photo is True
                else "Нет"
                if has_photo is False
                else "не определён"
            )
        )

        asyncio.create_task(
            _process_deal_background(
                deal_id,
                has_photo=has_photo,
            )
        )

        print()
        print(
            f"[ACTIVITY WEBHOOK] "
            f"Запущена квалификация сделки #{deal_id}"
        )

        return {
            "status": "accepted",
            "comment_id": comment_id,
            "deal_id": deal_id,
        }

    except Exception as exc:

        print()
        print(
            "[ACTIVITY WEBHOOK] "
            f"Ошибка обработки комментария: {exc}"
        )

        return {
            "status": "error",
            "comment_id": comment_id,
            "error": str(exc),
        }
