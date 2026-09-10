import json
import sys

from .qualification_service import process_deal


def main():

    if len(sys.argv) < 2:

        print(
            "Использование: "
            "python -m app.demo_bitrix DEAL_ID"
        )

        return

    deal_id = sys.argv[1]

    try:

        result = process_deal(
            deal_id
        )

    except Exception as exc:

        print()
        print(
            "ОШИБКА:"
        )
        print(
            str(exc)
        )

        raise

    print()
    print(
        "=" * 60
    )
    print(
        "RESULT"
    )
    print(
        "=" * 60
    )

    print(
        json.dumps(
            result,
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()