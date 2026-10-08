from __future__ import annotations

import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.core.config import Settings


class LLMConfigurationError(RuntimeError):
    pass


class LLMServiceError(RuntimeError):
    pass


class GeminiService:
    """Minimal Gemini REST client; API keys remain server-side in environment settings."""

    def __init__(self, settings: Settings) -> None:
        self._provider = (settings.llm_provider or "gemini").lower()
        self._api_key = settings.gemini_api_key
        self._model = settings.gemini_model

    async def generate(self, system_instruction: str, prompt: str) -> str:
        if self._provider != "gemini":
            raise LLMConfigurationError("Only the Gemini provider is configured for this release. Set LLM_PROVIDER=gemini.")
        if not self._api_key:
            raise LLMConfigurationError("Gemini is not configured. Set GEMINI_API_KEY in the backend .env file.")
        return await asyncio.to_thread(self._generate_sync, system_instruction, prompt)

    def _generate_sync(self, system_instruction: str, prompt: str) -> str:
        model = quote(self._model, safe="-._")
        request = Request(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            data=json.dumps({
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2, "maxOutputTokens": 350},
            }).encode("utf-8"),
            headers={"Content-Type": "application/json", "x-goog-api-key": self._api_key},
            method="POST",
        )
        try:
            with urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as error:
            response_body = error.read().decode("utf-8", errors="replace")
            print(f"Gemini HTTP error status: {error.code}")
            print(f"Gemini HTTP error response: {response_body}")
            raise LLMServiceError("Gemini could not complete the request. Check the API key and model configuration.") from error
        except URLError as error:
            raise LLMServiceError("Gemini is temporarily unavailable. Please try again shortly.") from error
        try:
            text = payload["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (KeyError, IndexError, TypeError, AttributeError) as error:
            raise LLMServiceError("Gemini returned an empty response. Please try again.") from error
        if not text:
            raise LLMServiceError("Gemini returned an empty response. Please try again.")
        return text
