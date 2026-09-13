# MVP Decisions

- Docker excluded.
- One CRM: Bitrix24.
- LLM provider: GigaChat.
- Speech-to-text provider: Yandex SpeechKit.
- One main niche profile: wooden house painting.
- Score is deterministic.
- AI may suggest a change to manager-owned fields but cannot overwrite them.
- Short/noise messages are ignored before LLM.
- Short calls are ignored before STT.
- Long calls are transcribed before LLM.
- Object priority is a business priority signal, not a judgment of client quality.
- New niche = new profile, not new core engine.
