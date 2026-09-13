import json
import sys
from pathlib import Path

from .analyzer import GigaChatAnalyzer
from .config import (
    GIGACHAT_CREDENTIALS,
    GIGACHAT_MODEL,
    GIGACHAT_API_URL,
    GIGACHAT_AUTH_URL,
    GIGACHAT_SCOPE,
    GIGACHAT_TIMEOUT,
    GIGACHAT_RETRIES,
    PROFILES_DIR,
)
from .models import LeadInput, QualificationState
from .pipeline import build_result
from .precheck import message_should_process
from .profile import load_profile


def run():
    filename = sys.argv[1] if len(sys.argv) > 1 else "demo_lead.json"

    lead_path = Path("data") / filename

    if not lead_path.exists():
        print(f"Файл не найден: {lead_path}")
        return

    lead = LeadInput.model_validate(
        json.loads(lead_path.read_text(encoding="utf-8"))
    )

    if not any(
        message_should_process(message.text)
        for message in lead.messages
    ) and not lead.calls:
        print("PRE-CHECK: ничего содержательного для анализа.")
        return

    profile = load_profile(PROFILES_DIR, "wooden_house")

    analyzer = GigaChatAnalyzer(
        credentials=GIGACHAT_CREDENTIALS,
        model=GIGACHAT_MODEL,
        api_url=GIGACHAT_API_URL,
        auth_url=GIGACHAT_AUTH_URL,
        scope=GIGACHAT_SCOPE,
        timeout=GIGACHAT_TIMEOUT,
        retries=GIGACHAT_RETRIES,
    )

    analysis = analyzer.analyze(lead, profile)

    result = build_result(
        lead,
        profile,
        analysis,
        QualificationState(),
    )

    print(
        json.dumps(
            result.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    run()
