"""Public Indian-English conversational voice; explicit env override remains available."""
import os

DEFAULT_VOICE = 'fPIfC3elMLbN9tNwMXkw'  # Viraj — Confident and Natural; workspace metadata verified 2026-11-17.


def selected_voice():
    value = os.getenv('ELEVENLABS_VOICE','').strip()
    return DEFAULT_VOICE if not value or value in ('brian','auto-indian') else value
