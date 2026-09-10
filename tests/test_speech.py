from app.speech_to_text import transcribe_audio


AUDIO_FILE = "demo_voice.ogg"


def main():
    print("=" * 60)
    print("SPEECHKIT REAL AUDIO TEST")
    print("=" * 60)

    text = transcribe_audio(AUDIO_FILE)

    print()
    print("TRANSCRIPT:")
    print("-" * 60)
    print(text)
    print("-" * 60)


if __name__ == "__main__":
    main()