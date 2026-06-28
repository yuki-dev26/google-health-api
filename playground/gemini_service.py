"""Gemini API（google-genai SDK）"""

import os
from pathlib import Path

from google import genai
from google.genai import types

SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "system_prompt.md"
DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")


def _load_character_prompt() -> str:
    return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8").strip()


def _build_system_instruction(health_context: str) -> str:
    return f"{_load_character_prompt()}\n\n{health_context}"


class GeminiClient:
    def __init__(self) -> None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("GEMINI_API_KEY が .env に設定されていません。")
        self._client = genai.Client(api_key=api_key)

    def ask(self, message: str, health_context: str) -> str:
        response = self._client.models.generate_content(
            model=DEFAULT_MODEL,
            contents=message,
            config=types.GenerateContentConfig(
                system_instruction=_build_system_instruction(health_context),
            ),
        )
        text = response.text
        if not text:
            raise RuntimeError("Gemini から空の応答が返されました。")
        return text
