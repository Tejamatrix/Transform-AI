"""LLM provider abstraction.

Providers:
- openai: OpenAI-compatible chat completions (OpenAI, Azure, Groq, Ollama, etc.)
- offline: deterministic heuristic engine so the full workflow runs without API keys.

Switch via LLM_PROVIDER env var. The application must never import a concrete
provider outside this module.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.core.config import settings
from app.providers.llm.offline_engine import offline_generate


class LLMError(Exception):
    pass


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, schema_hint: dict | None = None) -> dict[str, Any]:
        ...


class OpenAIProvider(LLMProvider):
    name = "openai"

    def generate_json(self, system_prompt: str, user_prompt: str, schema_hint: dict | None = None) -> dict[str, Any]:
        payload = {
            "model": settings.LLM_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {settings.GLM_API_KEY or settings.OPENAI_API_KEY}"}
        try:
            resp = httpx.post(
                f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
                json=payload,
                headers=headers,
                timeout=90,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return self._parse_json(content)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise LLMError("LLM rate limit reached. Please retry shortly.")
            raise LLMError(f"LLM request failed ({e.response.status_code}).")
        except (httpx.HTTPError, KeyError, IndexError):
            raise LLMError("LLM did not return a valid response.")
        except json.JSONDecodeError:
            raise LLMError("LLM returned malformed JSON.")

    @staticmethod
    def _parse_json(content: str) -> dict:
        content = content.strip()
        if content.startswith("```"):
            content = re.sub(r"^```[a-zA-Z]*\n?|```$", "", content, flags=re.MULTILINE).strip()
        return json.loads(content)


class OfflineProvider(LLMProvider):
    """Deterministic extraction/heuristic engine.

    Produces the same structured outputs the real LLM would, using rule-based
    analysis of the provided context. Keeps the platform fully demonstrable
    offline and in tests.
    """

    name = "offline"

    def generate_json(self, system_prompt: str, user_prompt: str, schema_hint: dict | None = None) -> dict[str, Any]:
        return offline_generate(system_prompt, user_prompt)


class FallbackAwareProvider(LLMProvider):
    """Live provider with automatic fallback to the offline engine.

    Keeps the platform fully usable when the live LLM is unavailable (zero
    balance, rate limit, timeout, invalid response). Non-strict mode: live
    failures degrade gracefully; strict mode: failures raise.
    """

    name = "openai+fallback"

    def generate_json(self, system_prompt: str, user_prompt: str, schema_hint: dict | None = None) -> dict[str, Any]:
        try:
            return OpenAIProvider().generate_json(system_prompt, user_prompt, schema_hint)
        except LLMError:
            if settings.LLM_FALLBACK == "strict":
                raise
            result = offline_generate(system_prompt, user_prompt)
            if isinstance(result, dict):
                result["_offline_fallback"] = True
            return result


_provider: LLMProvider | None = None


def get_llm_provider() -> LLMProvider:
    global _provider
    if _provider is None:
        if settings.LLM_PROVIDER == "openai":
            _provider = FallbackAwareProvider()
        else:
            _provider = OfflineProvider()
    return _provider
